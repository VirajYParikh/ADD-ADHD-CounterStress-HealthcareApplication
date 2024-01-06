import heapq
import json
import pickle
import sys

from sklearn.ensemble import RandomForestRegressor

import metaml
import pymysql
import asyncio
import logging
import node_connection
from metaml import NodeType
from messaging.message import *
from KnowledgeManager.KnowledgeManager import KnowledgeManager

import numpy as np
from pyts.image import GramianAngularField
import re
import uuid
import pandas as pd

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('BusinessService')
logging.getLogger('numba').setLevel(logging.WARNING)

MAX_FEATURE = 4


def get_bots_from_index(connection: 'pymysql.Connection', context: str) -> List:
    query = '''
            select bot_id, Github_link from   Bots_database
                     where  domains=%s AND 
                            dimensions=%s AND 
                            application_area=%s AND 
                            business_problem=%s AND 
                            customer_profile=%s
            '''
    with connection.cursor() as cursor:
        cursor.execute(query, context.split(','))
    return [row[0] for row in cursor.fetchall()]


# Get the fingerprint from the regime of request
def feature_extractor(size, maxtime, regime):
    regime = np.array(regime)
    transformer = GramianAngularField()
    m, _ = regime.shape
    # padding to (10, 22)
    feature = np.c_[np.full(m, size), np.full(m, maxtime), regime]
    # transform to image (10, 22, 22)
    feature = transformer.transform(feature)
    # resize to (4840, )
    feature = feature.flatten()
    return feature


def get_fingerprint(regime):
    logger.info('regime=%s', regime)
    if len(regime) == 2:
        km = KnowledgeManager(regime[0], regime[1])
        km.load_data()
        return km.features
    elif len(regime) == 3:
        return feature_extractor(regime[0], regime[1], regime[2])
    else:
        raise AttributeError('Invalid regime')


def process_fingerprint(fingerprint, ):
    features = re.split("\s|,", fingerprint)[:MAX_FEATURE]
    features = [float(feature) if feature else 0 for feature in features]
    return np.array(features)

def get_competition_id():
    competition_index = uuid.uuid1()
    return competition_index


def get_ml_predictions(filtered_bots, fingerprint, data_file, number_of_bots):
    predicted_bots = list()
    data = pd.read_csv(data_file, header=0)
    data[["bot_index", "competition_index", "competition_rank"]] = \
        data[["bot_index", "competition_index", "competition_rank"]].apply(pd.to_numeric)
    data['count'] = data['fingerprint'].apply(lambda x: len(x.split(' ')))
    # ['bot_index', 'competition_index', 'fingerprint', 'competition_rank']
    print(data['count'])
    rank_bot_prediction = []
    for bot_idx in filtered_bots:
        bot_data = data[data["bot_index"] == bot_idx]
        bot_data['fingerprint'] = bot_data['fingerprint'].apply(process_fingerprint)
        feature_cols = ["feature" + str(i + 1) for i in range(MAX_FEATURE)]
        bot_data_features = pd.DataFrame(bot_data['fingerprint'].tolist(), columns=feature_cols)
        features = np.array(bot_data_features)
        labels = np.array(bot_data['competition_rank'])
        logger.info('labels %s', labels)
        logger.info('features %s', features)
        rf = RandomForestRegressor(n_estimators=20, random_state=42)
        rf.fit(features, labels)

        predicted_rank = rf.predict(fingerprint)[0]

        if len(rank_bot_prediction) < number_of_bots:
            heapq.heappush(rank_bot_prediction, (predicted_rank, bot_idx))
        else:
            heapq.heappushpop(rank_bot_prediction, (predicted_rank, bot_idx))
        predicted_bots.extend(list(list(zip(*rank_bot_prediction))[1]))
    return predicted_bots


async def available_bots_fingerprints(connection: 'pymysql.Connection', context: str, regime: str):
    available_bots = get_bots_from_index(connection=connection, context=context)
    fingerprints = get_fingerprint(regime=regime)
    return available_bots, fingerprints


async def predict_bots(connection: 'pymysql.connections.Connection', context: str, regime, bot_count: int):
    available_bots, fingerprints = await available_bots_fingerprints(connection=connection, context=context,
                                                                    regime=regime)

    metrics_message = Message(message_type=MessageType.QUERY,
                              message_data=MessageData(method='update_metrics', args=(available_bots,)))
    metrics_nodes = await node.nearest_of_type(NodeType.Metrics)
    if metrics_nodes and len(metrics_nodes):
        logger.info('metrics nodes= %s', metrics_nodes)
        # host, port = metrics_nodes[0].split(':')
        metrics_connection = await node_connection.NodeConnection.create_connection(metrics_nodes[0])
        await metrics_connection.send_message(metrics_message)

    predicted_bots = get_ml_predictions(available_bots, fingerprints, "./data/ML_train.csv", bot_count)
    competition_id = get_competition_id()
    return {'predict_bot': predicted_bots, 'competition_id': str(competition_id)}


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
            if func in metaml.business_service_apis:
                if func == 'predict_bots':  # GET /bot_predict
                    # bots = await get_bots_from_index(connection=db_connection, context=args[0])
                    context, regime, bot_count = args
                    predicted_bots = await predict_bots(connection=db_connection, context=context,
                                                        regime=regime, bot_count=int(bot_count))
                    logger.info(predicted_bots)
                    response = Message(MessageType.RESPONSE,
                                       MessageData(response=json.dumps(predicted_bots), method=None, args=None))

                elif func == 'available_bots_fingerprints':  # used in PUT /fingerprint (@context service)
                    context, regime = args
                    _available_bots_fingerprints = await available_bots_fingerprints(connection=db_connection,
                                                                                     context=context,
                                                                                     regime=regime)
                    available_bots, fingerprints = _available_bots_fingerprints
                    fingerprints = metaml.encode(fingerprints)
                    response = Message(message_type=MessageType.RESPONSE,
                                       message_data=MessageData(method=None, args=None,
                                                                response=(available_bots, fingerprints)))
            elif func in metaml.context_service_apis:
                await metaml.forward_to(NodeType.Context, node, connection, msg)
            elif func in metaml.taxonomy_service_apis:
                await metaml.forward_to(NodeType.Taxonomy, node, connection, msg)
            elif func in metaml.metrics_service_apis:
                await metaml.forward_to(NodeType.Metrics, node, connection, msg)
            else:
                response = Message(MessageType.ERROR)
            if response:
                await connection.send_message(response)
            else:
                await connection.send_message(Message.empty_message())
    elif msg.message_type == MessageType.LIST:
        logger.info('List request received')
        nearest_nodes = await node.nearest_of_type()
        logger.debug(nearest_nodes)
        await connection.send_message(Message(MessageType.RESPONSE,
                                              MessageData(method=None, args=None, response=nearest_nodes)))
    elif msg.message_type == MessageType.PING:
        await connection.send_message(Message(MessageType.HELO, bytes(b'')))


port, bootstrap_node = metaml.fetch_args()

node = metaml.MetaMLNode(node_type=NodeType.Business,
                         client_handler=handle_client,
                         port=port,
                         bootstrap_node=bootstrap_node)
asyncio.run(node.init_dht())
