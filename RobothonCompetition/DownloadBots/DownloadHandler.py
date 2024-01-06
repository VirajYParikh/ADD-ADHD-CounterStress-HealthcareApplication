import pandas as pd
import os
import sys
sys.path.append(os.path.abspath('../'))
import subprocess
import logging
from configparser import ConfigParser
from DBUtil.MySQLDBConn import MySQLDBConn
import requests
import json
import shutil
from fingerprint import process_fingerprint
import zipfile



DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # ../RobothonCompetition/ directory
SYS_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/sys_config.ini')
BOT_REPO_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/bot_repo_config.ini')

def connect_to_mysqldb():
    # Connect to MySQL database
    mysqlconn = MySQLDBConn()
    db_cursor = mysqlconn.openDB()
    
    # Select database to use
    healthcdb = 'robowebhealthcdb'
    mysqlconn.selectDB(db_cursor, healthcdb)
    #mysqlconn.selectDB(db_cursor)
    
    return mysqlconn, db_cursor

class DownloadHandler:
    logger = None
    download_data = None  # dataframe containing downloaded participant info
    download_path = None
    bots_initial_download_path = None
    bots_download_path = None
    bot_repo_IP = None
    bot_repo_username = None
    bot_repo_password = None
    bot_repo_path = None
    bot_repo = None
    event_id = 0

    def __init__(self, event_id):
        # Configure logging
        self.configureLogging()

        if DEBUG:
            self.logger.info("DownloadHandler: Download Bots Handler")

        self.event_id = event_id
        self.readConfigFile()
        self.mysqlconn = MySQLDBConn()
        self.db_cursor = self.mysqlconn.openDB()

    def configureLogging(self):
        LOG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'logs/robothon_healthcare.log')
        LOG_LEVEL = logging.DEBUG
        self.logger = logging.getLogger(LOG_FILE_PATH)
        self.logger.setLevel(LOG_LEVEL)
        fh = logging.FileHandler(LOG_FILE_PATH)
        fh.setLevel(LOG_LEVEL)
        ch = logging.StreamHandler()
        ch.setLevel(LOG_LEVEL)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def readConfigFile(self):
        try:
            sysconfigparse = ConfigParser()
            sysconfigparse.read(SYS_CONFIG_FILE_PATH)
            self.bots_initial_download_path = sysconfigparse.get('BOTS', 'bot_download_path')

            sysconfigparse.read(BOT_REPO_CONFIG_FILE_PATH)
            self.bot_repo_IP = sysconfigparse.get('BOTREPO', 'bot_repo_IP')
            self.bot_repo_username = sysconfigparse.get('BOTREPO', 'bot_repo_username')
            self.bot_repo_password = sysconfigparse.get('BOTREPO', 'bot_repo_password')
            self.bot_repo_path = sysconfigparse.get('BOTREPO', 'bot_repo_path')
            self.bot_repo = sysconfigparse.get('BOTREPO', 'bot_repo')
            self.bot_repo_exec = sysconfigparse.get('BOTREPO', 'bot_competition_exec_path')
            self.bots_download_path = sysconfigparse.get('TESTENV', 'bots_download_path')
        except Exception as e:
            self.logger.error(f'An error occurred reading config files: {e}')

    def fetchParticipantDownloadInfo(self, robot_username=None):
        if DEBUG:
            self.logger.info("DownloadHandler: fetching participant download information...")

        mysqlconn, db_cursor = connect_to_mysqldb()
        download_recs = """SELECT robot_username, code_url, event_id_id
            FROM HC_CompetitionEventParticipant
            WHERE test_request=0 AND event_id_id = %s""" % self.event_id
        db_cursor.execute(download_recs)
        data = db_cursor.fetchall()
        mysqlconn.closeDB()
        # self.logger.debug(data)
        self.download_data = pd.DataFrame(data, columns=['participant_username', 'code_url', 'event_id'])
        self.download_data['event_id'] = self.download_data['event_id'].astype('str')
        # self.logger.debug(f'\n{self.download_data}')
        file_path = '%s/bot_downloads_eventnum_%s' % (self.bots_initial_download_path, self.event_id)

        if DEBUG:
            self.logger.info(f"DownloadHandler: file_path: {file_path}")

        os.makedirs(file_path, exist_ok=True)
        for i in range(len(self.download_data)):
            if robot_username is not None:
                if self.download_data['participant_username'][i] != robot_username:
                    continue
            if DEBUG:
                self.logger.debug(f"DownloadHandler: participant username: {self.download_data['participant_username'][i]}")
                self.logger.debug(f"DownloadHandler: download URL: {self.download_data['code_url'][i]}")
                self.logger.debug(f"DownloadHandler: event ID: {self.download_data['event_id'][i]}")
                self.logger.debug(f"DownloadHandler: file_path: {file_path}")

            self.downloadURL(self.download_data['participant_username'][i],
                             self.download_data['code_url'][i],
                             self.download_data['event_id'][i], file_path)


    def downloadURL(self, participant_username, code_url, event_id, file_path):
        if DEBUG:
            self.logger.info("DownloadHandler: downloading participant bots...")

        formatted_participant_username = participant_username.replace(' ', '')
        participant_code_file_path = '%s/%s' % (self.bots_initial_download_path, formatted_participant_username)
        os.makedirs(participant_code_file_path, exist_ok=True)
        #download_cmd = 'git clone %s %s' % (code_url, participant_code_file_path)
        #repo_access_cmd = 'ssh://%s@%s%s' % (self.bot_repo_username, self.bot_repo_IP, self.bot_repo_path)
        #repo_access_cmd = 'ssh://%s:%s@%s%s' % (self.bot_repo_username, self.bot_repo_password, self.bot_repo_IP, self.bot_repo_path)
        #download_cmd = 'git clone %s %s' % (repo_access_cmd, participant_code_file_path)
        download_cmd = 'git clone --local %s %s' % (self.bot_repo_path, participant_code_file_path)

        if DEBUG:
            # self.logger.info(f"DownloadHandler: repo_access_cmd: {repo_access_cmd}")
            self.logger.info(f"DownloadHandler: download_cmd: {download_cmd}")

        os.system(download_cmd)
        # subprocess.run(download_cmd, capture_output=False, shell=True)
        filename = os.listdir('%s/%s' % (self.bots_initial_download_path, formatted_participant_username))

        if DEBUG:
            self.logger.debug(f'DownloadHandler: filename: {filename}')

        for file in filename:
            if '.py' in file:
                current_file = '%s/%s ' % (participant_code_file_path, file)
                mv_file = '%s/%s.py' % (file_path, participant_username)
                cp_cmd = 'cp %s %s' % (current_file, mv_file)
                if DEBUG:
                    self.logger.debug(f'DownloadHandler: cp_cmd: {cp_cmd}')
                subprocess.run(cp_cmd, capture_output=False, shell=True)
                cp_cmd = 'cp %s %s' % (mv_file, self.bots_download_path)
                if DEBUG:
                    self.logger.debug(f'DownloadHandler: cp_cmd: {cp_cmd}')
                subprocess.run(cp_cmd, capture_output=False, shell=True)

        rm_cmd = 'rm -rf %s' % participant_code_file_path
        subprocess.run(rm_cmd, capture_output=False, shell=True)
    

    def fetchMetaMLBots(self, num_bots):
        # return None # Remove this

        # URL of the API endpoint
        url = 'http://127.0.0.1:5000/api/predict_bots'

        # datafileinfo = {'time_column': '_time', 'value_column': 'price', 'group_by': 'symb'}

        # data = pd.read_csv(path_to_data, names=column_headers)
        # csv_content = data.to_csv(index=False)
        # files = {"datafile": ("test_regime.csv", csv_content)}

        #event_id = self.event_id
        # Patient id will come from the database. We will make use of the event id to query the patient id
        patient_id = 1
        print("I have reached here")
        payload = process_fingerprint(patient_id)
        final_payload = json.loads(payload)
        # temp_payload["num_bots"] = num_bots
        # temp_payload["fingerprint_type"]="time_series"      
        # final_payload = {}
        # final_payload["fingerprint"] = temp_payload
        # payload['args'] = json.dumps(args_dict)
        print("This is fingerprint dict:", final_payload)
       # Make the API call with the multipart/form-data payload
        response = requests.post(url, data=final_payload)
        # args={'datafileinfo': {"time_column: _", "value_column: _, group_by: _"}, 'bot_metadata': {agent_id: _, github_url: _}, 'aggregates': {}}

        # Check the response
        if response.status_code == 200:
            print("Upload successful!")
            return response
        else:
            print("Upload failed with status code:", response.status_code)



    def downloadMetaMLBots(self, num_bots):
        # API call to get AgentIDs of top performing bots

        bot_scripts = self.fetchMetaMLBots(num_bots)
        # bot_data = {'JGil0403': '/robothon/ras10116/RobothonGlblMkts/ArchSimTrading/WinningBotsRepo/0/JGil0403.py'}


        if bot_scripts:
            print("Received bots from MetaML:")
            print()
        else:
            print("Error: Failed to fetch bots from MetaML.")
            return
        print(bot_scripts)

        # Download MetaML bots to Bots directory
        destination_path = self.bot_repo_exec
        
        file_name = 'downloaded_scripts.zip'
        with open(file_name, 'wb') as f:
            f.write(bot_scripts.content)

        destination_path = self.bot_repo_exec
        print("destination path:", destination_path)
        destination_file_path = os.path.join(destination_path, file_name)
        print("destination file path: ", destination_file_path)
        shutil.move(file_name, destination_file_path)

        with zipfile.ZipFile(destination_file_path, 'r') as zip_ref:
            zip_ref.extractall(destination_path)
        
        os.remove(destination_file_path)

        print('Finished downloading bots from MetaML')

        print()
        print('Finished downloading bots from MetaML')
