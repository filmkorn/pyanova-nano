from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias
from typing import Union

from pyanova_nano.proto.messages_pb2 import FirmwareInfo
from pyanova_nano.proto.messages_pb2 import IntegerValue
from pyanova_nano.proto.messages_pb2 import SensorType
from pyanova_nano.proto.messages_pb2 import SensorValueList


class ReadCommands(StrEnum):
    Start = "START"
    Stop = "STOP"
    GetSensorValues = "GET_SENSORS_VALUES"
    ReadTargetTemp = "READ_TARGET_TEMP"
    ReadUnit = "READ_UNIT"
    ReadTimer = "READ_TIMER"
    GetFirmwareInfo = "GET_FIRMWARE_INFO"


class WriteCommands(StrEnum):
    SetUnit = "SET_UNIT"
    SetTemp = "SET_TEMP"
    SetTimer = "SET_TIMER"


@dataclass
class SensorValues:
    water_temp: float
    water_temp_units: str
    heater_temp: float
    heater_temp_units: str
    triac_temp: float
    triac_temp_units: str
    internal_temp: float
    internal_temp_units: str

    water_low: bool
    water_leak: bool

    motor_speed: int


Commands: TypeAlias = Union[ReadCommands, WriteCommands]
MessageTypes: TypeAlias = Union[SensorType, SensorValueList, FirmwareInfo, IntegerValue]
