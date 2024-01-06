# MetaML

The MetaML platform's services are provided by a collection of nodes within a P2P network.
Any communication to, from and within happens by exchanging 'messages' between nodes or between node and client.

## p2p network

The nodes in the network use a DHT data structure to keep track of other nodes available on the network.
This project uses the [Kademlia DHT](https://github.com/bmuller/kademlia), which is an implementation of the kademlia
DHT datastructure as described in this [paper](https://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf).

Each node exposes two ports for a client to interact with (the client could be another node on the network).

* DHT Port - Used by the datastructure for storing and retrieving values from the DHT
* Service Port - Used by node to offer the service( like business service, context service, etc.)

### Initializing the network

The network can be initialized simply by starting up the nodes.

``python services/{service_name}_service.py --port {service_port}``

For example:

``python services/business_service.py --port 1203``

``python services/context_service.py --port 1300``

To connect the nodes and grow the network, start them up with the ``--bootstrap-node`` parameter
For example, if there is a ``business_service`` node at ``localhost:1203``.

``python services/context_service.py --port 1300 --bootstrap-node localhost:1203``

#### running the network on a single host (during dev)

The port for the DHT will be randomly set and the port for the service will have to be decided while starting up the
node.
This is because the nodes are all running on a single machine during development, and ports cannot be shared.

_The commands below assume you are in the p2p folder!_

Before running, make sure the following packages are installed and available( in addition to those in the
requirements.txt in the main folder):

* [kademlia](https://kademlia.readthedocs.io/en/latest/)

To get the DHT port, look for the following on starting up a node:

```
(p2p) ➜  p2p git:(fall2022) ✗ python services/business_service.py --port 1203
INFO:MetaML:Node Type: NodeType.Business
INFO:MetaML:Service port: 1203
INFO:MetaML:Running DHT on port 9999
DEBUG:asyncio:Using selector: KqueueSelector
DEBUG:asyncio:Using selector: KqueueSelector
INFO:kademlia.network:Node 1186272219630368780002556924816357195989648719126 listening on 0.0.0.0:9999
DEBUG:kademlia.network:Refreshing routing table
INFO:MetaML:Serving on ('10.0.0.142', 1203)
INFO:MetaML:starting server!

```

**NOTE:** When sending a message to the network the endpoint(ie., IP:Port) use the IP address that is presented in the log(here, 10.0.0.142). See ``services/client.py`` for a working example.

The second line in the run output shows the service port as 1203 (which is what was passed in CLI args).

The third line in the run output shows the DHT port to be 9999 (this is randomly chosen).

When starting up a new node, if we want the new node to connect to this node to build/extend the network:

``python services/context_service.py --port 1300 --bootstrap-node localhost:1203``

Here is the output to be expected:

```
(p2p) ➜  p2p git:(fall2022) ✗ python services/context_service.py --port 1300 --bootstrap-node localhost:9999
INFO:MetaML:bootstrapping with [('localhost', 9999)]
INFO:MetaML:Node Type: NodeType.Context
INFO:MetaML:Service port: 1300
INFO:MetaML:Bootstrap nodes: [('localhost', 9999)]
INFO:MetaML:Running DHT on port 9238
DEBUG:asyncio:Using selector: KqueueSelector
DEBUG:asyncio:Using selector: KqueueSelector
INFO:kademlia.network:Node 711290216908849764484315898953789041260140840022 listening on 0.0.0.0:9238
DEBUG:kademlia.network:Refreshing routing table
DEBUG:kademlia.network:Attempting to bootstrap node with 1 initial contacts
DEBUG:rpcudp.protocol:calling remote function ping on ('localhost', 9999) (msgid b'Md8wKR8+xRoZ8A3Kyf/73dDqnY8=')
DEBUG:rpcudp.protocol:received datagram from ('127.0.0.1', 9999)
DEBUG:rpcudp.protocol:received response b'\xcf\xcaI;\xc8C\xe5\xe3\xf3\x18N\xe2\xd1\xde`?\xc2t\xbd\x16' for message id b'Md8wKR8+xRoZ8A3Kyf/73dDqnY8=' from ('127.0.0.1', 9999)
```

The context service will provide its services on port 1300.
This instance of context service node has its DHT on port 9328, and is bootstrapping with the
node ``('localhost', 9999)``

Towards the bottom of the output notice that this new node has started exchanging rpcudp messages to communicate with
the bootstrap node.

_The rpcudp datagrams are how the package internally exchanges information between the various DHTs; This is different
from the messages that clients use to interact with the nodes!_

##### Interacting with the P2P network

To send a request and get a response from the platform; do the following:

* Create a ``NodeConnection`` instance by passing any node you are aware of in the network.
* Create a ``Message`` instance with the ``message_type``, and ``message_data`` in the constructor during initializing.
* Send the ``message`` to the node through the ``NodeConnection`` instance.
* Receive the ``message`` from the node through the ``NodeConnection`` instance.

Sending and receiving the messages happens asynchronously, so, they have to be called along with ``await``.
Refer to ``services/client.py`` for example on sending and receiving a message.
