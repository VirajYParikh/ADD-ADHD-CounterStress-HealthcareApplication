import codecs
import enum
import os
import pickle
import random
import socket
import logging
import asyncio
import argparse
import kademlia.node
import node_connection
import kademlia.crawling
import kademlia.network as ntwrk
from dotenv import load_dotenv
from typing import Final
from messaging import message
from typing import List, Tuple, Union, Optional

logger = logging.getLogger('MetaML')
load_dotenv()
database: Final[str] = os.getenv('database')  # 'Meta_ML'
db_host: Final[str] = os.getenv('host')  # 'localhost'
db_port: Final[int] = 3306
db_user: Final[str] = os.getenv('user')
db_password: Final[str] = os.getenv('password')


class NodeType(enum.IntEnum):
    Business = 0
    Context = 1
    Taxonomy = 2
    Metrics = 3


context_service_apis = {'delete_fingerprint', 'add_fingerprint'}

business_service_apis = {'predict_bots', 'available_bots_fingerprints'}

taxonomy_service_apis = {'add_business_problem', 'delete_business_problem', 'add_customer_profile',
                         'delete_customer_profile', 'add_application_area', 'delete_application_area',
                         'add_domain', 'delete_domain', 'add_dimension', 'delete_dimension'}
metrics_service_apis = {'update_metrics', 'bot_rank'}

from typing import Any


def encode(text: Any) -> str:
    return codecs.encode(pickle.dumps(text), 'base64').decode()


def decode(pickled: str):
    return pickle.loads(codecs.decode(pickled.encode(), "base64"))


async def forward_to(destination_node_type: NodeType,
                     current_node: 'MetaMLNode',
                     response_pipe: 'node_connection.NodeConnection',
                     msg: 'message.Message', ):
    service_nodes = await current_node.nearest_of_type(destination_node_type)
    if len(service_nodes) > 0:
        x = service_nodes[random.randint(0, len(service_nodes) - 1)]
        logger.debug('randomly chosen network node: %s', x)
        _host, _port = x.split(':')

        connection = node_connection.NodeConnection(*await asyncio.open_connection(host=_host, port=_port))
        # connection = node_connection.NodeConnection(host=_host, port=_port)
        await connection.send_message(msg=msg)
        response = await connection.read_message()
    else:
        logger.error('Cannot find right type of node!')
        response = message.Message(message.MessageType.ERROR, b'Cannot find right type of node!')
    asyncio.create_task(response_pipe.send_message(response))


def find_my_ip() -> str:
    """ Attempt to connect to an Internet host in order to determine the
    local machine's IP address.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("www.google.com", 80))
    server_host = s.getsockname()[0]
    s.close()
    return server_host


def parse_message_data(data: Union[bytes]) -> Optional['message.MessageData']:
    try:
        data = message.MessageData.from_bytes(data)
        return data
    except:
        logger.error('issue parsing message body: %s', data)
    return None


class DHTServer(ntwrk.Server):

    def __init__(self, address_type: str, ksize=20, alpha=3, node_id=None, storage=None):
        ntwrk.Server.__init__(self, ksize=ksize, alpha=alpha, node_id=node_id, storage=storage)
        self.address_type = address_type

    async def nearest_nodes_of_type(self, node_type: NodeType, levels: int = 0) -> List[str]:
        nearest_keys = []
        if levels >= 0:
            local_keys = set()
            for (k, v) in self.storage:
                temp = v.split(';')
                logger.debug("ip endpoint=%s node_type=%s", temp[0], temp[1])
                if node_type is None or int(temp[1]) == int(node_type):
                    local_keys.add(temp[0])

            nearest_keys.extend(local_keys)
            if len(local_keys) == 0:
                #   No keys available for this node type locally, need to look around!
                for node_id in self.protocol.get_refresh_ids():
                    node = kademlia.node.Node(node_id)
                    nearest = self.protocol.router.find_neighbors(node, self.alpha)
                    tasks = []
                    for x in nearest:
                        tasks.append(asyncio.create_task(x.nearest_nodes_of_type(node_type, levels=levels - 1)))
                    for task in asyncio.as_completed(tasks):
                        nearest_keys.extend(await task.result())
        logger.debug(nearest_keys)
        return nearest_keys


class MetaMLNode:
    DHTPort = random.randint(9000, 10000)

    def __init__(self, client_handler, node_type: NodeType, host: str = None, port: Union[int, str] = 9797,
                 bootstrap_node: List[Tuple[str, int]] = None):
        logger.info('Node Type: %s', node_type)
        self.node_type = node_type
        self.client_handler = client_handler
        logger.info('Service port: %d', int(port))
        self.port = int(port)
        self.is_bootstrap = True

        if bootstrap_node is not None and len(bootstrap_node) > 0:
            logger.info('Bootstrap nodes: %s', bootstrap_node)
            self.bootstrap_nodes = bootstrap_node
            self.is_bootstrap = False

        if host is not None:
            self.host = host
        else:
            self.host = find_my_ip()

        logger.info('Running DHT on port %d', MetaMLNode.DHTPort)
        self.address_type = f'{self.host}:{self.port};{int(self.node_type)}'
        self.dht_server = DHTServer(address_type=self.address_type)

    async def nearest_of_type(self, node_type: NodeType = None) -> List:
        return await self.dht_server.nearest_nodes_of_type(node_type=node_type, levels=1)

    async def __insert_node_into_dht(self):
        while True:
            await asyncio.sleep(2)
            temp = self.dht_server.bootstrappable_neighbors()
            if not self.is_bootstrap or (temp is not None and len(temp) > 0):
                logger.debug('is_bootstrap? %s;; temp %s', self.is_bootstrap, temp)
                logger.info('inserting %s into dht', self.address_type)
                await self.dht_server.set(self.address_type, self.address_type)
                break

    async def init_dht(self):
        loop = asyncio.new_event_loop()
        loop.set_debug(True)
        asyncio.set_event_loop(loop=loop)

        try:
            await self.dht_server.listen(MetaMLNode.DHTPort)  # set 9696 as DHT port
            asyncio.create_task(self.__insert_node_into_dht())
            if not self.is_bootstrap:
                await self.dht_server.bootstrap(self.bootstrap_nodes)

            server = await asyncio.start_server(self.client_handler, self.host, self.port)

            addresses = ', '.join(str(sock.getsockname()) for sock in server.sockets)
            logger.info(f'Serving on {addresses}')

            async with server:
                logger.info('starting server!')
                await server.serve_forever()

        except KeyboardInterrupt:
            logger.info('received keyboard interrupt; shutting down ...')
        finally:
            self.dht_server.stop()
            loop.close()


def init_argparse() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(usage="%(prog)s --port --bootstrap-nodes...")
    argument_parser.add_argument("-v", "--version", action="version", version=f"{argument_parser.prog} version 1.0.0")
    argument_parser.add_argument('--port', required=True)
    argument_parser.add_argument('--bootstrap-node', default=None)
    return argument_parser


def fetch_args():
    parser = init_argparse()
    args = parser.parse_args()
    port = int(args.port)
    bootstrap_nodes = list()
    if args.bootstrap_node:
        tmp = args.bootstrap_node.split(':')
        bootstrap_nodes.append((tmp[0], int(tmp[1])))
        logger.info(f'bootstrapping with {bootstrap_nodes}')
    return port, bootstrap_nodes
