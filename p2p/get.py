import logging
import asyncio

from kademlia.network import Server

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


async def run():
    server = Server()
    await server.listen(8469)
    bootstrap_node = ('localhost', 9893)
    await server.bootstrap([bootstrap_node])

    result = await server.get('10.0.0.142:1234')
    print("Get result:", result)
    server.stop()


asyncio.run(run())
