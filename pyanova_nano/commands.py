from typing import List
from typing import Optional

from pyanova_nano.proto import messages_pb2
from pyanova_nano.proto.messages_pb2 import IntegerValue
from pyanova_nano.types import ReadCommands
from pyanova_nano.types import WriteCommands


def encode_command(buffer: bytes, i: bool) -> bytes:
    result = [0]
    last_value = 0
    current_index = 1

    def reset_index(is_end: bool):
        nonlocal last_value
        nonlocal current_index
        result[last_value] = current_index
        last_value = len(result)
        if is_end:
            result.append(0)
        current_index = 1

    for u in range(len(buffer)):
        if buffer[u] == 0:
            reset_index(True)
        else:
            result.append(buffer[u])
            current_index += 1
            if current_index == 255:
                reset_index(True)
    reset_index(False)
    if i:
        result.append(0)
    return bytes(result)


def create_command_array(
    message_type: messages_pb2.ConfigDomainMessageType,
    value: Optional[IntegerValue] = None,
) -> bytes:
    command = [messages_pb2.DomainType.ANOVA_DOMAIN_ID_CONFIG, message_type]
    if value:
        command.extend(list(value.SerializeToString()))

    command = bytes(command)
    command = encode_command(command, True)

    return command


def convert_buffer(raw_data: bytearray) -> List:
    results = []
    data = raw_data[:-1]
    i = 0
    while i < (len(data) - 1):
        block_length = data[i]
        i += 1
        for k in range(1, block_length):
            try:
                results.append(data[i])
            except IndexError:
                results.append(None)
            i += 1
        if block_length < 255 and i < len(data):
            results.append(0)
    return results[2:]


COMMANDS_MAP = {
    ReadCommands.GetSensorValues: {
        "instruction": messages_pb2.ConfigDomainMessageType.GET_SENSORS,
        "handler": messages_pb2.SensorValueList,
    },
    ReadCommands.ReadTargetTemp: {
        "instruction": messages_pb2.ConfigDomainMessageType.GET_TEMP_SETPOINT,
        "handler": messages_pb2.IntegerValue,
    },
    ReadCommands.ReadTimer: {
        "instruction": messages_pb2.ConfigDomainMessageType.GET_COOKING_TIMER,
        "handler": messages_pb2.IntegerValue,
    },
    ReadCommands.GetFirmwareInfo: {
        "instruction": messages_pb2.ConfigDomainMessageType.GET_FIRMWARE_INFO,
        "handler": messages_pb2.FirmwareInfo,
    },
    ReadCommands.Start: {
        "instruction": messages_pb2.ConfigDomainMessageType.START_COOKING,
        "handler": messages_pb2.SensorValueList,
    },
    ReadCommands.Stop: {
        "instruction": messages_pb2.ConfigDomainMessageType.STOP_COOKING,
        "handler": messages_pb2.SensorValueList,
    },
    ReadCommands.ReadUnit: {
        "instruction": messages_pb2.ConfigDomainMessageType.GET_TEMP_UNITS,
        "handler": messages_pb2.IntegerValue,
    },
    WriteCommands.SetUnit: {
        "instruction": messages_pb2.ConfigDomainMessageType.SET_TEMP_UNITS,
    },
    WriteCommands.SetTemp: {
        "instruction": messages_pb2.ConfigDomainMessageType.SET_TEMP_SETPOINT
    },
    WriteCommands.SetTimer: {
        "instruction": messages_pb2.ConfigDomainMessageType.SET_COOKING_TIMER
    },
}
