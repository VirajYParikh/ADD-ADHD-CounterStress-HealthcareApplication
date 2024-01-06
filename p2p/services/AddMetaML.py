import argparse
import os
import sys
import asyncio
import node_connection
import client
from messaging import message
import socket
import context_transfer

hostname = socket.gethostname()
IP_address = socket.gethostbyname(hostname)

# Input the context
"""Change your request context below this line
================================================"""
raw_context = ['Health', 'HeartRate', 'Stress Detection', 'ASD Research', 'Meyer']
print("Input Context (" + ','.join(raw_context) + ")")
"""=============================================
Change your request context above this line"""

domain = raw_context[0]
dimension = raw_context[1]
application_area = raw_context[2]
business_problem = raw_context[3]
customer_profile = raw_context[4]

p1 = context_transfer.parser(domain, dimension, application_area, business_problem, customer_profile)
context_str = ','.join(p1.process())
print("context string transfers into (" + context_str + ")")


# Create P2P connection with MetaML
async def test(msg: 'message.Message', endpoint: str) -> 'message.Message':
    connection = await node_connection.NodeConnection.create_connection(endpoint)
    await connection.send_message(msg)
    return await connection.read_message()


# Send request of retrieving bots to MetaML
async def test_bot_predict() -> 'message.Message':
    msg = message.Message(message_type=message.MessageType.QUERY,
                          message_data=message.MessageData(method='predict_bots',
                                                           args=(
                                                               context_str, ['Meyers', 'fingerprint'], 2)))
    return await test(msg, IP_address + ':1203')

# Get response from MetaML
response1 = asyncio.run(test(test_bot_predict()))
print('=' * 15, 'Receive the bots from MetaML', '=' * 15)
print(f'data     = {response1.message_data}')

myargparser = argparse.ArgumentParser()
myargparser.add_argument('--event_id', type=str, const='text', nargs='?', default='text')
args = myargparser.parse_args()
print(args)

# data = (('JCF', 'https://github.com/ShenJimei/test_1.git', 1),
#         ('Jingzhou', 'https://github.com/ShenJimei/test_2.git', 1),
#         ('Jimei', 'https://github.com/ShenJimei/test_3.git', 1),
#         ('yue201614', 'https://github.com/ShenJimei/test_4.git', 2),
#         ('kshitij', 'https://github.com/ShenJimei/test_5.git', 2),
#         ('zhoucmg', 'https://github.com/ShenJimei/test_6.git', 2)
#         )

# temp_data = {'id': ['bot_100','bot_101','bot_102'],
#              'code_url': ['https://github.com/MuhammadHashirBinKhalid/hc_bot1.git','https://github.com/MuhammadHashirBinKhalid/hc_bot2.git','https://github.com/MuhammadHashirBinKhalid/hc_bot3.git'],
#              'event_id':[str(args.event_id),str(args.event_id),str(args.event_id)]}
# df = pd.DataFrame(data=temp_data)
file_path = os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), 'bots/validated/competition_%s' % args.event_id))

response1_str = str(response1.message_data)
encounter_prev = False
encounter_back = False
response1_concat = ''

for c in response1_str:
    if c == '}':
        encounter_back = True
    if encounter_prev == True and encounter_back == False:
        response1_concat += c
    if c == '[':
        encounter_prev = True

response1_concat = response1_concat[:-2]
response1_list = response1_concat.split(', ')

counter = 1
temp_id = 0
tuple_list = []
for element in response1_list:
    if counter % 2 == 1:
        temp_id = element[1:]
    else:
        temp_url = element[:-1]
        tuple_list.append(tuple((temp_id, temp_url)))
    counter += 1

platform_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dlfunc_path = os.path.join(platform_path, "download_files")
sys.path.append(dlfunc_path)
os.chdir(dlfunc_path)
file_path = os.path.abspath(os.path.join(platform_path, 'bots/validated/competition_%s' % args.event_id))

print('=' * 15, 'Downloading the bots from MetaML', '=' * 15)
from download_url import downloadURL

github_path1 = "https://github.com/annaojlg/hc_bot1.git"
github_path2 = "https://github.com/annaojlg/hc_bot2.git"
tuple_testlist = [("MetaML001", github_path1), ("MetaML002", github_path2)]
for tup in tuple_testlist:
    print("----------sssss-----------")
    downloadURL(tup[0], tup[1], args.event_id, file_path)
# Since the bots_url from MetaML is invalid, we have to create a github path manually to complete the test.
# Once the github link is validated from MetaML, change the 'tuple_testlist' to 'tuple_list'.
