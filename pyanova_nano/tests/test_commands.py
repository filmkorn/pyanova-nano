from pyanova_nano.commands import convert_buffer
from pyanova_nano.commands import create_command_array
from pyanova_nano.commands import encode_command
from pyanova_nano.proto import messages_pb2
from pyanova_nano.proto.messages_pb2 import IntegerValue
from pyanova_nano.proto.messages_pb2 import SensorValue
from pyanova_nano.proto.messages_pb2 import SensorValueList
from pyanova_nano.proto.messages_pb2 import UnitType


def test_encode_command():
    assert encode_command(bytearray([0, 5]), True) == bytearray([1, 2, 5, 0])


def test_create_command_array():
    assert create_command_array(
        messages_pb2.ConfigDomainMessageType.GET_SENSORS
    ) == bytearray(
        [
            1,
            2,
            5,
            0,
        ]
    )


def test_create_command_value_array():
    value = messages_pb2.IntegerValue()
    value.value = 2
    result = list(
        create_command_array(messages_pb2.ConfigDomainMessageType.SET_TEMP_UNITS, value)
    )

    assert result == [1, 4, 6, 8, 2, 0]


def test_convert_buffer_incomplete():
    result = convert_buffer(
        bytearray(
            b"\x01\n\x05\n\x07\x08\xf2\x11\x10\x04\x18\x14\n\x06\x08\x16\x10\x06\x18\x01"
        )
    )
    expected = [
        10,
        7,
        8,
        242,
        17,
        16,
        4,
        24,
        0,
        10,
        6,
        8,
        22,
        16,
        6,
        24,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]
    assert result == expected


def test_convert_buffer_complete():
    data_array = bytearray(
        b"\x01\n\x05\n\x07\x08\x8c\x10\x10\x04\x18\x14\n\x06\x08\x14\x10\x06\x18\x01\n\x06\x08\x15\x10\x06\x18\x02\n\x06\x08\x18\x10\x06\x18\x03\n\x06\x08\x19\x10\x06\x18\x04\n\x06\x08\x01\x10\x03\x18\x05\n\x06\x08\x08\x10\x03\x18\x06\n\x06\x08\x05\x10\x02\x18\x07\x00"
    )
    expected = [
        # 5,
        10,
        7,
        8,
        140,
        16,
        16,
        4,
        24,
        0,
        10,
        6,
        8,
        20,
        16,
        6,
        24,
        1,
        10,
        6,
        8,
        21,
        16,
        6,
        24,
        2,
        10,
        6,
        8,
        0,
        16,
        6,
        24,
        3,
        10,
        6,
        8,
        25,
        16,
        6,
        24,
        4,
        10,
        6,
        8,
        1,
        16,
        3,
        24,
        5,
        10,
        6,
        8,
        0,
        16,
        3,
        24,
        6,
        10,
        6,
        8,
        0,
        16,
        2,
        24,
        7,
    ]
    assert convert_buffer(data_array) == expected


def test_read_integer_value_from_response():
    data = bytearray(b"\x01\x05\x04\x08\xa4\x03\x00")
    converted = convert_buffer(data)

    int_value = IntegerValue.FromString(bytes(converted))

    assert int_value.value / 10 == 42


def test_decode_sensor_value_list_from_response():
    data = bytearray(
        b"\x01\n\x05\n\x07\x08\xd2\x10\x10\x04\x18\x14\n\x06\x08\x14\x10\x06\x18\x01\n\x06\x08\x16\x10\x06\x18\x02\n\x06\x08\x18\x10\x06\x18\x03\n\x06\x08\x19\x10\x06\x18\x04\n\x06\x08\x01\x10\x03\x18\x05\n\x06\x08\x08\x10\x03\x18\x06\n\x06\x08\x05\x10\x02\x18\x07\x00"
    )

    converted = convert_buffer(data)

    svl = SensorValueList.FromString(bytes(converted))
    values = iter(svl.values)

    water_temp: SensorValue = next(values)
    assert isinstance(water_temp, SensorValue)
    assert water_temp.value / 100 == 21.3
    assert water_temp.units == UnitType.DEGREES_POINT_01C

    heater_temp: SensorValue = next(values)
    assert heater_temp.value == 20
    assert heater_temp.units == UnitType.DEGREES_C

    triac_temp: SensorValue = next(values)
    assert triac_temp.value == 22
    assert triac_temp.units == UnitType.DEGREES_C

    _unused_temp: SensorValue = next(values)

    internal_temp: SensorValue = next(values)
    assert internal_temp.value == 25
    assert internal_temp.units == UnitType.DEGREES_C

    water_low: SensorValue = next(values)
    assert isinstance(water_low, SensorValue)

    assert water_low.value == 1
    assert water_low.units == UnitType.BOOLEAN

    water_leak: SensorValue = next(values)
    assert water_leak.value == 0
    assert water_leak.units == UnitType.BOOLEAN

    motor_speed: SensorValue = next(values)
    assert motor_speed.value == 0
    assert motor_speed.units == UnitType.MOTOR_SPEED
