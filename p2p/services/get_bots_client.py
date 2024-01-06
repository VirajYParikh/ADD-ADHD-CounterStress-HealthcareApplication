import asyncio
from node_connection import NodeConnection

from services.messaging.message import Message, MessageType, MessageData


async def test(msg: 'Message') -> 'Message':
    connection = await NodeConnection.create_connection('10.0.0.142:1300')
    await connection.send_message(message)
    return await connection.read_message()


message = Message(message_type=MessageType.QUERY,
                  message_data=MessageData(method='get_bots_from_index',
                                           args=('51661099211,11661075508,21661075508,31661075508,41661099211',)))

response = asyncio.run(test(message))

print(response.message_type)
print(response.message_length)
print(MessageData.from_bytes(response.message_data))
