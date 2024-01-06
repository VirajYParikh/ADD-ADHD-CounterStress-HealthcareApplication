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

class ThreadKiller(threading.Thread):
    """ Separate thread to kill TerminableThread """
    def __init__(self, target_thread, exception_cls, repeat_sec=2.0):
        threading.Thread.__init__(self)
        self.target_thread = target_thread
        self.exception_cls = exception_cls
        self.repeat_sec = repeat_sec
        self.daemon = True

    def run(self):
        """ Loop through raising exceptions """
        while self.target_thread.is_alive():
            # (ORIGINAL) ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.target_thread.ident), dctypes.py_object(self.exception_cls))
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.target_thread.ident), ctypes.py_object(self.exception_cls))
            self.target_thread.join(self.repeat_sec)

class TerminableThread(threading.Thread):
    """ Thread used to stop by forcing an exception in the execution context """
    def terminate(self, exception_cls, repeat_sec=2.0):
        if self.is_alive() is False:
            return True
        killer = ThreadKiller(self, exception_cls, repeat_sec=repeat_sec)
        killer.start()

def timeout(sec, repeat_sec=1):
    """
    timeout decorator
    :param sec: function raise TimeoutError after ? seconds
    :param repeat_sec: retry kill thread per ? seconds
        default: 1 second
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            class FuncTimeoutError(TimeoutError):
                ...

            result, exception = [], []

            def run_func():
                try:
                    res = func(*args, **kwargs)
                except FuncTimeoutError:
                    pass
                except Exception as e:
                    exception.append(e)
                else:
                    result.append(res)

            # a python thread cannot be terminated, use TerminableThread instead
            thread = TerminableThread(target=run_func, daemon=True)
            thread.start()
            thread.join(timeout=sec)

            if thread.is_alive():
                # a timeout thread keeps alive after join method, terminate and raise TimeoutError
                exc = type('TimeoutError', FuncTimeoutError.__bases__, dict(FuncTimeoutError.__dict__))
                thread.terminate(exception_cls=exc, repeat_sec=repeat_sec)
                err_msg = f'Function {func.__name__} timed out after {sec} seconds'
                raise TimeoutError(err_msg)

            elif exception:
                # if exception occurs during the thread running, raise it
                raise exception[0]
            else:
                # if the thread successfully finished, return its results
                return result[0]

        return wrapped_func

    return decorator

@timeout(35)
def runBot(bot_file, bot_run_path):
    
    cmd = "python %s --maxtime 15 --bot_id %s" % (bot_run_path, bot_file.replace('.py', ''))
    ##cmd = "python %s --action='buy' --symbol 'ZFH0:MBO' --size 25 --maxtime 30 --strategy AggressiveNoSlices --bot_id %s" % (bot_run_path, bot_file.replace('.py', ''))
    print(f'-------------------------------------------- COMMAND RUNNING: {cmd}')
    ##return subprocess.run(cmd, capture_output=True, shell=False, text=True, executable='/bin/bash', timeout=30)
    ###return subprocess.run(cmd, capture_output=True, shell=True, text=True, executable='/bin/bash', timeout=180)
    
    # NOTE: subprocess.run manages the .py processes better than using os.system. When os.system is used, 
    #       the .py fies never timeout and hang, and so these processes add up. When using subprocess.run,
    #       the .py files will be timeed out by subprocesses.run using the timeout flag (as shown above)
    #       In either case, need to debug why these .py processes are not terminating on their own.
    #       One problem with using subprocess.run instead of os.system is don't see the bot IDs generated or other output
    
    os.system(cmd)
    # (ORIG) os.system('python %s --maxtime 15 --bot_id %s' % (bot_run_path, bot_file.replace('.py', '')))
    # os.system("python %s --action='buy' --symbol 'ZFH0:MBO' --size 25 --maxtime 30 --strategy AggressiveNoSlices --bot_id %s" % (bot_run_path, bot_file.replace('.py', '')))
 
    # print(f"---------------------------------------- GET PROCESS INFO ----------------------------------------")
    # getProcessInfo(bot_run_path)
    # print(f"--------------------------------------------------------------------------------------------------")
 
    # DEBUG MODE - enable when debugging   
    # print("*************************************************** I AM HERE (0) !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        
    # print("-------------------------------------------------------------------------------------------")
    # print(f"******** INSIDE runBot ******** - bot_file: {bot_file}")
    # print(f"******** INSIDE bot_run_path ******** - bot_file: {bot_run_path}")
    # print("-------------------------------------------------------------------------------------------")
    
    # try:
    #     os.system('python %s --maxtime 15 --bot_id %s' % (bot_run_path, bot_file.replace('.py', '')))
    # except Exception as e:
    #     print(f"An error occurred in runBot: {e}")
        
class ValidateHandler:
    LOG_FILE_PATH = "../logs/robothon_healthcare.log"
    LOG_LEVEL = logging.DEBUG
    logger = None
    
    # MySQL DB Connection
    mysqlconn = None
    db_cursor = None
    
    # Influx DB Connection
    influxdbconn = None
    influxdb_cursor = None
    
    event_id = 0
    
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
        self.mysqlconn = MySQLDBConn()
        self.db_cursor = self.mysqlconn.openDB()
        self.mysqlconn.selectDB(self.db_cursor)
        self.influxdbconn = InfluxDBConn()
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
        self.logger = logging.getLogger(self.LOG_FILE_PATH)
        self.logger.setLevel(self.LOG_LEVEL)
        fh = logging.FileHandler(self.LOG_FILE_PATH)
        fh.setLevel(self.LOG_LEVEL)
        ch = logging.StreamHandler()
        ch.setLevel(self.LOG_LEVEL)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def readConfigFile(self):
        sysconfigparse = ConfigParser()
        sysconfigparse.read('../config/sys_config.ini')
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
        self.checkBotFileExtension()
        self.testRunBots()
        #self.runBotsInTestEnvironment() # - to validate - python entry_script.py -user_id <robo_usr/BOT_ID> --> returns a .csv file
        #self.notifyParticipants()
        self.prepareQualifiedBotsForCompetition()

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

    def validate_stress_detection(id, downloaded_file, maxtime, resultpath, apipath):
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
        
    def validate_action_evaluation(id, downloaded_file, maxtime, resultpath, apipath):
        command = ['python', downloaded_file, '--maxtime',
                                str(maxtime), '--result_path', resultpath, '--data_api', apipath, '--mode','2']            
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

    def testRunBots(self):
        # Check the bots download path is valid
        if os.path.exists(self.downloaded_bots_full_path):            
            # Test run all bots in the download directory - if bot fails to run then disqualified
            for bot_file in self.bot_list:
                
                if DEBUG:
                    self.logger.info(f"Current bot filename: >>{bot_file}<<")
                
                participant_bots_location = '%s/%s' % (self.bot_download_path, self.downloaded_bots_dir)
                download_loc = os.path.abspath(participant_bots_location)
                test_run_loc = os.path.abspath(self.validate_bots_test_run_path)
                
                # if DEBUG:
                #     self.logger.info(f"TEST RUN BOT - participant_bots_location: {participant_bots_location}")
                #     self.logger.info(f"TEST RUN BOT - download_loc: {download_loc}")
                #     self.logger.info(f"TEST RUN BOT - test_run_loc: {test_run_loc}")
                
                bot_full_source_path = download_loc + '/' + bot_file
                bot_full_destination_path = test_run_loc + '/' + bot_file

                # if DEBUG:
                #     self.logger.info(f"TEST RUN BOT - bot_full_source_path: {bot_full_source_path}")
                #     self.logger.info(f"TEST RUN BOT - bot_full_destination_path: {bot_full_destination_path}")
                
                # Copy participant bot to test run location - an environment to validate bot with a test run
                os.system('cp ' + bot_full_source_path + ' ' + bot_full_destination_path)
                
                # Test run the bot in the test run environment
                bot_test_run_path = None
                
                # TODO: here - insert code to test run the healthcare bots during validation phase (need to understand the code better)(see validation.py in old code)
                # TODO: figure out when the participant table gets updated when a participant is disqualified (for both citi and meyers)
                
                botAgentID = bot_file.replace('.py', '')
                try:
                    bot_test_run_path = os.path.abspath(os.path.join(self.validate_bots_test_run_path, bot_file))

                    if DEBUG:
                        self.logger.info(f"Test running current bot: {bot_file}")
                        self.logger.info(f"Test running current bot full path: {bot_test_run_path}")

                    # output = runBot(bot_file, bot_test_run_path)
                    
                    # if DEBUG:
                    #     self.logger.info(f"Test running current bot output: {output}")
                                            
                    runBot(bot_file, bot_test_run_path)
                    #self.getProcessInfo(bot_test_run_path)
                    
                    # Confirm the prospect participant bot wrote to the time series database (InfluxDB)
                    # If the bot can successfully write to the time series database, then qualify to compete
                    with self.influxdbconn.openInfluxDBBotBucket() as _client:
                        query = """ 
                            import "strings"
                            from(bucket: "%s") 
                            |> range(start: -1h) 
                            |> filter(fn: (r) => strings.containsStr(v: r["AgentID"], substr: "%s") == true)
                        """ % (self.influxdbconn.getBucket(), botAgentID)
                        tables = _client.query_api().query(query, org=self.influxdbconn.getOrg())                    
                        output = json.dumps(tables, cls=FluxStructureEncoder, indent=2)
                        json_records = json.loads(output)
                        #records_only = json_records[0]['records'][0]
                        #records_only = json_records[0]['records']
            
                    if DEBUG:
                        bucket = self.influxdbconn.getBucket()
                        self.logger.info(f"botAgentID (in EXCEPT): >>{botAgentID}<<")
                        self.logger.info(f"BUCKET USED (in EXCEPT): >>{bucket}<<")
                        self.logger.info(f"output (in EXCEPT): {output}")
                        self.logger.info(f"records_only (in EXCEPT): {json_records}")
                        #self.logger.info(f"records_only (in EXCEPT): {records_only}")
                        
                    if (json_records is None) or (len(json_records) == 0):
                        self.report_dict[bot_file] = 'Validation Failure - test run failed: participant bot test run failed.'
                        self.disqualified_bot_list.append(bot_file)
                        self.logger.error(f'Error: participant bot, {botAgentID}, test run failed: {e}')
                    else:
                        self.logger.info(f'Participant bot, {botAgentID} successfully wrote to InfluxDB')
                    
                    # # Participant bot passed all validation - add it to final competition list
                    # self.validated_bot_list.append(bot_file)
                except Exception as e:
                    self.logger.error(f"An error occurred trying to test run participant bot ({bot_file}): {e}")
                    
                    with self.influxdbconn.openInfluxDBBotBucket() as _client:
                        query = """ 
                            import "strings"
                            from(bucket: "%s") 
                            |> range(start: -1h) 
                            |> filter(fn: (r) => strings.containsStr(v: r["AgentID"], substr: "%s") == true)
                        """ % (self.influxdbconn.getBucket(), botAgentID)
                        tables = _client.query_api().query(query, org=self.influxdbconn.getOrg())                    
                        output = json.dumps(tables, cls=FluxStructureEncoder, indent=2)
                        json_records = json.loads(output)
                        #records_only = json_records[0]['records'][0]
                        #records_only = json_records[0]['records']
            
                    if DEBUG:
                        bucket = self.influxdbconn.getBucket()
                        self.logger.info(f"botAgentID (in EXCEPT): >>{botAgentID}<<")
                        self.logger.info(f"BUCKET USED (in EXCEPT): >>{bucket}<<")
                        self.logger.info(f"output (in EXCEPT): {output}")
                        self.logger.info(f"records_only (in EXCEPT): {json_records}")
                        #self.logger.info(f"records_only (in EXCEPT): {records_only}")
                    
                    if (json_records is None) or (len(json_records) == 0):
                        self.report_dict[bot_file] = 'Validation Failure - test run failed: participant bot test run failed.'
                        self.disqualified_bot_list.append(bot_file)
                        self.logger.error(f'Error: participant bot, {botAgentID}, test run failed: {e}')
                    else:
                        self.logger.info(f'Participant bot, {botAgentID} successfully wrote to InfluxDB')
                    #self.getProcessInfo(bot_test_run_path)             
            
            if DEBUG:
                self.logger.info(f"(testRunBots) List of valid bot file types: {self.bot_list}")
                self.logger.info(f"(testRunBots) List of disqualified bots (invalid file types): {self.disqualified_bot_list}")
                self.logger.info(f"(testRunBots) List of report reasons: {self.report_dict}")
                #self.logger.info(f"(testRunBots) List of competing bots (passed all tests): {self.validated_bot_list}")
            
        else:
            self.logger.error(f"Error: bot download path={self.downloaded_bots_full_path} is invalid for event ID {self.event_id}.")

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
            participant_user_info_query = """SELECT au.first_name, au.last_name, au.email 
            FROM auth_user AS au, healthcare_competitioneventparticipant AS cep 
            WHERE cep.event_id_id=%s AND cep.robot_username=\'%s\' AND cep.user_id=au.id;""" % (self.event_id, bot_file)
            self.db_cursor.execute(participant_user_info_query)
            user_data = self.db_cursor.fetchall()
            self.db_cursor.close()
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

    def prepareQualifiedBotsForCompetition(self):
        self.db_cursor = self.mysqlconn.getConn().cursor()
        #self.mysqlconn.selectDB(self.db_cursor)

        strategy_info_query = """SELECT healthcare_competitioneventparticipant.robot_username, healthcare_competitioneventparticipant.robot_password, healthcare_competitioneventparticipant.event_id_id, healthcare_algorithmtype.algo_name 
        FROM healthcare_competitioneventparticipant
        JOIN healthcare_algorithmtype
        ON healthcare_competitioneventparticipant.implemented_algorithm_id = healthcare_algorithmtype.algo_type_id
        WHERE healthcare_competitioneventparticipant.event_id_id = %s""" % self.event_id
        self.db_cursor.execute(strategy_info_query)
        strategy_info = self.db_cursor.fetchall()
        self.db_cursor.close()
        if DEBUG:
            self.logger.info(f'Participant competition strategy_info DATA: {strategy_info}')

        #comptitition_mode_status = """SELECT * FROM healthcare_competitionmode"""
        self.db_cursor = self.mysqlconn.getConn().cursor()
        competition_mode_query = """SELECT test_mode_enabled FROM healthcare_competitionmode"""
        self.db_cursor.execute(competition_mode_query)
        competition_mode_data = self.db_cursor.fetchall()
        self.db_cursor.close()
        competition_mode = competition_mode_data[0][0]
        
        if DEBUG:
            self.logger.info(f'Competition mode (1=test mode, 0=prod mode): {competition_mode}')
        
        #self.mysqlconn.closeDB()

        df = pd.DataFrame(strategy_info, columns=['id', 'password', 'event_id', 'strategy'])
        df['event_id'] = df['event_id'].astype('str')
        
        if DEBUG:
            self.logger.info(f"Strategy Info Dataframe\n\n {df}")
        
        # The bot_list has all bots that were submitted, but as validation proceeded, the bots that failed at 
        # any step moved to disqualified_bot_list (although remained on bot_list). Here, we check if the bot
        # on bot_list is also in disqualified_bot_list, if so, do not include in the competition
        qualified_bots_list = [i.split(".py")[0] for i in self.bot_list if i not in self.disqualified_bot_list]
        
        if DEBUG:
            self.logger.info(f'Qualified participents bot list: {qualified_bots_list}')

        final_qualified_bot_list = df[df['id'].isin(qualified_bots_list)].reset_index(drop=True)
        
        if DEBUG:
            self.logger.info(f"final_qualified_bot_list:\n\n {final_qualified_bot_list}")

        # Check final list of qualified bots is not empty, generate batch scripts
        if (final_qualified_bot_list is not None) or (len(final_qualified_bot_list) > 0):  
            
            # Get qualifying bots python files
            qualified_bots_python_files = [i for i in self.bot_list if i not in self.disqualified_bot_list]
            
            if DEBUG:
                self.logger.info(f'Qualified participents bot list (qualified_bots_python_files): {qualified_bots_python_files}')
            
            # Copy qualifying bot to competition run location - the ArchSimTrading competition environment
            for pyfile in qualified_bots_python_files:
                bot_exec_source_path = self.validate_bots_test_run_path + '/' + pyfile
                bot_exec_destination_path = self.bot_competition_exec_path + '/' #+ pyfile
                
                if DEBUG:
                    self.logger.info(f'Exec source path (bot_exec_source_path): {bot_exec_source_path}')
                    self.logger.info(f'Exec destination path (bot_exec_destination_path): {bot_exec_destination_path}')
                
                os.system('cp ' + bot_exec_source_path + ' ' + bot_exec_destination_path)
            
            # Generate batch scripts for each qualifying bot     
            from RunBots.RunBotsHandler import RunBotsHandler
            rbhandler = RunBotsHandler(self.event_id)
            rbhandler.generateBotBatchScripts(final_qualified_bot_list, competition_mode)
        self.mysqlconn.closeDB()
        if DEBUG:
            self.logger.info("----------------------------- ValidateHandler: Reached end of prepareQualifiedBotsForCompetition() in Validation Phase -----------------------------")

if __name__ == "__main__":
    if DEBUG:
        event_id=31
        validateHandler = ValidateHandler(event_id)