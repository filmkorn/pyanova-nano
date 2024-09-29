"""Test client interaction.

Note: This requires a device to be available.
TODO: Mock the device.

"""

import asyncio
import logging
from unittest import mock

import pytest
import pytest_asyncio

from pyanova_nano.client import PyAnova

logging.basicConfig(level=logging.DEBUG)

pytestmark = pytest.mark.asyncio(loop_scope="module")

_CLIENT = None


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def device():
    loop = asyncio.get_running_loop()
    global _CLIENT

    _CLIENT = PyAnova(loop)

    async with _CLIENT:
        yield _CLIENT


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
    sensors = await device.get_sensor_values()

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
    current_unit = await device.get_unit()
    other_unit = "C" if current_unit == "F" else "F"

    await device.set_unit(other_unit)
    assert await device.get_unit() == other_unit

    # Restore unit.
    await device.set_unit(current_unit)
    assert (await device.get_unit()) == current_unit


@pytest.mark.skip("Don't test on an actual live device.")  # TODO: Mock device!
async def test_get_set_timer(device: PyAnova):
    """Timer can be read and set."""
    await device.set_timer(42)

    assert await device.get_timer() == 42


@pytest.mark.skip("Don't test on an actual live device.")  # TODO: Mock device!
async def test_get_set_water_temperature(device: PyAnova):
    current_temp = await device.get_target_temperature()

    await device.set_target_temperature(42)
    assert (await device.get_target_temperature()) == 42

    await device.set_target_temperature(current_temp)


@pytest.mark.skip("Don't test on an actual live device.")  # TODO: Mock device!
async def test_start_stop(device: PyAnova):
    """Start and stop the device."""
    await device.start()

    await asyncio.sleep(10)

    assert (await device.get_status()) == "running"

    print((await device.get_sensor_values()).motor_speed)

    await device.stop()


async def test_poll(device):
    """Test subscription to repeated polling."""
    device.set_poll_interval(1)

    # Given a callable is subscribed to device updates.
    callback = mock.MagicMock()
    device.subscribe(callback)

    # Given we poll the device for some time.
    device.start_poll()
    await asyncio.sleep(2)
    await device.stop_poll()

    # Then the callable has been called.
    assert len(callback.mock_calls) > 1
    # And a device status is accessible.
    assert device.last_status is not None
