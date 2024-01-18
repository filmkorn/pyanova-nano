import asyncio
import logging
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import overload

from bleak import AdvertisementData
from bleak import BLEDevice
from bleak import BleakClient
from bleak import BleakScanner
from google.protobuf.message import DecodeError

from pyanova_nano.commands import COMMANDS_MAP
from pyanova_nano.commands import convert_buffer
from pyanova_nano.commands import create_command_array
from pyanova_nano.proto.messages_pb2 import IntegerValue
from pyanova_nano.proto.messages_pb2 import SensorValue
from pyanova_nano.proto.messages_pb2 import UnitType
from pyanova_nano.types import MessageTypes
from pyanova_nano.types import Commands
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

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        device: Optional[BLEDevice] = None,
    ):
        self._loop = loop or asyncio.get_running_loop()
        assert self._loop, "Must create an event loop first."

        self._scanner: Optional[BleakScanner] = None
        self._device: Optional[BLEDevice] = device
        self._client: Optional[BleakClient] = None

        self._connected = self._loop.create_future()
        self._scanning = asyncio.Event()

    @property
    def client(self) -> BleakClient:
        """Return the BleakClient instance.

        Note: Only available once connected.

        """
        return self._client

    def is_connected(self) -> bool:
        """Return True if connected to the BLE device."""
        return self._client is not None

    async def connect(self, device: Optional[BLEDevice] = None):
        """Connect to a device.

        Args:
            device: If given, connect to this device. If not given, the client will
                discover the device.

        """
        if not device:
            await self.discover(connect=True, list_all=False)
        else:
            await self._connect(device)

        await self._connected

    async def disconnect(self):
        _LOGGER.info(f"Disconnecting from device: %s", self._client.address)
        # async with self._client as client:
        #     await client.stop_notify(self.CHARACTERISTICS_READ)
        await self._client.disconnect()

    async def _connect(self, device):
        _LOGGER.info("Found device: %s", device.address)
        self._device = device
        self._client = BleakClient(address_or_ble_device=device)
        await self._client.connect()
        self._connected.set_result(True)

    async def __aenter__(self):
        await self.connect()
        await self._connected
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def discover(
        self,
        connect: bool = False,
        list_all: bool = False,
        use_bdaddr=False,
        timeout_seconds=5,
    ) -> List[BLEDevice]:
        """Find a device that provides the service id.

        Raises:
            RuntimeError: If no device was found.

        """
        detection_callback = (
            self._on_discovery_connect if connect else self._on_discover_log
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

        if not list_all and connect and not self.is_connected():
            raise RuntimeError("Could not connect to your Anova Nano.")

        # Filter by service uuid as bleak returns everything it found.
        devices = [
            device
            for device, adv in scanner.discovered_devices_and_advertisement_data.values()
            if self.SERVICE_UUID in adv.service_uuids
        ]
        return devices

    async def _on_discovery_connect(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ):
        """Connect on discovery."""
        # Stop scanning.
        self._scanning.clear()
        await self._connect(device)

    @staticmethod
    async def _on_discover_log(
        device: BLEDevice, advertisement_data: AdvertisementData
    ):
        _LOGGER.info("Found device: %s", device)

    async def _on_disconnect(self):
        """Handle the device disconnecting from this client."""
        self._client = None
        _LOGGER.warning("Anova device disconnected. Trying to reconnect...")
        # TODO: Add retrys.
        await self.connect(self._device)

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

        await self._connected

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
                await self._client.start_notify(
                    self.CHARACTERISTICS_READ, on_data_received
                )

            # Request the data.
            await self._client.write_gatt_char(
                self.CHARACTERISTICS_WRITE, bytes(command_array), response=True
            )

        await get_data()

        # Stopping to listen to the characteristics fails on windows.
        # await self._client.stop_notify(self.CHARACTERISTICS_READ)

        if not handler:
            return

        async with asyncio.timeout(3):
            await data

        try:
            message = handler.FromString(bytes(data.result()))
        except DecodeError:
            # TODO: Add error handling.
            raise

        return message

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

        return sensor_values

    async def get_status(self) -> str:
        """Return the current device status (either stopped or running)."""
        values = await self.get_sensor_values()
        return "stopped" if values.motor_speed == 0 else "running"

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
        return await self.send_write_command(WriteCommands.SetUnit, value)
