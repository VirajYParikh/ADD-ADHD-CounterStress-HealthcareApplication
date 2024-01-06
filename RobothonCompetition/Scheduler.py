# -*- coding: utf-8 -*-
# Author: Ziyang Zeng

from configparser import ConfigParser
import datetime
import logging
import os
import signal
import subprocess
import pandas as pd
from rq import get_current_job

from RobothonHandler import RobothonHandler
from DBUtil.MySQLDBConn import MySQLDBConn
from MySQLdb.cursors import DictCursor

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory
SYS_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/sys_config.ini')

# Configure logger
LOG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'logs/robothon_healthcare.log')
LOG_LEVEL = logging.DEBUG
logger = None
banner = '*'*20

logger = logging.getLogger(LOG_FILE_PATH)
logger.setLevel(LOG_LEVEL)
fh = logging.FileHandler(LOG_FILE_PATH)
fh.setLevel(LOG_LEVEL)
ch = logging.StreamHandler()
ch.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

sysconfigparse = ConfigParser()
sysconfigparse.read(SYS_CONFIG_FILE_PATH)
VALIDATION_MAX_TRIES = int(sysconfigparse.get('BOTS', 'validation_max_tries', fallback=3))
healthcdb = 'robowebhealthcdb' # default database

def connect_to_mysqldb():
    # Connect to MySQL database
    mysqlconn = MySQLDBConn()
    db_cursor = mysqlconn.openDB()
    mysqlconn.selectDB(db_cursor, healthcdb)
    return mysqlconn, db_cursor

def save_job_data(key: str = None, value=None, data: dict = None):
    job = get_current_job()
    if job is None:
        return False
    if data is not None:
        job.meta = data
    elif key is not None and value is not None:
        job.meta[key] = value
    else:
        return False
    job.save_meta()
    return True

def save_job_message(message: str):
    return save_job_data(key='message', value=message)

def get_event_info(event_id: str):
    mysqlconn, db_cursor = connect_to_mysqldb()
    fetch_cursor = mysqlconn.getConn().cursor(cursorclass=DictCursor)
    # NOTE: no longer need to look at the competition_processed flag to determine whether a competition event was processe 
    #       event was processe because using APScheduled to schedule competitions by starting jBPM process instances
    # fetch_query = """SELECT * FROM HC_CompetitionEvent AS ce, HC_CompetitionEventQueue AS cq
    #                         WHERE ce.event_id='%s' AND cq.competition_event_id_id = ce.event_id AND cq.competition_processed=0;""" % (event_id)

    fetch_query = """SELECT * FROM HC_CompetitionEvent WHERE event_id='%s';""" % (event_id)
    fetch_cursor.execute(fetch_query)
    
    event_info_list = fetch_cursor.fetchall()
    fetch_cursor.close()
    db_cursor.close()
    mysqlconn.closeDB()
    if len(event_info_list) == 0:
        return None
    return event_info_list[0]

def get_participant_info(event_id: str):
    mysqlconn, db_cursor = connect_to_mysqldb()
    fetch_cursor = mysqlconn.getConn().cursor(cursorclass=DictCursor)
    
    fetch_query = """SELECT robot_username,robot_password,code_url,test_request,validation_count,disqualified, \
        qualified_to_compete,test_disqualified,num_code_submissions,num_test_environment_used,implemented_ml_id \
        FROM HC_CompetitionEventParticipant WHERE event_id_id='%s';""" % (event_id)
    fetch_cursor.execute(fetch_query)
    participant_info_list = fetch_cursor.fetchall()
    fetch_cursor.close()
    db_cursor.close()
    mysqlconn.closeDB()
    if len(participant_info_list) == 0:
        return None
    return participant_info_list


def is_event_in_phase(event, phase):
    dt = datetime.datetime.now()
    now_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
    if phase == 'coding':
        coding_start_date = str(event['coding_start_date'])
        coding_end_date = str(event['coding_end_date'])
        return now_datetime >= coding_start_date and now_datetime < coding_end_date
    elif phase == 'submit_validation':
        submit_validation_start_date = str(
            event['submit_validation_start_date'])
        submit_validation_end_date = str(event['submit_validation_end_date'])
        return now_datetime >= submit_validation_start_date and now_datetime < submit_validation_end_date
    elif phase == 'competition':
        competition_start_date = str(event['competition_start_date'])
        competition_end_date = str(event['competition_end_date'])
        return now_datetime >= competition_start_date and now_datetime < competition_end_date
    elif phase == 'evaluation':
        competition_end_date = str(event['competition_end_date'])
        return now_datetime >= competition_end_date
    else:
        return False

def get_event_phase(event):
    if is_event_in_phase(event, 'submit_validation'):
        return 'submit_validation'
    elif is_event_in_phase(event, 'coding'):
        return 'coding'
    elif is_event_in_phase(event, 'competition'):
        return 'competition'
    elif is_event_in_phase(event, 'evaluation'):
        return 'evaluation'
    else:
        return None

def get_sandbox_env_used(event_id: str, robot_username: str, mode: str):
    mysqlconn, db_cursor = connect_to_mysqldb()
    counter_column = "validation_count" if mode == "validation" else "num_test_environment_used"
    db_cursor2 = mysqlconn.getConn().cursor()
    current_test_env_used_query = """SELECT %s
                                FROM HC_CompetitionEventParticipant
                                WHERE event_id_id=%s AND robot_username =\'%s\'""" % (counter_column, event_id, robot_username)
    db_cursor2.execute(current_test_env_used_query)
    query_data = db_cursor2.fetchall()
    db_cursor2.close()
    db_cursor.close()
    mysqlconn.closeDB()
    return query_data[0][0]

def get_sandbox_env_result(robot_username: str):
    bots_results_path = sysconfigparse.get('TESTENV', 'bots_results_path', fallback=None)
    path_to_status_file = f"{bots_results_path}/{robot_username}_status.csv"
    path_to_errors_file = f"{bots_results_path}/{robot_username}_errors.csv"
    path_to_results_file = f"{bots_results_path}/{robot_username}_results.csv"

    if (not os.path.exists(path_to_status_file)) or (os.path.exists(path_to_errors_file) and not os.path.exists(path_to_results_file)):
        error_message = 'Unknown internal error'
        if os.path.exists(path_to_errors_file):
            errors_read = pd.read_csv(path_to_errors_file)
            errors_read.columns = errors_read.iloc[0]
            errors_read = errors_read.iloc[:, 1]
            errors_read = [i for i in errors_read if pd.isna(i) != True]
            error_message = str(errors_read)
        return False, error_message
    return True, None

def test_in_sandbox_env(event_id: str, robot_username: str):
    handler = RobothonHandler()
    handler.downloadOneBot(event_id=event_id, robot_username=robot_username)

    handler.requestSandboxEnv(event_id=event_id, robo_user=robot_username, mode='test')
    docker_prune_cmd = 'sudo docker system prune -f'
    subprocess.Popen(docker_prune_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    bot_status, bot_errors = get_sandbox_env_result(robot_username)
    save_job_data("bot_status", bot_status)
    if bot_errors:
        save_job_data("bot_errors", bot_errors)
    return True

def download_all_bots(event_id: str):
    handler = RobothonHandler()
    handler.downloadBots(event_id=event_id)
    return True

def download_metaml_bots(event_id: str, num_bots: int):
    handler = RobothonHandler()
    handler.downloadMetaMLBots(event_id=event_id, num_bots=num_bots)
    return True

def validate_all_bots(event_id: str, robot_username: str):
    handler = RobothonHandler()
    handler.validateBots(event_id, robot_username)

def validate_in_sandbox_env(event_id: str, robot_username: str):
    handler = RobothonHandler()
    handler.downloadOneBot(event_id=event_id, robot_username=robot_username)

    test_env_used = get_sandbox_env_used(event_id, robot_username, "validation")
    if test_env_used >= VALIDATION_MAX_TRIES:
        save_job_message(f"Validation requested more than {VALIDATION_MAX_TRIES} times")
        return False
    handler.requestSandboxEnv(event_id=event_id, robo_user=robot_username, mode='validation')
    docker_prune_cmd = 'sudo docker system prune -f'
    subprocess.Popen(docker_prune_cmd, shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    bot_status, bot_errors = get_sandbox_env_result(robot_username)
    save_job_data("bot_status", bot_status)
    if bot_errors:
        save_job_data("bot_errors", bot_errors)
    test_env_used = get_sandbox_env_used(event_id, robot_username, "validation")
    save_job_data("test_env_used", test_env_used)
    return True

def generate_bot_run_scripts(event_id: str):
    handler = RobothonHandler()
    handler.generateBotBatchScripts(event_id=event_id)
    return True

def start_all_server_processes(event_id: str):
    handler = RobothonHandler()
    handler.startAllServerProcesses(event_id=event_id)
    return True

def stop_all_server_processes(event_id: str):
    handler = RobothonHandler()
    handler.stopAllServerProcesses(event_id=event_id)
    return True

def check_processes_status(event_id: str):
    handler = RobothonHandler()
    return handler.checkProcessesStatus(event_id=event_id)

def run_bots(event_id: str):
    handler = RobothonHandler()
    handler.runBots(event_id=event_id)
    return True

def check_bots_completed(event_id: str, qualified_bots=None):
    handler = RobothonHandler()
    if qualified_bots is None:
        qualified_bots = handler.getQualifiedBots(event_id)
        qualified_bots = list(qualified_bots['id'])
    if len(qualified_bots) == 0:
        return True, []
    running_bots = []
    for bot in qualified_bots:
        if handler.checkRobotScriptRunning(bot):
            running_bots.append(bot)
    if len(running_bots) == 0:
        return True, []
    return False, running_bots

def kill_bots(event_id: str):
    handler = RobothonHandler()
    qualified_bots = handler.getQualifiedBots(event_id)
    qualified_bots = list(qualified_bots['id'])
    if len(qualified_bots) == 0:
        return True, []
    running_bot_pids = []
    for bot in qualified_bots:
        running_bot_pids += handler.getRobotScriptRunningPIDs(bot)
    if len(running_bot_pids) == 0:
        return True, []
    for pid in running_bot_pids:
        os.kill(pid, signal.SIGTERM)
    return check_bots_completed(event_id, qualified_bots)

def run_evaluation(event_id: str, force: bool = False):
    event = get_event_info(event_id)
    if event is None:
        raise Exception(f"Event {event_id} not found.")
    if DEBUG:
        logger.info(f"Competition Event #{event_id} - Start results computation")
    handler = RobothonHandler()
    handler.calculateResults(event_id=event_id)

    mysqlconn, db_cursor = connect_to_mysqldb()
    calcresults_cursor = mysqlconn.getConn().cursor()
    check_status = """SELECT name FROM HC_CompetitionPhaseStatus where name='Evaluate'"""
    results_phase_status_exists = calcresults_cursor.execute(check_status)

    if DEBUG:
        logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ results phase completed: {results_phase_status_exists}")

    if not results_phase_status_exists:
        insert_result = """insert into HC_CompetitionPhaseStatus
        (name, description, time_entered, competition_event_id_id, is_completed, num_order )
        values (%s,%s,%s,%s,%s,%s)"""
        calcresults_cursor.execute(insert_result,
                                   ('Evaluate',
                                    'The performance of the bots are evaluated.',
                                    datetime.datetime.now(),
                                    event_id,
                                    True,
                                    4))
        calcresults_cursor.close()

    # Update status - competition event completed

    competitioncomplete_cursor = mysqlconn.getConn().cursor()

    check_status = """SELECT name FROM HC_CompetitionPhaseStatus where name='Complete'"""
    completion_phase_status_exists = competitioncomplete_cursor.execute(check_status)

    if DEBUG:
        logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ competition phase completed: {completion_phase_status_exists}")

    if not completion_phase_status_exists:
        insert_result = """insert into HC_CompetitionPhaseStatus
        (name, description, time_entered, competition_event_id_id, is_completed, num_order )
        values (%s,%s,%s,%s,%s,%s)"""
        competitioncomplete_cursor.execute(insert_result,
                                           ('Complete',
                                            'The competition has completed.',
                                            datetime.datetime.now(),
                                               event_id,
                                               True,
                                               5))
        competitioncomplete_cursor.close()
    db_cursor.close()
    mysqlconn.closeDB()
    return True

def end_competition(event_id: str):
    print("Im here: Scheduler")
    handler = RobothonHandler()
    handler.endCompetition(event_id=event_id)
    return True

def run_competition_phase(event_id: str, force: bool = False):
    """
    Deprecated
    """
    event = get_event_info(event_id)
    if event is None:
        raise Exception(f"Event {event_id} not found.")
    handler = RobothonHandler()
    handler.startAllServerProcesses()
    handler.runBots(event_id=event_id)
    handler.stopAllServerProcesses()

    # Update status - Competition/Computation phase completed
    mysqlconn, db_cursor = connect_to_mysqldb()
    competition_cursor = mysqlconn.getConn().cursor()

    check_status = """SELECT name FROM HC_CompetitionPhaseStatus where name='Compute'"""
    competition_phase_status_exists = competition_cursor.execute(check_status)

    if DEBUG:
        logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ competition phase completed: {competition_phase_status_exists}")

    if not competition_phase_status_exists:
        insert_result = """insert into HC_CompetitionPhaseStatus
        (name, description, time_entered, competition_event_id_id, is_completed, num_order )
        values (%s,%s,%s,%s,%s,%s)"""
        competition_cursor.execute(insert_result,
                                   ('Compute',
                                    'The competition bots are running.',
                                    datetime.datetime.now(),
                                    event_id,
                                    True,
                                    3))
        competition_cursor.close()
    db_cursor.close()
    mysqlconn.closeDB()
    return True
