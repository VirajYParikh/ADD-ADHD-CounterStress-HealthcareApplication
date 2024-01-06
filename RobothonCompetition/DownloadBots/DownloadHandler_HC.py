import pandas as pd
import os
import sys
import subprocess
import logging
from configparser import ConfigParser
from DBUtil.MySQLDBConn import MySQLDBConn

DEBUG = True

class DownloadHandler:

    LOG_FILE_PATH = "../logs/robothon_healthcare.log"
    LOG_LEVEL = logging.DEBUG
    logger = None
    
    mysqlconn = None
    db_cursor = None
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
        self.logger = logging.getLogger(self.LOG_FILE_PATH)
        self.logger.setLevel(self.LOG_LEVEL)
        fh = logging.FileHandler(self.LOG_FILE_PATH)
        fh.setLevel(self.LOG_LEVEL)
        ch = logging.StreamHandler()
        ch.setLevel(self.LOG_LEVEL)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def readConfigFile(self):
        try:
            sysconfigparse = ConfigParser()
            sysconfigparse.read('../config/sys_config.ini')
            self.bots_initial_download_path = sysconfigparse.get(
                'BOTS', 'bot_download_path')

            sysconfigparse.read('../config/bot_repo_config.ini')
            self.bot_repo_IP = sysconfigparse.get('BOTREPO', 'bot_repo_IP')
            self.bot_repo_username = sysconfigparse.get(
                'BOTREPO', 'bot_repo_username')
            self.bot_repo_password = sysconfigparse.get(
                'BOTREPO', 'bot_repo_password')
            self.bot_repo_path = sysconfigparse.get('BOTREPO', 'bot_repo_path')
            self.bot_repo = sysconfigparse.get('BOTREPO', 'bot_repo')

            self.bots_download_path = sysconfigparse.get(
                'TESTENV', 'bots_download_path')
        except Exception as e:
            self.logger.error(f'An error occurred reading config files: {e}')
        
def fetchParticipantDownloadInfo(self, robot_username=None):
        if DEBUG:
            self.logger.info("DownloadHandler: fetching participant download information...")

        self.db_cursor.execute("""use robowebhealthcdb;""")
        download_recs = """SELECT robot_username, code_url, event_id_id, implemented_ml_id
            FROM HC_CompetitionEventParticipant
            WHERE test_request=0 AND event_id_id = %s""" % self.event_id
        self.db_cursor.execute(download_recs)
        data = self.db_cursor.fetchall()
        self.mysqlconn.closeDB()
        
        if DEBUG:
            self.logger.debug(data)
        
        self.download_data = pd.DataFrame(data, columns=['participant_username', 'code_url', 'event_id', 'implemented_ml_id'])
        self.download_data['event_id'] = self.download_data['event_id'].astype('str')
        
        if DEBUG:
            self.logger.debug(f'\n{self.download_data}')
        
        file_path_det = '%s/bot_downloads_eventnum_%s/det' % (self.bots_initial_download_path, self.event_id)
        file_path_act = '%s/bot_downloads_eventnum_%s/act' % (self.bots_initial_download_path, self.event_id)

        if DEBUG:
            self.logger.info(f"DownloadHandler: file_path: {file_path_det}")
            self.logger.info(f"DownloadHandler: file_path: {file_path_act}")

        os.makedirs(file_path_det, exist_ok=True)
        os.makedirs(file_path_act, exist_ok=True)

        for i in range(len(self.download_data)):
            if robot_username is not None:
                if self.download_data['participant_username'][i] != robot_username:
                    continue
            if DEBUG:
                self.logger.debug(f"DownloadHandler: participant username: {self.download_data['participant_username'][i]}")
                self.logger.debug(f"DownloadHandler: download URL: {self.download_data['code_url'][i]}")
                self.logger.debug(f"DownloadHandler: event ID: {self.download_data['event_id'][i]}")
                self.logger.debug(f"DownloadHandler: file_path: {file_path}")

            # self.db_cursor.execute("""use robowebhealthcdb;""")
            # ml_model_code = """SELECT mlmodel_code
            #     FROM machinelearningmodeltype
            #     WHERE mlmodel_type_id = %s""" % self.implemented_ml_id
            mlmodel_type = self.download_data['implemented_ml_id']
            if mlmodel_type == 1:
                print(f"CURRENT VALUE of MLMODEL_TYPE: {mlmodel_type} -- A DET BOT")
                # self.downloadURL(self.download_data['participant_username'][i],
                #                 self.download_data['code_url'][i],
                #                 self.download_data['event_id'][i], file_path_det)
            elif mlmodel_type == 2:
                print(f"CURRENT VALUE of MLMODEL_TYPE: {mlmodel_type} -- AN ACT BOT")
                # self.downloadURL(self.download_data['participant_username'][i],
                #                 self.download_data['code_url'][i],
                #                 self.download_data['event_id'][i], file_path_act)

def downloadURL(self, participant_username, code_url, event_id, file_path):
    if DEBUG:
        self.logger.info(
            "DownloadHandler: downloading participant bots...")

    formatted_participant_username = participant_username.replace(' ', '')
    participant_code_file_path = '%s/%s' % (
        self.bots_initial_download_path, formatted_participant_username)
    os.makedirs(participant_code_file_path, exist_ok=True)
    #download_cmd = 'git clone %s %s' % (code_url, participant_code_file_path)
    #repo_access_cmd = 'ssh://%s@%s%s' % (self.bot_repo_username, self.bot_repo_IP, self.bot_repo_path)
    #repo_access_cmd = 'ssh://%s:%s@%s%s' % (self.bot_repo_username, self.bot_repo_password, self.bot_repo_IP, self.bot_repo_path)
    #download_cmd = 'git clone %s %s' % (repo_access_cmd, participant_code_file_path)
    download_cmd = 'git clone --local %s %s' % (
        self.bot_repo_path, participant_code_file_path)

    if DEBUG:
        # self.logger.info(f"DownloadHandler: repo_access_cmd: {repo_access_cmd}")
        self.logger.info(f"DownloadHandler: download_cmd: {download_cmd}")

    os.system(download_cmd)

    # if DEBUG:
    #     self.logger.debug(f'DownloadHandler: download command: {download_cmd}')

    # subprocess.run(download_cmd, capture_output=False, shell=True)
    filename = os.listdir(
        '%s/%s' % (self.bots_initial_download_path, formatted_participant_username))

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
