import pandas as pd
import json
import os
import sys
sys.path.append(os.path.abspath('../'))
import requests
import shutil
import tempfile
import zipfile
from tqdm import tqdm
from configparser import ConfigParser
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from DBUtil.MySQLDBConn import MySQLDBConn
from fingerprint import process_fingerprint
# from MySQLDBConn import MySQLDBConn

pd.options.mode.chained_assignment = None


def connect_to_mysqldb():
    # Connect to MySQL database
    mysqlconn = MySQLDBConn()
    db_cursor = mysqlconn.openDB()

    # Select database to use
    glblmktsdb = 'robowebhealthcdb'
    mysqlconn.selectDB(db_cursor, glblmktsdb)
    # mysqlconn.selectDB(db_cursor)

    return mysqlconn, db_cursor

class EndCompetitionHandler:
    def __init__(self, patient_id):
        self.patient_id = patient_id

        configparse = ConfigParser()
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(root_path, 'config/db_config.ini')
        configparse.read(config_path)
        configparse.read('../config/db_config.ini')
        self.influxdb_host = configparse.get('INFLUXDB', 'influxdb_host')
        self.port = configparse.get('INFLUXDB', 'influxdb_port')
        self.org = configparse.get('INFLUXDB', 'influxdb_org')
        self.token = configparse.get('BOTINFLUXDB', 'bot_influxdb_token')
        self.bucket = 'HCSimTradingResults'
        self.url = f'http://{self.influxdb_host}:{self.port}'


        # config_path = os.path.join(root_path, 'config/bot_repo_config.ini')
        # self.bots_repo_path = configparse.get('BOTREPO', 'bot_competition_exec_path')
        # self.winning_bots_repo_path = configparse.get('BOTREPO', 'bot_winning_bot_repo_path')
        # self.new_directory_path = None

        # self.bot_metadata = {}
        
        

    def get_bots(self):
        # connect to MySQL db, get 
        mysqlconn, db_cursor = connect_to_mysqldb()
        download_recs = """SELECT agent_id, implemented_ml_id, rank 
            FROM HC_CompetitionResult 
            WHERE competition_event_id_id = %s 
            ORDER BY rank ASC 
            LIMIT 3""" % self.competition_id
        db_cursor.execute(download_recs)
        data = db_cursor.fetchall()
        mysqlconn.closeDB()

        # data = [('JGil0403', 'Sniper', 1)] # For isolated testing

        # Create competition subdirectory in WinningBotsRepo
        # self.new_directory_path = os.path.join(self.winning_bots_repo_path, str(self.competition_id))
        # if not os.path.exists(self.new_directory_path):
        #     os.makedirs(self.new_directory_path)

        for i, row in enumerate(data):
            agent_id, implemented_ml_id, rank = row
            # parsed_agent_id = "_".join(agent_id.rsplit('_', 2)[:-2]) # Check parsing
            parsed_agent_id = agent_id
            # Using parsed_agent_id, find bot in Bots repo and copy to WinningBotsRepo/competition_id. Then get the path to the file in WinningBotsRepo

            # Name of the .py file to copy
            file_name = f"{parsed_agent_id}.py"
            source_file_path = os.path.join(self.bots_repo_path, file_name)
            new_file_name = file_name = f"{parsed_agent_id}_MML_bot{i+1}.py"
            # destination_file_path = os.path.join(self.new_directory_path, new_file_name)
            destination_file_path = "/robothon/vp2359/RobothonHealthcare/HCSimTrading/WinningBotsRepo/0/bot1.py"

            # Copy the .py file
            shutil.copy(source_file_path, destination_file_path)
            print(f"Bot '{file_name}' copied from '{self.bots_repo_path}' to '{self.new_directory_path}'.")
            
            d = {
                "agent_id": f"{parsed_agent_id}_MML_bot{i+1}",
                "implemented_ml": implemented_ml_id,
                "rank": rank,
                "url": destination_file_path,
                "competition_id": self.competition_id
            }
            self.bot_metadata[parsed_agent_id] = d

            # bot_metadata = {'JGil0403': {"agent_id": 'JGil0403',
            #                              "exec_algorithm": 'Sniper',
            #                              "rank": 1,
            #                              "url": '/robothon/ras10116/RobothonGlblMkts/ArchSimTrading/WinningBotsRepo/0/JGil0403.py',
            #                              "competition_id": '0'}}
        print()
            
        # Sort by rank, pick top 3
        # parse agent_id for first part
        # Get bots code from Bots/
        # In WinningBotsRepo, create competition subdirectory and store code there
        # in the bot_metadata, add agent_id, competition_id and path to the code in WinningBotsRepo


    # def write_to_db(self):
        # with InfluxDBClient(url=self.url, token=self.token, org=self.org) as client:
        #     write_api = client.write_api(write_options=SYNCHRONOUS)
        #     print(f"Writing {len(self.data)} records to InfluxDB... ")
        #     for index, row in tqdm(self.data.iterrows()):
        #         point = Point("marketregimeresults") \
        #             .tag('CompetitionID', self.competition_id) \
        #             .time(row['_time'].to_pydatetime(), WritePrecision.NS) \
        #             .field('symb', row['symb']) \
        #             .field('price', row['price']) \
        #             .field('origQty', row['origQty']) \
        #             .field('orderNo', row['orderNo']) \
        #             .field('status', row['status']) \
        #             .field('remainingQty', row['remainingQty']) \
        #             .field('action', row['action']) \
        #             .field('side', row['side']) \
        #             .field('FOK', row['FOK']) \
        #             .field('AON', row['AON']) \
        #             .field('strategy', row['strategy'])
        #         write_api.write(self.bucket, self.org, point)
        #     print("Done\n")


    def add_fingerprint(self):
            print("Im here")

            # URL of the API endpoint
            url = 'http://127.0.0.1:5000/api/add_fingerprint'

            self.bot_metadata = {'bot1': {"agent_id": 'JGil0403',
                                         "implemented_ml": 'Sniper',
                                         "rank": 1,
                                         "url": '/robothon/vp2359/RobothonHealthcare/HCSimTrading/WinningBotsRepo/0/bot1.py',
                                         "competition_id": '0'}}


            print("Bot metadata:", self.bot_metadata)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip_file:
                with zipfile.ZipFile(temp_zip_file, 'w') as zipf:
                    print("Bot Metadata items:",self.bot_metadata.items())
                    for _, file_dict in self.bot_metadata.items():
                        print(file_dict)
                        print("-------------------", end="\n")
                        print("This is the url: ",file_dict['url'])
                        print("-------------------", end="\n")
                        zipf.write(file_dict['url'], os.path.basename(file_dict['url']))
            print("Temp Zip File:", temp_zip_file.name)
            

            files = {"zipfile": ("bot_scripts.zip", open(temp_zip_file.name, 'rb'))}
            payload = json.loads(process_fingerprint(self.patient_id))

            # Make the API call with the multipart/form-data payload
            response = requests.post(url, files=files, data=payload)
            # args={'datafileinfo': {"time_column: _", "value_column: _, group_by: _"}, 'bot_metadata': {agent_id: _, github_url: _}, 'aggregates': {}}

            # Check the response
            if response.status_code == 200:
                print("Upload successful!")
            else:
                print("Upload failed with status code:", response.status_code)
                print("Response:", response.text)
    

    def end(self):
        # self.calculate_aggregates()
        # self.write_to_db()
        # self.get_bots()
        self.add_fingerprint()

if __name__ == "__main__":
    # regime_path = os.path.join(self.regime_data_path, self.regime_data_csv_filename)
    end_competition = EndCompetitionHandler(1)
    end_competition.end()