"""Test client interaction.

Responses are extracted from debug logs.

"""

import asyncio
import logging
from typing import Callable
from typing import Optional
from unittest import mock
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

from bleak import BLEDevice
from bleak import BleakClient
import pytest
import pytest_asyncio

from pyanova_nano.client import PyAnova

logging.basicConfig(level=logging.DEBUG)

pytestmark = pytest.mark.asyncio(loop_scope="module")

_CLIENT = None

# Store the notification callbacks
callback_storage = {}

# SensorValues(
#     water_temp=31.4,
#     water_temp_units="C",
#     heater_temp=31.0,
#     heater_temp_units="C",
#     triac_temp=28.0,
#     triac_temp_units="C",
#     internal_temp=29.0,
#     internal_temp_units="C",
#     water_low=False,
#     water_leak=False,
#     motor_speed=0,
# )
_RESPONSE_SENSOR_VALUES_STOPPED = [
    b"\x01\n\x05\n\x07\x08\xc4\x18\x10\x04\x18\x14\n\x06\x08\x1f\x10\x06\x18\x01",
    b"\n\x06\x08\x1c\x10\x06\x18\x02\n\x06\x08\x10\x10\x06\x18\x03\n\x06\x08\x1d",
    b"\x10\x06\x18\x04\n\x06\x08\x08\x10\x03\x18\x05\n\x06\x08\x08\x10\x03\x18\x06",
    b"\n\x06\x08\x05\x10\x02\x18\x07\x00",
]

_RESPONSE_SENSOR_VALUES_RUNNING = [
    b"\x01\n\x05\n\x07\x08\x96\x1a\x10\x04\x18\x14\n\x06\x08#\x10\x06\x18\x01",
    b"\n\x06\x08+\x10\x06\x18\x02\n\x06\x08\x10\x10\x06\x18\x03\n\x06\x08\x1d",
    b"\x10\x06\x18\x04\n\x06\x08\x08\x10\x03\x18\x05\n\x06\x08\x0e\x10\x03\x18\x06",
    b"\n\x07\x08\x9f\x01\x10\x02\x18\x07\x00",
]


async def mock_start_notify(char_uuid, callback):
    callback_storage[char_uuid] = callback
    return True


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def device():
    loop = asyncio.get_running_loop()
    global _CLIENT

    mock_device = MagicMock(spec=BLEDevice)
    mock_device.address = "AA:BB:CC:DD:EE:FF"
    mock_device.name = "MockDevice"

    mock_client = AsyncMock(spec=BleakClient)
    mock_client.is_connected = True
    mock_client.start_notify = mock_start_notify

    _CLIENT = PyAnova(loop, device=mock_device)

    with patch("pyanova_nano.client.establish_connection", return_value=mock_client):
        async with _CLIENT:
            yield _CLIENT


async def simulate_device_response(
    func: Optional[Callable], uuid: str, responses: list[bytes]
):
    """Simulate the device answering to read requests."""
    if func:
        task = asyncio.create_task(func())
    else:
        task = None

    # Let the client request the data.
    await asyncio.sleep(0.01)

    # Simulate data returned by the device in batches.
    for response in responses:
        func = callback_storage[uuid]
        func(uuid, response)

    if task:
        result = await task
        return result


async def test_connect_again(device: PyAnova):
    """Ensure nothing bad happens when we try to connect twice to the device."""
    # Given the client is connected
    client = device.client
    assert client.is_connected

    # When we try to connect again.
    await device.connect()

    # Then the BleakClient remains the same.
    assert device.client is client


async def test_get_status(device: PyAnova):
    sensors = await simulate_device_response(
        device.get_sensor_values,
        device.CHARACTERISTICS_READ,
        _RESPONSE_SENSOR_VALUES_RUNNING,
    )

    assert isinstance(sensors.water_temp, float)
    assert sensors.water_temp_units in ("C", "F")

    assert isinstance(sensors.heater_temp, float)
    assert sensors.heater_temp_units in ("C", "F")

    assert isinstance(sensors.internal_temp, float)

    assert isinstance(sensors.water_low, bool)
    assert isinstance(sensors.water_leak, bool)

    assert isinstance(sensors.motor_speed, int)


async def test_get_set_unit(device: PyAnova):
    """Ensure unit can be read and set."""
    # Given the device is currently set to degrees Celsius.
    current_unit = await simulate_device_response(
        device.get_unit,
        device.CHARACTERISTICS_READ,
        responses=[b"\x01\x03\x07\x08\x01\x00"],
    )
    assert current_unit == "C"

    # When we set the device to degrees Fahrenheit.
    other_unit = "F"
    await device.set_unit(other_unit)
    # Then the device units are set.
    new_unit = await simulate_device_response(
        device.get_unit,
        device.CHARACTERISTICS_READ,
        responses=[b"\x01\x04\x07\x08\x01\x00"],
    )
    assert new_unit == other_unit

    # When we set the units back to degrees Celsius.
    await device.set_unit(current_unit)

    # Then the device units are set.
    new_unit = await simulate_device_response(
        device.get_unit,
        device.CHARACTERISTICS_READ,
        responses=[b"\x01\x03\x07\x08\x01\x00"],
    )
    assert new_unit == current_unit


async def test_get_set_timer(device: PyAnova):
    """Timer can be read and set."""
    await device.set_timer(42)

    new_timer = await simulate_device_response(
        device.get_timer,
        device.CHARACTERISTICS_READ,
        responses=[b"\x01\x04\x12\x08*\x00"],
    )
    assert new_timer == 42


async def test_get_set_target_temperature(device: PyAnova):
    current_temp = await simulate_device_response(
        device.get_target_temperature,
        device.CHARACTERISTICS_READ,
        [b"\x01\x05\x04\x08\xae\x03\x00"],
    )
    assert current_temp == 43.0

    await device.set_target_temperature(42)

    current_temp = await simulate_device_response(
        device.get_target_temperature,
        device.CHARACTERISTICS_READ,
        [b"\x01\x05\x04\x08\xa4\x03\x00"],
    )

    await device.set_target_temperature(current_temp)


async def test_start_stop(device: PyAnova):
    """Start and stop the device."""
    status = await simulate_device_response(
        device.get_status,
        device.CHARACTERISTICS_READ,
        _RESPONSE_SENSOR_VALUES_STOPPED,
    )
    assert status == "stopped"

    # Given we start the device
    await simulate_device_response(
        device.start,
        device.CHARACTERISTICS_READ,
        [b"\x01\x02\n\x00"],
    )
    # On an actual device we should wait for the device to spin up.
    status = await simulate_device_response(
        device.get_status,
        device.CHARACTERISTICS_READ,
        _RESPONSE_SENSOR_VALUES_RUNNING,
    )
    assert status == "running"

    await simulate_device_response(
        device.stop,
        device.CHARACTERISTICS_READ,
        # TODO: Find out content of response.
        responses=[b"\x01\x02\x0b\x00"],
    )


async def test_poll(device):
    """Test subscription to repeated polling."""
    interval = 0.01
    device.set_poll_interval(interval)

    # Given a callable is subscribed to device updates.
    callback = mock.MagicMock()
    device.subscribe(callback)

    # Given we poll the device for some time.
    device.start_poll()

    await simulate_device_response(
        None, device.CHARACTERISTICS_READ, _RESPONSE_SENSOR_VALUES_RUNNING
    )
    await asyncio.sleep(interval / 2)
    await simulate_device_response(
        None, device.CHARACTERISTICS_READ, _RESPONSE_SENSOR_VALUES_RUNNING
    )
    await asyncio.sleep(interval / 2)

    await device.stop_poll()

    # Then the callback has been called.
    assert len(callback.mock_calls) == 2
    # And a device status is accessible.
    assert device.last_status is not None


def test_reconnect(device):
    """Add test to ensure we can safely disconnect and connect."""
    # Given the device is connected.
    assert device.is_connected()

    device.disconnect()
    device.connect()

    device.get_status()
