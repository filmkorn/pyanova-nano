"""Test client interaction.

Note: This requires a device to be available.
TODO: Mock the device.

"""

import asyncio

import pytest
import pytest_asyncio

from pyanova_nano.client import PyAnova

@pytest_asyncio.fixture(scope="session")
async def device(event_loop):
    async with PyAnova() as device:
        yield device


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_get_set_unit(device: PyAnova):
    """Ensure unit can be read and set."""
    current_unit = await device.get_unit()
    other_unit = "C" if current_unit == "F" else "F"

    await device.set_unit(other_unit)
    assert await device.get_unit() == other_unit

    # Restore unit.
    await device.set_unit(current_unit)
    assert (await device.get_unit()) == current_unit


@pytest.mark.asyncio
async def test_get_set_timer(device: PyAnova):
    """Timer can be read and set."""
    await device.set_timer(42)

    assert await device.get_timer() == 42


@pytest.mark.asyncio
async def test_get_set_water_temperature(device: PyAnova):
    current_temp = await device.get_target_temperature()

    await device.set_target_temperature(42)
    assert (await device.get_target_temperature()) == 42

    await device.set_target_temperature(current_temp)


@pytest.mark.asyncio
@pytest.mark.skip("Don't test on an actual live device.")  # TODO: Mock device!
async def test_start_stop(device: PyAnova):
    """Start and stop the device."""
    await device.start()

    await asyncio.sleep(10)

    assert (await device.get_status()) == "running"

    print((await device.get_sensor_values()).motor_speed)

    await device.stop()
