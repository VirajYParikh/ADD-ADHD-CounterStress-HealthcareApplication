import sys
import metaml
import pymysql
import logging
import asyncio
import node_connection
from metaml import NodeType
from messaging.message import *
import time

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('ContextService')

available_bots = []
fingerprint = []


def find_start_bots(context, regime, competition_index):
    global available_bots, fingerprint
    data = [(bot_id, competition_index, fingerprint) for bot_id in available_bots]
    return data


def delete_fingerprint(connection: 'pymysql.connections.Connection',
                       bot_index,
                       competition_index):
    query = 'delete from ml_train where bot_index=%s and competition_index=%s'
    logger.info('deleting fingerprint')
    # with connection.cursor() as cursor:
    #     cursor.execute(query, (bot_index, competition_index))
    return True


def add_bots(connection: 'pymysql.Connection',
             context,
             regime,
             competition_index):
    query = 'insert into ml_train(bot_index, competition_index,fingerprint) values (%s,%s,%s)'
    #
    x = tuple(find_start_bots(context, regime, competition_index))
    logger.info('bots added!')
    # with connection.cursor() as cursor:
    #     try:
    #         cursor.executemany(query, x)
    #         connection.commit()
    #     except:
    #         connection.rollback()


async def add_fingerprint(connection: 'pymysql.Connection', context: str, regime: str,
                          competition_index: str):
    business_nodes = await node.nearest_of_type(NodeType.Business)
    response: Message = Message.empty_message()
    if business_nodes and len(business_nodes):
        business_connection = await node_connection.NodeConnection.create_connection(business_nodes[0])
        business_message = Message(message_type=MessageType.QUERY,
                                   message_data=MessageData(method='available_bots_fingerprints',
                                                            args=(context, regime)))
        await business_connection.send_message(business_message)
        response = await business_connection.read_message()
        add_bots(connection=connection, context=context, regime=regime, competition_index=competition_index)
        return response.message_data.decode('utf-8')
    return ''


async def handle_client(reader: 'asyncio.StreamReader', writer: 'asyncio.StreamWriter'):
    connection = node_connection.NodeConnection(reader, writer)
    msg = await connection.read_message()
    if msg.message_type == MessageType.QUERY:
        request_body = metaml.parse_message_data(msg.message_data)
        func, args = request_body.method, request_body.args
        with pymysql.connect(host=metaml.db_host,
                             port=metaml.db_port,
                             user=metaml.db_user,
                             database=metaml.database,
                             password=metaml.db_password) as db_connection:
            response = None
            if func in metaml.context_service_apis:
                if func == 'delete_fingerprint':  # DELETE /fingerprint
                    bot_index, competition_index = args
                    delete_fingerprint(connection=db_connection, competition_index=competition_index,
                                       bot_index=bot_index)
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method='delete_fingerprint', args=None,
                                                                response='fingerprint deleted'))
                elif func == 'add_fingerprint':  # PUT /fingerprint
                    context, regime, competition_index = args[0], args[1], args[2]
                    response = await add_fingerprint(connection=db_connection, context=context,
                                                     regime=regime,
                                                     competition_index=competition_index)
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method='add_fingerprint', args=None, response=response))
            elif func in metaml.business_service_apis:
                await metaml.forward_to(NodeType.Business, node, connection, msg)
            elif func in metaml.taxonomy_service_apis:
                await metaml.forward_to(NodeType.Taxonomy, node, connection, msg)
            elif func in metaml.metrics_service_apis:
                await metaml.forward_to(NodeType.Metrics, node, connection, msg)
            else:
                response = Message(MessageType.ERROR)
            if response:
                await connection.send_message(response)
    elif msg.message_type == MessageType.LIST:
        logger.info('List request received')
        nearest_nodes = await node.nearest_of_type()
        logger.debug(nearest_nodes)
        await connection.send_message(Message(MessageType.RESPONSE,
                                              MessageData(method=None, args=None,
                                                          response=nearest_nodes)))

    elif msg.message_type == MessageType.PING:
        await connection.send_message(Message(MessageType.HELO, ))


port, bootstrap_node = metaml.fetch_args()
node = metaml.MetaMLNode(node_type=NodeType.Context,
                         client_handler=handle_client,
                         port=port,
                         bootstrap_node=bootstrap_node)
asyncio.run(node.init_dht())
