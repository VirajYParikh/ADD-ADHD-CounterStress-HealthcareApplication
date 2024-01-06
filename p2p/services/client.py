import asyncio

import node_connection
from messaging import message


# business_service - 1203
# context_service - 1300
# metrics_service - 1100
# taxonomy_service - 1200

def print_response(msg: 'message.Message'):
    print(f'msg_type = {msg.message_type}')
    print(f'length   = {msg.message_length}')
    print(f'data     = {msg.message_data}')


async def test(msg: 'message.Message', endpoint: str) -> 'message.Message':
    connection = await node_connection.NodeConnection.create_connection(endpoint)
    await connection.send_message(msg)
    return await connection.read_message()


async def test_bot_predict() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='predict_bots',
                                                           args=(
                                                               '51661099211,11661075508,21661075508,31661075508,41661099211',
                                                               ['ZBH0_MBO', 'buy'], 3)))
    return await test(msg, '192.168.1.163:1203')


async def test_bot_rank() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='bot_rank',
                                                           args=(2, 2022080111, 10001, 5)))

    return await test(msg, '10.0.0.142:1100')


async def test_add_business_problem() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='add_business_problem',
                                                           args=('a', 'b')))
    return await test(msg, '10.0.0.142:1200')


async def test_add_domain() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='add_domain',
                                                           args=('51661099212', 'Sports')))
    return await test(msg, '10.0.0.142:1200')


async def test_add_dimension() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='add_dimension',
                                                           args=('11661075509', 'Europe Market')))
    return await test(msg, '10.0.0.142:1200')


async def test_add_customer_profile() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='add_customer_profile',
                                                           args=('41661099212', 'JPM')))
    return await test(msg, '10.0.0.142:1200')


async def test_delete_fingerprint() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='delete_fingerprint',
                                                           args=(
                                                               '49766696-84a2-11ed-b0a9-b65161bf9f88',
                                                               '10001'
                                                           )))
    return await test(msg, '10.0.0.142:1300')


async def test_add_fingerprint() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='add_fingerprint',
                                                           args=(
                                                               '51661099211,11661075508,21661075508,31661075508,41661099211',
                                                               ['ZBH0_MBO', 'buy'],
                                                               '49766696-84a2-11ed-b0a9-b65161bf9f88')))
    return await test(msg, '10.0.0.142:1300')


print_response(asyncio.run(test_bot_predict()))
#print_response(asyncio.run(test_delete_fingerprint()))
# print_response(asyncio.run(test_add_business_problem()))
# print_response(asyncio.run(test_add_customer_profile()))
# print_response(asyncio.run(test_add_dimension()))
# print_response(asyncio.run(test_add_domain()))
# print_response(asyncio.run(test_bot_rank()))
# print_response(asyncio.run(test_add_fingerprint()))
# print_response(asyncio.run(test_bot_predict_send_to_different_service()))
