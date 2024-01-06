import sys
import logging
from typing import Union

import numpy as np
from sklearn import preprocessing
import pymysql
from messaging.message import Message, MessageData
from messaging.message import MessageType
import metaml
from metaml import NodeType
import node_connection
import asyncio

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('MetricsService')

available_bots = []
competition_result = {}
normalized_competition_result = {}
bot_num = 0


def update_availability_score(connection: 'pymysql.Connection', bot):
    logger.info("Updating availability scores in table Metrics")
    sql_exist = "SELECT * from Metrics WHERE EXISTS(SELECT * FROM Metrics WHERE bot_index = %s)"
    sql_update = "UPDATE Metrics SET availability_score = (%s) WHERE bot_index = (%s)"
    sql_insert = "INSERT INTO " \
                 "Metrics (bot_index, use_times, suitability_score, availability_score) " \
                 "VALUES (%s , %s, %s , %s)"
    if not bot:
        logger.error("No bots are available. Availability scores unchanged")
    else:
        with connection.cursor() as cursor:
            for index in bot:
                cursor.execute(sql_exist, (index,))
                # check whether this bot exist in metrics
                record = cursor.fetchone()
                # if this bot exist, then update its availability score
                if record:
                    # get the record
                    sql_select = "SELECT * from Metrics WHERE bot_index = %s"
                    cursor.execute(sql_select, (index,))
                    records = cursor.fetchall()
                    # recalculate the availability score
                    new_available_score = records[0][3] + 1
                    val = (new_available_score, index)
                    # update dabase
                    cursor.execute(sql_update, val)
                    logger.info("Bot %s already exists, now updating its availability score", index)
                # if this bot doesn't exist, then add the record into database
                else:
                    # if not exist, then set use times=0 suitability score = 0
                    new_available_score = 1
                    use_times = 0
                    suitability_score = 0
                    val = (index, use_times, suitability_score, new_available_score)
                    # insert new record into database
                    cursor.execute(sql_insert, val)
                    logger.info("Bot %s is a new bot, now adding this record", index)
            logger.info("Now table Metrics is updated successfully")
        connection.commit()


# calculate suitability score
# new use_times = old use_times + 1
# new suitability score = [(old use_times * old suitability score) + normalizes competition rankings scores] / new use_times
def update_suitability_score(connection: 'pymysql.Connection', competition_result, bot):
    logger.info("Updating suitability scores in table Metrics")
    key = 'bot_index'

    # get the row data of specific bot from metrics
    exist = "SELECT * from Metrics WHERE EXISTS(SELECT * FROM Metrics WHERE bot_index = %s)"
    update = "UPDATE Metrics SET use_times = (%s), suitability_score = (%s) WHERE bot_index = (%s)"
    insert = "INSERT INTO Metrics (bot_index, use_times, suitability_score, availability_score) VALUES (%s , %s, %s , %s)"
    update_availability = "UPDATE Metrics SET availability_score = (%s) WHERE bot_index = (%s)"

    with connection.cursor() as cursor:
        for k in range(0, len(competition_result)):
            index = competition_result[k][key]
            cursor.execute(exist, (index,))
            # check whether this bot exist in metrics
            new_record = cursor.fetchone()
            # if this bot exist, then update use_times, suitability score
            if new_record:
                # find this record
                sql_select = "SELECT * from Metrics WHERE bot_index = %s"
                cursor.execute(sql_select, (index,))
                new_record = cursor.fetchall()
                # recalculate Use times, suitability score
                old_use_times = new_record[0][1]
                new_use_times = old_use_times + 1
                old_suitability_score = new_record[0][2]
                suitability_score_need_add = competition_result[k]['competition_rank']
                new_suitability_score = (old_use_times * old_suitability_score + suitability_score_need_add) \
                                        / new_use_times
                new_val = (new_use_times, new_suitability_score, index)
                # update record
                cursor.execute(update, new_val)
                print("Bot", index, "already exists, now updating its use times and suitability score", cursor)
                # if this bot not from existing metaml, but selected by competition platform, then we also need
                # to change its availability score
                if int(index) not in bot:
                    avail_val = new_record[0][3] + 1
                    this_val = (avail_val, index)
                    # update availability score
                    cursor.execute(update_availability, this_val)
                    print("Bot %s is selected by competition platform, now updating its availability score", index, )
            # if not exist, this is a new bot introduced from competition platform
            else:
                new_use_times = 1
                new_suitability_score = competition_result[k]['competition_rank']
                new_availability_score = 1
                new_val = (index, new_use_times, new_suitability_score, new_availability_score)
                # insert new record
                cursor.execute(insert, new_val)
                logger.info("Bot %s is a new bot, now adding this record", index, )
        connection.commit()

    logger.info("Now table Metrics is updated successfully")


def update_ml_database(connection: 'pymysql.Connection', competition_result_normalized):
    logger.info("Now updating table ML_Train..........")
    key1 = 'competition_index'
    key2 = 'bot_index'
    key3 = 'competition_rank'
    sql_update = "UPDATE ML_Train SET Competition_rank = (%s) WHERE Competition_index = (%s) AND bot_index = (%s)"
    with connection.cursor() as cursor:
        for j in range(0, len(competition_result_normalized)):
            val1 = competition_result_normalized[j][key3]
            val2 = competition_result_normalized[j][key1]
            val3 = competition_result_normalized[j][key2]
            val = (val1, val2, val3)
            # cursor.execute(sql_update, val)
            logger.info("Now updating the competition ranking of bot %s", val3)
        logger.info("Now table ML_Train is updated successfully")

    # update the competition ranking in ML_Trian table with the values in normalized_competition_result dictionary


def recalculate_ranking(competition_result):
    key = "competition_rank"
    # get all the competition ranking to a list
    wait_recal = [sub[key] for sub in competition_result.values() if key in sub.keys()]
    # normalizes competition rankings/scores
    change_format = np.array(wait_recal).reshape(-1, 1)
    scaler = preprocessing.MinMaxScaler(feature_range=(-1, 1))
    # retain two decimal places
    normalized_ranking = (-1) * (scaler.fit_transform(change_format).round(2))
    # update competition_result dictionary
    for i in range(0, len(normalized_ranking)):
        new_value = list(normalized_ranking[i])
        competition_result[i][key] = new_value[0]
    return competition_result


def check_bots(connection: 'pymysql.Connection', bot_index: int, competition_index: Union[str, int],
               competition_rank: int, total_bot_count: int):
    global bot_num, competition_result, normalized_competition_result
    # bot_index, competition_index, competition_rank, total_bot_num = result
    # add into competition_result
    competition_result[bot_num] = {'competition_index': competition_index, 'bot_index': bot_index,
                                   'competition_rank': competition_rank}
    bot_num += 1
    # if bot_num==total_bot_num, calculate the rank
    if bot_num == total_bot_count:
        # get the ranked bot to update the ML_Train table
        normalized_competition_result = recalculate_ranking(competition_result)
        update_ml_database(connection=connection, competition_result_normalized=normalized_competition_result)
        competition_result = {}
        bot_num = 0


def check_bot_and_result(connection: 'pymysql.Connection'):
    global available_bots, normalized_competition_result
    if not available_bots or not normalized_competition_result:
        return
    # calculate based on both the request to business solution mgmt and the request to competition platform
    # then update metrics table for suitability score
    update_suitability_score(connection=connection, competition_result=normalized_competition_result,
                             bot=available_bots)
    available_bots = []
    normalized_competition_result = {}


def update_metrics(connection: 'pymysql.Connection', bot):
    update_availability_score(connection=connection, bot=bot)
    check_bot_and_result(connection=connection)


def bot_rank(connection: 'pymysql.Connection', bot_index: int, competition_index: Union[str, int],
             competition_rank: int,
             total_bot_count: int):
    logger.info('bot rank to be persisted')
    check_bots(connection, bot_index, competition_index, competition_rank, total_bot_count)
    check_bot_and_result(connection=connection)


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
            if func in metaml.metrics_service_apis:
                if func == 'update_metrics':
                    bot = args[0]
                    update_metrics(connection=db_connection, bot=bot)
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method='update_metrics', args=None,
                                                                response='metrics updated'))
                elif func == 'bot_rank':
                    bot_index, competition_index, competition_rank, total_bot_count = args
                    bot_rank(connection=db_connection, bot_index=bot_index, competition_index=competition_index,
                             competition_rank=competition_rank, total_bot_count=total_bot_count)
                    logger.info('saved bot rank')
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method='bot_rank', args=None,
                                                                response='saved bot record'))
            elif func in metaml.business_service_apis:
                await metaml.forward_to(NodeType.Business, node, connection, msg)
            elif func in metaml.taxonomy_service_apis:
                await metaml.forward_to(NodeType.Taxonomy, node, connection, msg)
            elif func in metaml.context_service_apis:
                await metaml.forward_to(NodeType.Context, node, connection, msg)
            else:
                response = Message(MessageType.ERROR)
            if response:
                logger.info(response)
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

node = metaml.MetaMLNode(node_type=NodeType.Metrics,
                         client_handler=handle_client,
                         port=port,
                         bootstrap_node=bootstrap_node)
asyncio.run(node.init_dht())
