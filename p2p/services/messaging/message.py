import enum
import logging
import struct
from typing import Union, Tuple
from dataclasses import dataclass, field
from typing import List, Any, Optional
import json


class MessageType(enum.Enum):
    NOOP = 'NOOP'
    NAME = 'NAME'
    LIST = 'LIST'
    QUIT = 'QUIT'
    PING = 'PING'
    HELO = 'HELO'
    JOIN = 'JOIN'
    QUERY = 'QUER'
    ERROR = 'ERRO'
    RESPONSE = 'RESP'

    @staticmethod
    def from_label(label: Union[str, bytes]):
        if label == 'NOOP' or label == b'NOOP':
            return MessageType.NOOP
        elif label == 'NAME' or label == b'NAME':
            return MessageType.NAME
        elif label == 'LIST' or label == b'LIST':
            return MessageType.LIST
        elif label == 'QUIT' or label == b'QUIT':
            return MessageType.QUIT
        elif label == 'PING' or label == b'PING':
            return MessageType.PING
        elif label == 'JOIN' or label == b'JOIN':
            return MessageType.JOIN
        elif label == 'QUER' or label == b'QUER':
            return MessageType.QUERY
        elif label == 'ERRO' or label == b'ERRO':
            return MessageType.ERROR
        elif label == 'RESP' or label == b'RESP':
            return MessageType.RESPONSE
        elif label == 'HELO' or label == b'HELO':
            return MessageType.HELO
        else:
            print(label, ' not implemented')
            raise NotImplementedError

    def __bytes__(self):
        return self.value.encode('utf-8')


@dataclass
class MessageData:
    method: Optional[str]
    args: Optional[Tuple]
    response: Any = None

    @staticmethod
    def from_json(msg_body: str) -> 'MessageData':
        obj = json.loads(msg_body)
        return MessageData(method=obj['method'], args=obj['args'])

    @staticmethod
    def from_bytes(msg_body: bytes) -> 'MessageData':
        return MessageData.from_json(msg_body.decode('utf-8'))

    def __bytes__(self):
        return self.__str__().encode('utf-8')

    def __str__(self):
        return json.dumps(self.__dict__)


@dataclass
class Message:
    message_type: MessageType
    message_data: Union[bytes, str, MessageData] = field(default=b"")
    message_length: int = field(init=False, compare=False)

    def __post_init__(self):
        if isinstance(self.message_data, str):
            self.message_data = self.message_data.encode('utf-8')
        elif isinstance(self.message_data, MessageData):
            self.message_data = bytes(self.message_data)
        self.message_length = len(self.message_data)

    def __bytes__(self) -> bytes:
        return struct.pack(f"!4sL{self.message_length}s",
                           bytes(self.message_type),
                           self.message_length,
                           self.message_data)

    def __str__(self) -> str:
        return self.__bytes__().decode('utf-8')

    @staticmethod
    def list_message() -> 'Message':
        return Message(MessageType.LIST, b'')

    @staticmethod
    def ping_message() -> 'Message':
        return Message(MessageType.PING, b'')

    @staticmethod
    def name_message() -> 'Message':
        return Message(MessageType.NAME, b'')

    @staticmethod
    def insert_message(peer_id: str, host: str, port: int) -> 'Message':
        return Message(MessageType.JOIN, f'{peer_id} {host} {port}'.encode('utf-8'))

    @staticmethod
    def empty_message() -> 'Message':
        return Message(MessageType.NOOP, '')
