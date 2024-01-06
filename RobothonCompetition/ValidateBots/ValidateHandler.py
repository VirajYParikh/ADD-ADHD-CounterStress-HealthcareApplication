from configparser import ConfigParser
import pandas as pd
import keras
import pickle
import signal
import functools
import ctypes
import threading
import pathlib
import psutil
import time
import csv
import sys
import re
import os
import logging
from DBUtil.MySQLDBConn import MySQLDBConn
from DBUtil.InfluxDBConn import InfluxDBConn
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxStructureEncoder
from EmailUtil.EmailSender import EmailSender
import subprocess
import json

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # ../RobothonCompetition/ directory
SYS_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/sys_config.ini')

def connect_to_mysqldb():
    # Connect to MySQL database
    mysqlconn = MySQLDBConn()
    db_cursor = mysqlconn.openDB()
    
    # Select database to use
    healthcdb = 'robowebhealthcdb'
    mysqlconn.selectDB(db_cursor, healthcdb)
    #mysqlconn.selectDB(db_cursor)
    
    return mysqlconn, db_cursor

def connect_to_influxdb():
    # Connect to InfluxDB
    influxdbconn = InfluxDBConn()
    #influxdb_cursor = self.influxdbconn.openInfluxDBBotBucket()
    
    return influxdbconn

class ValidateHandler:
    logger = None
    event_id = 0
    maxtime = 120 # default
    bot_download_path = None
    downloaded_bots_dir = None
    downloaded_bots_full_path = None
    bot_disqualified_path = None
    validate_bots_test_run_path = None
    bot_competition_exec_path = None

    report_dict = {} # format is {file name} : {report reason}
    bot_list = [] # list of participant bots (Python files)
    disqualified_bot_list = [] # list of disqualified participant bots (Python files)
    #validated_bot_list = [] # list of participant bots that passed all validation tests (will compete)

    def __init__(self, event_id):        
        # Configure logging
        self.configureLogging()
        
        if DEBUG:
            self.logger.info("ValidateHandler: Validate participant bots")
        
        self.readConfigFile()
        self.event_id = event_id
        
        #self.downloaded_bots_full_path = '%s/bot_downloads_eventnum_%s' % (self.bot_download_path, self.event_id)
        self.downloaded_bots_dir = 'bot_downloads_eventnum_%s' % (self.event_id)
        self.downloaded_bots_full_path = os.path.abspath(os.path.join(self.bot_download_path, self.downloaded_bots_dir))
        
        # if DEBUG:
        #     self.logger.info(f"Path to downloaded participant bots: {self.bot_download_path}")
        #     self.logger.info(f"Directory of downloaded participant bots: {self.downloaded_bots_dir}")
        #     self.logger.info(f"FULL Path to downloaded participant bots: {self.downloaded_bots_full_path}")
            
        #     self.logger.info(f"FULL Path to disqualified bots: {self.bot_disqualified_path}")
        #     self.logger.info(f"FULL Path to execute a test run to validate bots: {self.validate_bots_test_run_path}")
        #     self.logger.info(f"FULL Path to final validated bots that will compete: {self.bot_competition_exec_path}")

        ##self.validateBots()

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
        sysconfigparse = ConfigParser()
        sysconfigparse.read(SYS_CONFIG_FILE_PATH)
        self.bot_download_path = sysconfigparse.get('BOTS', 'bot_download_path')
        self.bot_disqualified_path = sysconfigparse.get('BOTS', 'bot_disqualified_path')
        self.validate_bots_test_run_path = sysconfigparse.get('BOTS', 'validate_bots_test_run_path')
        self.bot_competition_exec_path = sysconfigparse.get('BOTS', 'bot_competition_exec_path')

    def findProcessIDByName(self, processName):
        '''
            Get a list of all PIDs of all running processes that match processName
        '''
        listOfProcessObjects = []
        
        # iterate over all running processes
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
                self.logger.info(f'pinfo: {pinfo}')
                # check if process name matches processName
                if processName.lower() in pinfo['name'].lower():
                    listOfProcessObjects.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return listOfProcessObjects;

    def getProcessInfo(self, processName):
            self.logger.info("---- validateHandler: find PIDs of a running process by name ----")
            listOfProcessIds = self.findProcessIDByName(processName)
            if len(listOfProcessIds) > 0:
                self.logger.info('validateHandler: Process Exists | PID and other process details: ')
                for elem in listOfProcessIds:
                    processID = elem['pid']
                    processName = elem['name']
                    processCreationTime =  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(elem['create_time']))
                    self.logger.info(f'validateHandler: {processID}, {processName}, {processCreationTime}')
            else :
                self.logger.info(f'validateHandler: No Running Process(es) found for {processName}')
                
            # Find PIDs of all the running instances of process that contains 'influxdb' in it's name
            procObjList = [procObj for procObj in psutil.process_iter() if 'influxdb' in procObj.name().lower() ]
            for elem in procObjList:
                print (elem)

    def validateBots(self):
        if DEBUG:
            self.logger.info("****************************** ValidateBots CALLED!! *****************************************")
        
        validated_code_path = os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), 'bots/validated/competition_%s' % self.event_id))
        if DEBUG:
            self.logger.info("Path is: ",validated_code_path)
    
        mysqlconn, db_cursor = connect_to_mysqldb()
        self.db_cursor.execute("""use robowebhealthcdb;""")
        download_recs = """SELECT id, robot_username, code_url, event_id_id, validation_count
            FROM HC_CompetitionEventParticipant WHERE event_id_id = %s""" % self.event_id
        db_cursor.execute(download_recs)
        data = db_cursor.fetchall()
        mysqlconn.closeDB()
        
        if DEBUG:
            self.logger.info(data)
        
        df = pd.DataFrame(data, columns=['table_id','id', 'code_url', 'event_id','validation_count'])
        df['event_id'] = df['event_id'].astype('str')  
        
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if DEBUG:
            self.logger.info(f'PROJECT ROOT: {proj_root}')
        
        for i in range(len(df)):
            # detresultpath = os.path.join(proj_root, 'bots/temp/competition_'+ str(df['event_id'][i])+'/det/'+ df['id'][i])
            # actresultpath = os.path.join(proj_root, 'bots/temp/competition_'+ str(df['event_id'][i])+'/act/'+ df['id'][i])
            detresultpath = os.path.join(proj_root, 'bots/downloaded/bot_downloads_eventnum_'+ str(df['event_id'][i])+'/det/'+ df['id'][i])
            actresultpath = os.path.join(proj_root, 'bots/downloaded/bot_downloads_eventnum_'+ str(df['event_id'][i])+'/act/'+ df['id'][i])
            apipath = os.path.join(proj_root, 'bots/validation_api/')
            download_path = os.path.join(proj_root, 'bots/downloaded/bot_downloads_eventnum_%s' % self.event_id)
            downloaded_file = download_path + '/%s.py'%df['id'][i]
            
            if DEBUG:
                self.logger.info(f'---- detresultpath: {detresultpath}')
                self.logger.info(f'---- actresultpath: {actresultpath}')
                self.logger.info(f'---- apipath: {apipath}')
                self.logger.info(f'---- download_path: {download_path}')
                self.logger.info(f'---- downloaded_file: {downloaded_file}')

            # command = 'python '+ validated_code_path+'/%s.py --maxtime %s --result_path %s \
            #    --data_api %s' %(df['id'][i] , self.maxtime, detresultpath, apipath)
            # print("Command=",command)
            
            # command = 'python '+ validated_code_path+'/%s.py --maxtime %s --result_path %s \
            #    --data_api %s' %(df['id'][i] , self.maxtime, resultpath, apipath)
            # print("Command=",command)
            
            update_query = "UPDATE HC_CompetitionEventParticipant SET validation_count = %s WHERE id = %s"
            val = (df['validation_count'][i]+1, df['table_id'][i])
            #SQL.cursor.execute(update_query,val)
            #data = SQL.cursor.fetchall()
            
            # print("----------------------------------------------------")
            # print(f"df['id'][i]: {df['id'][i]}")
            # print("----------------------------------------------------")
            
            stress_det_val = self.validate_stress_detection(df['id'][i], downloaded_file, self.maxtime, detresultpath, apipath)
            act_eval_val = self.validate_action_evaluation(df['id'][i], downloaded_file, self.maxtime, actresultpath, apipath)
            if (stress_det_val==1):
            #and (act_eval_val==1):
                os.system('cp %s/%s.py '%(download_path, df['id'][i]) + validated_code_path + '/')
                os.remove('%s/%s.py'%(download_path, df['id'][i]))
        # #self.checkBotFileExtension()
        # #self.testRunBots()
        # #self.runBotsInTestEnvironment() # - to validate - python entry_script.py -user_id <robo_usr/BOT_ID> --> returns a .csv file
        # #self.notifyParticipants()
        # #self.prepareQualifiedBotsForCompetition()

    def checkBotFileExtension(self):
        # Check the bots download path is valid
        if os.path.exists(self.downloaded_bots_full_path):
            # Check that all bots are valid Python files (have the .py file extension) - if not .py then disqualified
            for bot_file in os.listdir(self.downloaded_bots_full_path):
                if not bot_file.endswith('.py'):
                    self.report_dict[bot_file] = 'Validation Failure - invalid file type: participant bot is not a Python file.'
                    if DEBUG:
                        self.logger.info(f'Error: participant bot, {bot_file}, is not a valid Python file')
                    self.disqualified_bot_list.append(bot_file)
                    continue
                self.bot_list.append(bot_file)

            if DEBUG:
                self.logger.info(f"(checkBotFileExtension) List of valid bot file types: {self.bot_list}")
                self.logger.info(f"(checkBotFileExtension) List of disqualified bots (invalid file types): {self.disqualified_bot_list}")
                self.logger.info(f"(checkBotFileExtension) List of report reasons: {self.report_dict}")
        else:
            self.logger.info(f"Error: bot download path={self.downloaded_bots_full_path} is invalid for event ID {self.event_id}.")

    def validate_stress_detection(self, id, downloaded_file, maxtime, resultpath, apipath):
        command = ['python', downloaded_file, '--maxtime', str(maxtime), '--result_path', resultpath, '--data_api', apipath, '--mode', '1']
        
        try:
            p = subprocess.run(command, timeout = maxtime, capture_output=True)
            #print( 'exit status:', p.returncode )
            #print( 'stdout:', p.stdout.decode() )
            #print( 'stderr:', p.stderr.decode() )
            #print("PRINTING OUTPUT:",p)
            if p.returncode == 0:
                classifier = keras.models.load_model(resultpath)
                print("Stress Detection: Successfully Validated Bot:",id)
                #os.system('cp %s/%s.py '%(download_path, id) + validated_code_path + '/')
                #os.remove('%s/%s.py'%(download_path, id))
                return 1
            else:
                print(f"Bot {id} gave some error:", p.returncode)
                return 0
                        
        except subprocess.TimeoutExpired:
            print("Timed out")
            return 0
        except:
            print(f"Bot Validation failed for bot {id}")
            return 0
        
    def validate_action_evaluation(self, id, downloaded_file, maxtime, resultpath, apipath):
        command = ['python', downloaded_file, '--maxtime', str(maxtime), '--result_path', resultpath, '--data_api', apipath, '--mode','2']            
        try:
            p = subprocess.run(command, timeout = maxtime, capture_output=True)
            #print("PRINTING OUTPUT:",p)
            if p.returncode == 0:
                #classifier = keras.models.load_model(resultpath)
                loaded_model = pickle.load(open(resultpath, 'rb'))
                print("Action Detection: Successfully Validated Bot:",id)
                #os.system('cp %s/%s.py '%(download_path, id) + validated_code_path + '/')
                #os.remove('%s/%s.py'%(download_path, id))
                return 1
            else:
                print("failed")
                return 0
                #return 0 # ORIGINAL
                        
        except subprocess.TimeoutExpired:
            return 0
        except:
            return 0

    def runBotsInSandboxEnvironment(self):
        if DEBUG:
            self.logger.info(f"ValidateHandler: Run bots in test enviornment")
            
            from RunSandboxEnvironment.SandboxEnvHandler import SandboxEnvHandler
            teHandler = SandboxEnvHandler(event_id)
            self.logger.info(f"{self.banner} ValidateHandler: running bots in sandbox test environment... {self.banner}")
            #teHandler.fetchParticipantDownloadInfo() 
            teHandler.runSandboxTestEnv()   

    def notifyParticipants(self):
        
        if DEBUG:
            self.logger.info(f"REPORT DICTIONARY: {self.report_dict}")
        
        # self.db_cursor = self.mysqlconn.openDB()
        # self.mysqlconn.selectDB(self.db_cursor)
        
        emailer = EmailSender()
        for key, value in self.report_dict.items():
            
            if DEBUG:
                self.logger.info(f"Current report item: key={key}, value={value}")
            
            # Fetch participant information
            #bot_file = key.replace('.py', '')
            bot_file = os.path.splitext(key)[0]
            
            if DEBUG:
                self.logger.info(f"Bot filename with removed file extension - serves as robot_username: {bot_file}")
            
            # Fetch the participant information, including email address
            mysqlconn, db_cursor = connect_to_mysqldb()
            participant_user_info_query = """SELECT au.first_name, au.last_name, au.email 
            FROM auth_user AS au, HC_CompetitionEventParticipant AS cep 
            WHERE cep.event_id_id=%s AND cep.robot_username=\'%s\' AND cep.user_id=au.id;""" % (self.event_id, bot_file)
            db_cursor.execute(participant_user_info_query)
            user_data = db_cursor.fetchall()
            db_cursor.close()
            participant_firstname = user_data[0][0]
            participant_lastname = user_data[0][1]
            participant_email = user_data[0][2]

            if DEBUG:
                self.logger.info(f"USER DATA (user info): {user_data}")
                self.logger.info(f"Participant participant_firstname: {participant_firstname}")
                self.logger.info(f"Participant participant_lastname: {participant_lastname}")
                self.logger.info(f"Participant participant_email: {participant_email}")
                
            # Email participant about disqualified bot
            to_email = participant_email
            subject = "Healthcare Robothon Competition - Bot Status"
            message = """Hello %s %s,\n
            Unfortunately, your bot did not qualify for the Healthcare Robothon Competition. 
            See below for the reason(s) your bot failed to qualify for the competition.
            You have up to three tries before the submission deadline to try and qualify your bot.\n
            Reason(s): %s\n\n
            Good luck!\n
            The Healthcare Robothon Team
            """ % (participant_firstname, participant_lastname, value)
            emailer.sendEmail(to_email, subject, message)              
            
        #self.mysqlconn.closeDB()

    
if __name__ == "__main__":
    if DEBUG:
        event_id=1
        validateHandler = ValidateHandler(event_id)