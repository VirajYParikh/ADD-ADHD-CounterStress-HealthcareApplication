import struct
import asyncio
import logging
import traceback
from typing import Union, Optional

from messaging import message


class NodeConnection:
    logger: 'logging.Logger' = logging.getLogger('NodeConnection')

    @classmethod
    async def create_connection(cls, node_address: str) -> Optional['NodeConnection']:
        _host, _port = node_address.split(':')
        reader, writer = None, None
        cls.logger.debug('connecting to %s:%s', _host, _port)
        try:
            reader, writer = await asyncio.open_connection(host=_host, port=_port, )

        except ConnectionRefusedError as cre:
            traceback.print_exc()
            NodeConnection.logger.debug('connection refused %d:%d', _host, _port)

        return None if not reader or not writer else NodeConnection(reader=reader, writer=writer)

    def __init__(self, reader: 'asyncio.StreamReader' = None, writer: 'asyncio.StreamWriter' = None):
        self.__reader = reader
        self.__writer = writer

    @property
    def reader(self) -> 'asyncio.StreamReader':
        return self.__reader

    @property
    def writer(self) -> 'asyncio.StreamWriter':
        return self.__writer

    async def send_message(self, msg: Union['message.Message', 'asyncio.Task']):
        if asyncio.iscoroutine(msg):
            msg = await msg
        self.__writer.write(bytes(msg))
        await self.__writer.drain()

    async def read_message(self) -> 'message.Message':
        msg_type = message.MessageType.NOOP
        msg_data = b''
        try:
            msg_type = await self.__reader.read(4)
            self.logger.debug(f'message type={msg_type}')
            if not msg_type:
                return message.Message.empty_message()
            msg_type = message.MessageType.from_label(msg_type)
            if msg_type is message.MessageType.NOOP:
                return message.Message.empty_message()
            len_str = await self.__reader.read(4)
            msg_len = int(struct.unpack("!L", len_str)[0])
            while len(msg_data) != msg_len:
                data = await self.__reader.read(min(2048, msg_len - len(msg_data)))
                if not len(data):
                    break
                msg_data += data
            if len(msg_data) != msg_len:
                return message.Message.empty_message()
        except KeyboardInterrupt:
            pass
        except Exception as ex:
            self.logger.error(ex)
            traceback.print_exc()
            return message.Message.empty_message()
        return message.Message(msg_type, msg_data)
