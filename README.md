# PyAnova-Nano

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)


Control the Anova Nano via BLE.

This is a rough translation of [dengelke/node-sous-vide](https://github.com/dengelke/node-sous-vide/).

Notes:
- The code should be considered experimental at this point.
- Presumably this library is not compatible with any other Anova model!
- The PyAnova class is not compatible with [c3V6a2Vy/pyanova](https://github.com/c3V6a2Vy/pyanova).

# Examples

### Automatic discovery

#### Context manager: auto connect and disconnect

```python
import asyncio
from pyanova_nano import PyAnova

async def print_device_sensors():
    async with PyAnova() as client:
        print(await client.get_sensor_values())

asyncio.run(print_device_sensors())
```

#### No context manager

```python
import asyncio

from pyanova_nano import PyAnova


async def stop_anova():
    client = PyAnova()
    await client.connect()

    print(await client.get_timer())
    await asyncio.sleep(0.5)
    print(await client.get_unit())

    await client.disconnect()


asyncio.run(stop_anova())
```

### Manual connection
```python
import asyncio

from bleak import BLEDevice

from pyanova_nano import PyAnova


async def print_target_temp():
    client = PyAnova()
    devices: list[BLEDevice] = await client.discover(connect=False, list_all=True)
    device = next(iter(devices))

    print(f"Found: {device.address}")

    await client.connect(device)

    temperature = await client.get_target_temperature()
    print(temperature)
    
    await client.disconnect()


asyncio.run(print_target_temp())

```

# Disclaimer

This software may harm your device. Use it at your own risk.

THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
