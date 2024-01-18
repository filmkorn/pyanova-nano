from typing import ClassVar as _ClassVar
from typing import Iterable as _Iterable
from typing import Mapping as _Mapping
from typing import Optional as _Optional
from typing import Union as _Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class DomainType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ANOVA_DOMAIN_ID_CONFIG: _ClassVar[DomainType]
    ANOVA_DOMAIN_ID_BULK_TRANSFER: _ClassVar[DomainType]
    ANOVA_DOMAIN_ID_COUNT: _ClassVar[DomainType]

class SensorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WaterTemp: _ClassVar[SensorType]
    HeaterTemp: _ClassVar[SensorType]
    TriacTemp: _ClassVar[SensorType]
    UnusedTemp: _ClassVar[SensorType]
    InternalTemp: _ClassVar[SensorType]
    WaterLow: _ClassVar[SensorType]
    WaterLeak: _ClassVar[SensorType]
    MotorSpeed: _ClassVar[SensorType]

class UnitType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DEGREES_POINT_1C: _ClassVar[UnitType]
    DEGREES_POINT_1F: _ClassVar[UnitType]
    MOTOR_SPEED: _ClassVar[UnitType]
    BOOLEAN: _ClassVar[UnitType]
    DEGREES_POINT_01C: _ClassVar[UnitType]
    DEGREES_POINT_01F: _ClassVar[UnitType]
    DEGREES_C: _ClassVar[UnitType]
    DEGREES_F: _ClassVar[UnitType]

class ConfigDomainMessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOOPBACK: _ClassVar[ConfigDomainMessageType]
    CLI_TEXT: _ClassVar[ConfigDomainMessageType]
    SAY_HELLO: _ClassVar[ConfigDomainMessageType]
    SET_TEMP_SETPOINT: _ClassVar[ConfigDomainMessageType]
    GET_TEMP_SETPOINT: _ClassVar[ConfigDomainMessageType]
    GET_SENSORS: _ClassVar[ConfigDomainMessageType]
    SET_TEMP_UNITS: _ClassVar[ConfigDomainMessageType]
    GET_TEMP_UNITS: _ClassVar[ConfigDomainMessageType]
    SET_COOKING_POWER_LEVEL: _ClassVar[ConfigDomainMessageType]
    GET_COOKING_POWER_LEVEL: _ClassVar[ConfigDomainMessageType]
    START_COOKING: _ClassVar[ConfigDomainMessageType]
    STOP_COOKING: _ClassVar[ConfigDomainMessageType]
    SET_SOUND_LEVEL: _ClassVar[ConfigDomainMessageType]
    GET_SOUND_LEVEL: _ClassVar[ConfigDomainMessageType]
    SET_DISPLAY_BRIGHTNESS: _ClassVar[ConfigDomainMessageType]
    GET_DISPLAY_BRIGHTNESS: _ClassVar[ConfigDomainMessageType]
    SET_COOKING_TIMER: _ClassVar[ConfigDomainMessageType]
    STOP_COOKING_TIMER: _ClassVar[ConfigDomainMessageType]
    GET_COOKING_TIMER: _ClassVar[ConfigDomainMessageType]
    CANCEL_COOKING_TIMER: _ClassVar[ConfigDomainMessageType]
    SET_CHANGE_POINT: _ClassVar[ConfigDomainMessageType]
    CHANGE_POINT: _ClassVar[ConfigDomainMessageType]
    SET_BLE_PARAMS: _ClassVar[ConfigDomainMessageType]
    BLE_PARAMS: _ClassVar[ConfigDomainMessageType]
    GET_DEVICE_INFO: _ClassVar[ConfigDomainMessageType]
    GET_FIRMWARE_INFO: _ClassVar[ConfigDomainMessageType]
    SYSTEM_ALERT_VECTOR: _ClassVar[ConfigDomainMessageType]
    RESERVED28: _ClassVar[ConfigDomainMessageType]
    MESSAGE_SPOOF: _ClassVar[ConfigDomainMessageType]

ANOVA_DOMAIN_ID_CONFIG: DomainType
ANOVA_DOMAIN_ID_BULK_TRANSFER: DomainType
ANOVA_DOMAIN_ID_COUNT: DomainType
WaterTemp: SensorType
HeaterTemp: SensorType
TriacTemp: SensorType
UnusedTemp: SensorType
InternalTemp: SensorType
WaterLow: SensorType
WaterLeak: SensorType
MotorSpeed: SensorType
DEGREES_POINT_1C: UnitType
DEGREES_POINT_1F: UnitType
MOTOR_SPEED: UnitType
BOOLEAN: UnitType
DEGREES_POINT_01C: UnitType
DEGREES_POINT_01F: UnitType
DEGREES_C: UnitType
DEGREES_F: UnitType
LOOPBACK: ConfigDomainMessageType
CLI_TEXT: ConfigDomainMessageType
SAY_HELLO: ConfigDomainMessageType
SET_TEMP_SETPOINT: ConfigDomainMessageType
GET_TEMP_SETPOINT: ConfigDomainMessageType
GET_SENSORS: ConfigDomainMessageType
SET_TEMP_UNITS: ConfigDomainMessageType
GET_TEMP_UNITS: ConfigDomainMessageType
SET_COOKING_POWER_LEVEL: ConfigDomainMessageType
GET_COOKING_POWER_LEVEL: ConfigDomainMessageType
START_COOKING: ConfigDomainMessageType
STOP_COOKING: ConfigDomainMessageType
SET_SOUND_LEVEL: ConfigDomainMessageType
GET_SOUND_LEVEL: ConfigDomainMessageType
SET_DISPLAY_BRIGHTNESS: ConfigDomainMessageType
GET_DISPLAY_BRIGHTNESS: ConfigDomainMessageType
SET_COOKING_TIMER: ConfigDomainMessageType
STOP_COOKING_TIMER: ConfigDomainMessageType
GET_COOKING_TIMER: ConfigDomainMessageType
CANCEL_COOKING_TIMER: ConfigDomainMessageType
SET_CHANGE_POINT: ConfigDomainMessageType
CHANGE_POINT: ConfigDomainMessageType
SET_BLE_PARAMS: ConfigDomainMessageType
BLE_PARAMS: ConfigDomainMessageType
GET_DEVICE_INFO: ConfigDomainMessageType
GET_FIRMWARE_INFO: ConfigDomainMessageType
SYSTEM_ALERT_VECTOR: ConfigDomainMessageType
RESERVED28: ConfigDomainMessageType
MESSAGE_SPOOF: ConfigDomainMessageType

class FirmwareInfo(_message.Message):
    __slots__ = ("commitId", "tagId", "dateCode")
    COMMITID_FIELD_NUMBER: _ClassVar[int]
    TAGID_FIELD_NUMBER: _ClassVar[int]
    DATECODE_FIELD_NUMBER: _ClassVar[int]
    commitId: str
    tagId: str
    dateCode: int
    def __init__(
        self,
        commitId: _Optional[str] = ...,
        tagId: _Optional[str] = ...,
        dateCode: _Optional[int] = ...,
    ) -> None: ...

class IntegerValue(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: _Optional[int] = ...) -> None: ...

class SensorValue(_message.Message):
    __slots__ = ("value", "units", "sensorType")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UNITS_FIELD_NUMBER: _ClassVar[int]
    SENSORTYPE_FIELD_NUMBER: _ClassVar[int]
    value: int
    units: UnitType
    sensorType: SensorType
    def __init__(
        self,
        value: _Optional[int] = ...,
        units: _Optional[_Union[UnitType, str]] = ...,
        sensorType: _Optional[_Union[SensorType, str]] = ...,
    ) -> None: ...

class SensorValueList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[SensorValue]
    def __init__(
        self, values: _Optional[_Iterable[_Union[SensorValue, _Mapping]]] = ...
    ) -> None: ...
