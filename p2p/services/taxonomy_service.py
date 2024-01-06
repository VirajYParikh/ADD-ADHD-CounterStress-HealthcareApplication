import sys
import time
import logging
import asyncio

import metaml
import pymysql
import node_connection
from metaml import NodeType
from messaging.message import MessageType
from messaging.message import Message, MessageData

node_type = NodeType.Taxonomy

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('TaxonomyService')


def is_admin(connection: 'pymysql.Connection', user: str) -> bool:
    sql = 'select * from meta_ml.admin_users where Username=%s'
    with connection.cursor() as cursor:
        cursor.execute(sql, user)
        return cursor.fetchone() is not None


def time_index(characteristic: str):
    millis = '0'
    if characteristic.lower() == 'dimension':
        millis = '1' + str(round(time.time()))
    elif characteristic.lower() == 'application_area':
        millis = '2' + str(round(time.time()))
    elif characteristic.lower() == 'business_problem':
        millis = '3' + str(round(time.time()))
    elif characteristic.lower() == 'customer_profile':
        millis = '4' + str(round(time.time()))
    elif characteristic.lower() == 'domains':
        millis = '5' + str(round(time.time()))
    return int(millis)


def add_item(connection: 'pymysql.Connection', characteristic: str, user: str, item: str):
    index = str(time_index(characteristic=characteristic))
    sql = f'insert into {characteristic} values(%s, %s)'
    if is_admin(connection=connection, user=user):
        logger.info('Adding item to table')
        with connection.cursor() as cursor:
            cursor.execute(sql, (index, item))
    return True


def delete_item(connection: 'pymysql.Connection', characteristic: str, user: str, item: str, ):
    sql = f'delete from {characteristic} where name=%s'
    if is_admin(connection=connection, user=user):
        logger.info('Deleting item from table')
        with connection.cursor() as cursor:
            cursor.execute(sql, item)
    return True


def add_business_problem(connection: 'pymysql.Connection', user: str, item: str, ) -> bool:
    return add_item(connection=connection, user=user, characteristic='business_problem', item=item, )


def delete_business_problem(connection: 'pymysql.Connection', user: str, item: str) -> bool:
    return delete_item(connection=connection, characteristic='business_problem', user=user, item=item)


def add_customer_profile(connection: 'pymysql.Connection', user: str, item: str, ) -> bool:
    return add_item(connection=connection, user=user, characteristic='customer_profile', item=item, )


def delete_customer_profile(connection: 'pymysql.Connection', user: str, item: str) -> bool:
    return delete_item(connection=connection, characteristic='customer_profile', user=user, item=item)


def add_application_area(connection: 'pymysql.Connection', user: str, item: str, ) -> bool:
    return add_item(connection=connection, user=user, characteristic='application_area', item=item, )


def delete_application_area(connection: 'pymysql.Connection', user: str, item: str) -> bool:
    return delete_item(connection=connection, characteristic='application_area', user=user, item=item)


def add_domain(connection: 'pymysql.Connection', user: str, item: str, ) -> bool:
    return add_item(connection=connection, user=user, characteristic='domain', item=item, )


def delete_domain(connection: 'pymysql.Connection', user: str, item: str) -> bool:
    return delete_item(connection=connection, characteristic='domain', user=user, item=item)


def add_dimension(connection: 'pymysql.Connection', user: str, item: str, ) -> bool:
    return add_item(connection=connection, user=user, characteristic='dimension', item=item, )


def delete_dimension(connection: 'pymysql.Connection', user: str, item: str) -> bool:
    return delete_item(connection=connection, characteristic='dimension', user=user, item=item)


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
            if func in metaml.taxonomy_service_apis:
                user, item = args
                if func == 'add_business_problem':
                    response = add_business_problem(connection=db_connection, user=user, item=item, )
                elif func == 'add_customer_profile':
                    response = add_customer_profile(connection=db_connection, user=user, item=item, )
                elif func == 'add_application_area':
                    response = add_application_area(connection=db_connection, user=user, item=item, )
                elif func == 'add_domain':
                    response = add_domain(connection=db_connection, user=user, item=item, )
                elif func == 'add_dimension':
                    response = add_dimension(connection=db_connection, user=user, item=item, )
                elif func == 'delete_business_problem':
                    response = delete_business_problem(connection=db_connection, user=user, item=item, )
                elif func == 'delete_customer_profile':
                    response = delete_customer_profile(connection=db_connection, user=user, item=item, )
                elif func == 'delete_application_area':
                    response = delete_application_area(connection=db_connection, user=user, item=item, )
                elif func == 'delete_domain':
                    response = delete_domain(connection=db_connection, user=user, item=item, )
                elif func == 'delete_dimension':
                    response = delete_dimension(connection=db_connection, user=user, item=item, )
                if response:
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method=None, args=None, response='done'))
                else:
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method=None, args=None, response='error'))
            elif func in metaml.business_service_apis:
                await metaml.forward_to(NodeType.Business, node, connection, msg)
            elif func in metaml.context_service_apis:
                asyncio.get_event_loop().create_task(metaml.forward_to(NodeType.Context, node, connection, msg))
            elif func in metaml.metrics_service_apis:
                asyncio.get_event_loop().create_task(metaml.forward_to(NodeType.Metrics, node, connection, msg))
            else:
                response = Message(MessageType.ERROR)
            if response:
                await connection.send_message(response)
    elif msg.message_type == MessageType.LIST:
        logger.info('List request received')
        nearest_nodes = await node.nearest_of_type()
        logger.debug(nearest_nodes)
        await connection.send_message(Message(MessageType.RESPONSE,
                                              MessageData(method=None, args=None, response=nearest_nodes)))

    elif msg.message_type == MessageType.PING:
        await connection.send_message(Message(MessageType.HELO, ))


port, bootstrap_node = metaml.fetch_args()

node = metaml.MetaMLNode(node_type=NodeType.Taxonomy,
                         client_handler=handle_client,
                         port=port,
                         bootstrap_node=bootstrap_node)
asyncio.run(node.init_dht())
