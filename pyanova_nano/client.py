import asyncio
from asyncio import Future
from contextlib import suppress
import logging
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import overload

from bleak import AdvertisementData
from bleak import BLEDevice
from bleak import BleakClient
from bleak import BleakError
from bleak import BleakScanner
from google.protobuf.message import DecodeError

from pyanova_nano.commands import COMMANDS_MAP
from pyanova_nano.commands import convert_buffer
from pyanova_nano.commands import create_command_array
from pyanova_nano.proto.messages_pb2 import IntegerValue
from pyanova_nano.proto.messages_pb2 import SensorValue
from pyanova_nano.proto.messages_pb2 import UnitType
from pyanova_nano.types import Commands
from pyanova_nano.types import MessageTypes
from pyanova_nano.types import ReadCommands
from pyanova_nano.types import SensorValues
from pyanova_nano.types import WriteCommands

_LOGGER = logging.getLogger(__name__)


class PyAnova:
    """Client for the Anova Nano sous vide cooker.

    Examples:
        >>> import asyncio
        >>> from pyanova_nano import PyAnova

        >>> async def print_device_sensors():
        ...     async with PyAnova() as client:
        ...         print(await client.get_sensor_values())

        >>> asyncio.run(print_device_sensors())

    Args:
        loop: The active asyncio event loop.
        device: An optional bleak.BLEDevice to connect to.

    """

    SERVICE_UUID = "0e140000-0af1-4582-a242-773e63054c68"

    CHARACTERISTICS_WRITE = "0e140001-0af1-4582-a242-773e63054c68"
    CHARACTERISTICS_READ = "0e140002-0af1-4582-a242-773e63054c68"
    CHARACTERISTICS_ASYNC = "0e140003-0af1-4582-a242-773e63054c68"

    _CONNECT_TIMEOUT_SEC = 10
    _RX_DATA_TIMEOUT_SEC = 3

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        device: Optional[BLEDevice] = None,
        discover_timeout: int = 10,
    ):
        self._loop = loop or asyncio.get_running_loop()
        assert self._loop, "Must create an event loop first."

        self._scanner: Optional[BleakScanner] = None
        self._device: Optional[BLEDevice] = device
        self._client: Optional[BleakClient] = None

        self._discover_timeout: int = discover_timeout
        self._scanning = asyncio.Event()

        self._connect_lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()

        self._callbacks_disconnect: List[Callable] = []

        # Polling
        self._last_sensor_values: Optional[SensorValues] = None
        self._poll_interval: int = 30
        self._callbacks: List[Callable] = []
        self._stop = False
        self._is_poll_started = False
        self._task: Optional[Future] = None

    @property
    def client(self) -> BleakClient:
        """Return the BleakClient instance.

        Note: Only available once connected.

        """
        return self._client

    @property
    def ble_device(self) -> BLEDevice:
        """The BLEDevice."""
        return self._device

    @property
    def last_status(self) -> SensorValues:
        """Return the last polled sensor values."""
        return self._last_sensor_values

    def is_connected(self) -> bool:
        """Return True if connected to the BLE device."""
        return self._client is not None and self._client.is_connected

    async def connect(
        self,
        device: Optional[BLEDevice] = None,
        timeout_seconds: int | None = None,
    ):
        """Connect to a device.

        Args:
            device: If given, connect to this device. If not given, the client will
                discover the device.
            timeout_seconds: Time out connection attempt after this many seconds.

        """
        if self.is_connected():
            return

        _LOGGER.debug("Connecting...")
        if device:
            self._device = device

        if not self._device:
            _LOGGER.info("No device specified. Starting discovery...")
            await self.discover(
                connect=True, list_all=False, timeout_seconds=self._discover_timeout
            )
        else:
            await self._connect(self._device, timeout_seconds=timeout_seconds)

    async def disconnect(self):
        if self.is_connected():
            _LOGGER.info(f"Disconnecting from device: %s", self._device.address)
            await self._client.disconnect()

    async def _connect(self, device, timeout_seconds: int | None = None):
        timeout_seconds = timeout_seconds or self._CONNECT_TIMEOUT_SEC

        if self.is_connected():
            return

        async with self._connect_lock:
            if self.is_connected():
                return

            if not self._client or self._device is not device:
                self._device = device
                # Avoid re-using the same BleakClient - according to home assistant docs
                self._client = BleakClient(
                    address_or_ble_device=self._device,
                    timeout=timeout_seconds,
                    disconnected_callback=self._on_disconnect,
                )

            if not self._client.is_connected:
                await self._client.connect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def discover(
        self,
        connect: bool = False,
        list_all: bool = False,
        use_bdaddr: bool = False,
        timeout_seconds: int | None = None,
    ) -> List[BLEDevice]:
        """Find a device that provides the service id.

        Raises:
            RuntimeError: If no device was found.

        """
        timeout_seconds = timeout_seconds or self._discover_timeout
        detection_callback = (
            self._on_discovery_set_device if connect else self._on_discover_log
        )

        self._scanner = scanner = BleakScanner(
            detection_callback=detection_callback,
            use_bdaddr=use_bdaddr,
            # Look for any devices that provide the service uuid we need.
            service_uuids=[self.SERVICE_UUID],
        )
        await scanner.start()

        # Stop scan the moment we found a fitting device.
        self._scanning.set()
        end_time = self._loop.time() + timeout_seconds

        while self._scanning.is_set():
            await asyncio.sleep(0.1)
            if self._loop.time() < end_time:
                continue

            # Abort if we run out of time.
            self._scanning.clear()

        await scanner.stop()

        if not list_all and connect and not self._device:
            raise RuntimeError("Could not discover your Anova Nano.")

        if self._device and connect:
            await self._connect(self._device, timeout_seconds=self._CONNECT_TIMEOUT_SEC)

        # Filter by service uuid as bleak returns everything it found.
        devices = [
            device
            for device, adv in scanner.discovered_devices_and_advertisement_data.values()
            if self.SERVICE_UUID in adv.service_uuids
        ]
        return devices

    async def _on_discovery_set_device(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ):
        """Connect on discovery."""
        # Stop scanning.
        if (
            not device.name == "Nano"
            and self.SERVICE_UUID not in advertisement_data.service_uuids
        ):
            # On linux the callback is fired for every device, so we have to filter.
            _LOGGER.warning("Skipping unknown device: %s", device.name)
            return

        _LOGGER.info("Found device: %s - name: (%s)", device.address, device.name)

        if not self._connect_lock.locked():
            # Stop the scan.
            self._scanning.clear()
            self._device = device

    @staticmethod
    async def _on_discover_log(
        device: BLEDevice, advertisement_data: AdvertisementData
    ):
        _LOGGER.info("Found device: %s (%s)", device, device.name)

    def _on_disconnect(self, _: BleakClient):
        """Handle the device disconnecting from this client."""
        self._fire_callbacks(self._callbacks_disconnect)
        self._client = None

    def add_on_disconnect(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device notifications.

        Returns:
             Callable to unsubscribe.

        """
        self._callbacks_disconnect.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks_disconnect.remove(callback)

        return _unsub

    async def send_read_command(self, command: ReadCommands) -> MessageTypes:
        """Request data from the device."""
        return await self.send_command(command=command)

    async def send_write_command(self, command: WriteCommands, value: IntegerValue):
        """Write a value to the device."""
        return await self.send_command(command=command, value=value)

    @overload
    async def send_command(self, command: ReadCommands) -> MessageTypes:
        ...

    @overload
    async def send_command(self, command: WriteCommands, value: IntegerValue):
        ...

    async def send_command(
        self,
        command: Commands,
        value: Optional[IntegerValue] = None,
    ) -> Union[None, MessageTypes]:
        """Send a command to the device."""
        command_config = COMMANDS_MAP[command]
        command_instruction = command_config["instruction"]
        command_array = create_command_array(command_instruction, value)
        handler = command_config.get("handler")

        data = self._loop.create_future()

        async def get_data():
            """Request the data from the device."""
            result = bytearray()

            def on_data_received(_uuid, raw_data):
                """Add each chunk of data to the array until the array is full

                Keep adding to the result until the converted buffer can be completed
                with the received data.

                Once the converted buffer is complete, set it as result to the future
                and mark the future done.

                """
                nonlocal result

                result.extend(raw_data)

                if None in convert_buffer(result):
                    return
                elif not data.done():
                    # End of data.
                    data.set_result(convert_buffer(result))
                else:
                    _LOGGER.debug("Unexpected data received: %s", str(raw_data))

            # Start listening for answers.
            if handler:
                try:
                    await self._client.start_notify(
                        self.CHARACTERISTICS_READ, on_data_received
                    )
                except BleakError as err:
                    # Subsequent subscription raises a BleakError on the bleak_esphome
                    # backend.
                    _LOGGER.debug(
                        "Failed to subscribe to %s: %s", self.CHARACTERISTICS_READ, err
                    )
                    pass

            # Request the data.
            await self._client.write_gatt_char(
                self.CHARACTERISTICS_WRITE, bytes(command_array), response=True
            )

        await self._command_lock.acquire()
        try:
            await get_data()
        except Exception:
            self._command_lock.release()
            raise

        if not handler:
            self._command_lock.release()
            return

        try:
            async with asyncio.timeout(self._RX_DATA_TIMEOUT_SEC):
                await data
        finally:
            self._command_lock.release()

        try:
            message = handler.FromString(bytes(data.result()))
        except DecodeError:
            # TODO: Add error handling.
            raise

        return message

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device notifications.

        Returns:
             Callable to unsubscribe.

        """
        self._callbacks.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks.remove(callback)

        return _unsub

    def _fire_callbacks(self, callbacks: List[Callable]):
        """Execute all callbacks."""
        # Catch errors to not have one callback stop another from being executed.
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                _LOGGER.exception(e)

    async def _poll(self):
        """Repeatedly poll the device status and fire callbacks."""
        while self.is_connected():
            await self.get_sensor_values()
            self._fire_callbacks(self._callbacks)

            await asyncio.sleep(self._poll_interval)

    def start_poll(self, poll_interval: int | None = None):
        """Start polling the device for updates.

        The status will be accessible on ``self.last_status`` once polled.
        Use ``PyAnova.subscribe()`` to get notified.

        Args:
            poll_interval: Interval in seconds.

        """
        if poll_interval:
            self.set_poll_interval(poll_interval)

        if not self._is_poll_started:
            self._is_poll_started = True
            self._task = asyncio.ensure_future(self._poll())

    async def stop_poll(self):
        """Stop polling the device for updates."""
        if self._is_poll_started:
            self._is_poll_started = False
            # Stop task and await it stopped:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    def set_poll_interval(self, interval: int):
        """Set the poll interval in seconds."""
        self._poll_interval = interval

    @staticmethod
    def _get_unit_and_factor(unit: int) -> Tuple[str, int]:
        """Convert the unit into a readable format."""
        if unit == UnitType.DEGREES_C:
            return "C", 1
        elif unit == UnitType.DEGREES_POINT_1C:
            return "C", 10
        elif unit == UnitType.DEGREES_POINT_01C:
            return "C", 100
        elif unit == UnitType.DEGREES_F:
            return "F", 1
        elif unit == UnitType.DEGREES_POINT_1F:
            return "F", 10
        elif unit == UnitType.DEGREES_POINT_01F:
            return "F", 100

        raise ValueError(f"Unknown unit type: {unit}")

    async def get_sensor_values(self) -> SensorValues:
        """Return the current status of the device."""
        sensor_value_list = await self.send_read_command(ReadCommands.GetSensorValues)
        values = iter(sensor_value_list.values)

        water_temp: SensorValue = next(values)
        water_temp_units, water_temp_factor = self._get_unit_and_factor(
            water_temp.units
        )

        heater_temp: SensorValue = next(values)
        heater_temp_units, heater_temp_factor = self._get_unit_and_factor(
            heater_temp.units
        )

        triac_temp: SensorValue = next(values)
        triac_temp_units, triac_temp_factor = self._get_unit_and_factor(
            triac_temp.units
        )

        _unused_temp: SensorValue = next(values)

        internal_temp: SensorValue = next(values)
        internal_temp_units, internal_temp_factor = self._get_unit_and_factor(
            internal_temp.units
        )

        water_low: SensorValue = next(values)
        water_leak: SensorValue = next(values)
        motor_speed: SensorValue = next(values)

        sensor_values = SensorValues(
            water_temp=water_temp.value / water_temp_factor,
            water_temp_units=water_temp_units,
            heater_temp=heater_temp.value / heater_temp_factor,
            heater_temp_units=heater_temp_units,
            triac_temp=triac_temp.value / triac_temp_factor,
            triac_temp_units=triac_temp_units,
            internal_temp=internal_temp.value / internal_temp_factor,
            internal_temp_units=internal_temp_units,
            water_low=bool(water_low.value),
            water_leak=bool(water_leak.value),
            motor_speed=motor_speed.value,
        )

        self._last_sensor_values = sensor_values

        return sensor_values

    async def get_status(self) -> str:
        """Return the current device status (either stopped or running)."""
        self._last_status = await self.send_read_command(ReadCommands.Status)
        print(self._last_status)
        return "stopped" if self._last_sensor_values.motor_speed == 0 else "running"

    async def get_current_temperature(self) -> float:
        """Return the current temperature."""
        return (await self.get_sensor_values()).water_temp

    async def get_target_temperature(self) -> float:
        """Return the target temperature."""
        setpoint = await self.send_read_command(ReadCommands.ReadTargetTemp)
        return setpoint.value / 10

    async def get_timer(self) -> int:
        """Return the remaining timer in minutes."""
        timer = await self.send_read_command(ReadCommands.ReadTimer)
        return timer.value

    async def get_unit(self) -> str:
        """Return the current temperature units (either C or F)."""
        unit = await self.send_read_command(ReadCommands.ReadUnit)
        return self._get_unit_and_factor(unit.value)[0]

    async def start(self):
        """Start cooking."""
        return await self.send_command(ReadCommands.Start)

    async def stop(self):
        """Stop cooking."""
        return await self.send_command(ReadCommands.Stop)

    async def set_timer(self, time_minutes: int):
        """Set the timer in minutes."""
        value = IntegerValue()
        value.value = time_minutes
        return await self.send_write_command(WriteCommands.SetTimer, value)

    async def set_target_temperature(self, temperature: float):
        """Set the temperature in the current units."""
        value = IntegerValue()
        value.value = int(round(temperature * 10))
        return await self.send_write_command(WriteCommands.SetTemp, value)

    async def set_unit(self, unit: str):
        """Set the units to either C or F."""
        value = IntegerValue()
        value.value = UnitType.DEGREES_C if unit.lower() == "c" else UnitType.DEGREES_F
        result = await self.send_write_command(WriteCommands.SetUnit, value)
        await asyncio.sleep(0.1)
        return result

    async def get_device_info(self):
        return await self.send_read_command(ReadCommands.GetDeviceInfo)
