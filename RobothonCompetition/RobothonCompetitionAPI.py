import argparse
from configparser import ConfigParser
import pandas as pd
from redis import Redis
from rq import Queue
import requests
from requests import request
import os
import Scheduler

configparse = ConfigParser()
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory
DB_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/db_config.ini')
SYS_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/sys_config.ini')
configparse.read(DB_CONFIG_FILE_PATH)
#configparse.read('../config/db_config.ini')
REDIS_URL = configparse.get('REDIS', 'redis_url')
#REDIS_URL = 'redis://127.0.0.1:6379/'
sysconfigparse = ConfigParser()
sysconfigparse.read(SYS_CONFIG_FILE_PATH)
#sysconfigparse.read('../config/sys_config.ini')
VALIDATION_MAX_TRIES = int(sysconfigparse.get('BOTS', 'validation_max_tries', fallback=3))

redis_conn = Redis.from_url(REDIS_URL)
q = Queue(connection=redis_conn)
force = False
competition_phase = ''
banner = "*"*30

class RobothonCompetitionAPI:
    event_id = None
    
    def __init__(self, *args, **kwargs):
        kwargs2 = kwargs.copy()
        self.event_id = kwargs2["event_id"]
        # self.competition_phase = kwargs2["competition_phase"]

    def get_job_status(self, job_id):
        job = q.fetch_job(job_id)
        if job is None:
            return {'api_status': 'failure', 'message': 'job id not found'}
        return {'api_status': 'success', 'job_status': job.get_status(), 'job_result': job.result, 'job_data': job.meta}
        
    def cancel_job(self, job_id):
        job = q.fetch_job(job_id)
        if job is None:
            return {'api_status': 'failure', 'message': 'job id not found'}
        job.cancel()
        return {'api_status': 'success', 'job_status': job.get_status()}

    def download_all_bots(self):
        print(f"{banner} Downloading bots... {banner}")
        event = Scheduler.download_all_bots(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        return {'api_status': 'success', 'message': 'Bots downloaded for '}

    def download_metaml_bots(self, num_bots):
        print(f"{banner} Downloading bots from MetaML... {banner}")
        event = Scheduler.download_metaml_bots(self.event_id, num_bots)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        return {'api_status': 'success', 'message': 'MetaML bots downloaded for '}
    
    # Invoked by Django RobothonWeb site (robo_username provided by website)
    def test_bot(self, robot_username):
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        
        job = q.enqueue(Scheduler.test_in_sandbox_env, args=(self.event_id, robot_username))
        return {'api_status': 'success', 'job_id': job.id}

    # def download_bots(self):
    #     print(f"{banner} DOWNLOAD BOTS {banner}")

   # Invoked by Django RobothonWeb site (robo_username provided by website)
    def validate_bot(self, robo_username):
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        
        sandbox_env_used = Scheduler.get_sandbox_env_used(self.event_id, robot_username, 'validation')
        if sandbox_env_used >= VALIDATION_MAX_TRIES:
            return {'api_status': 'failure', 'message': f'all {VALIDATION_MAX_TRIES} validation tries used up'}
        job = q.enqueue(Scheduler.validate_in_sandbox_env, args=(self.event_id, robot_username))
        return {'api_status': 'success', 'job_id': job.id}

    # def validate_bots(self):
    #     print(f"{banner} VALIDATE BOTS {banner}")        

    def validate_all_bots(self):
        print(f"{banner} VALIDATE BOTS {banner}")
        
        # event = Scheduler.get_event_info(self.event_id)
        # if event is None:
        #     return {'api_status': 'failure', 'message': 'event {self.event} not found'}

        # print("COMPETITION EVENT FETCHED: \n")
        # print(event)
        # print("\n")
        # print("Data structure of event: \n")
        # print(type(event))
        # print("\n")
        
        data = Scheduler.get_participant_info(self.event_id)
        if data is None:
            return {'api_status': 'failure', 'message': 'Participant list not found for event: {self.event}'}
        
        print("COMPETITION PARTICIPANT DATA FETCHED: \n")
        print(data)
        print("\n")
        print("Data structure of data: \n")
        print(type(data))
        print("\n")
        
        participants = pd.DataFrame(data, columns=['robot_username','robot_password','code_url','test_request','validation_count','disqualified', \
        'qualified_to_compete','test_disqualified','num_code_submissions','num_test_environment_used','implemented_ml_id'])
        
        #participants['event_id'] = participants['event_id'].astype('str')
        
        print("Participant dataframe: \n")
        print(participants)
        print("\n")
        
        for i in range(len(participants)):
            robot_username = participants['robot_username'][i]
            print(f"CURRENT robot_username: {robot_username}")

        # **** TODO: ENABLE THIS WHEN CREATE THE SANDBOX TEST ENV        
        # sandbox_env_used = Scheduler.get_sandbox_env_used(self.event_id, robot_username, 'validation')
        # if sandbox_env_used >= VALIDATION_MAX_TRIES:
        #     return {'api_status': 'failure', 'message': f'all {VALIDATION_MAX_TRIES} validation tries used up'}
        job = q.enqueue(Scheduler.validate_all_bots, args=(self.event_id, robot_username))
        #job = q.enqueue(Scheduler.validate_in_sandbox_env, args=(self.event_id, robot_username))
        print(f"{banner} Validate Bots Status:: job_status: {job.get_status()}, job_result: {job.result}, job_data: {job.meta} {banner}")
    
    def get_sandbox_status(self, robo_username):
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        
        event_phase = Scheduler.get_event_phase(event)
        sandbox_env_used = 0
        if event_phase == 'coding':
            sandbox_env_used = Scheduler.get_sandbox_env_used(
                event_id, robot_username, 'test')
        elif event_phase == 'submit_validation':
            sandbox_env_used = Scheduler.get_sandbox_env_used(
                event_id, robot_username, 'validation')
        if sandbox_env_used == 0:
            bot_status, bot_errors = False, "Sandbox not used in this phase"
        else:
            bot_status, bot_errors = Scheduler.get_sandbox_env_result(
                robot_username)
        return {
            'api_status': 'success',
            'event_phase': event_phase,
            'sandbox_env_used': sandbox_env_used,
            'bot_status': bot_status,
            'bot_errors': bot_errors
        }

    def generate_bot_run_scripts(self):
        print(f"{banner} GENERATE BOT RUN SCRIPTS {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        job = q.enqueue(Scheduler.generate_bot_run_scripts, args=(self.event_id,))
        print(f"{banner} Generate Bots Scripts Status:: job_status: {job.get_status()}, job_result: {job.result}, job_data: {job.meta} {banner}")

    def start_all_server_processes(self):
        print(f"{banner} STARTING ALL PROCESSES {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        job = q.enqueue(Scheduler.start_all_server_processes, args=(self.event_id,))
        print(f"{banner} Start All Processes Status:: job_status: {job.get_status()}, job_result: {job.result}, job_data: {job.meta} {banner}")
    
    def stop_all_server_processes(self):
        print(f"{banner} STOPPING ALL PROCESSES {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        job = q.enqueue(Scheduler.stop_all_server_processes, args=(self.event_id,))
        
    def check_processes_status(self):
        print(f"{banner} CHECK PROCESSES {banner}")
        
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        running, running_processes = Scheduler.check_processes_status(self.event_id)
        return {'api_status': 'success', 'running': running, 'running_processes': running_processes}

    # def check_processes(self):
    #     print(f"{banner} CHECK PROCESSES {banner}")

    def schedule_run_bots(self):
        print(f"{banner} RUN BOTS {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        job = q.enqueue(Scheduler.run_bots, args=(self.event_id,))
        print(f"{banner} Run Bots Status:: job_status: {job.get_status()}, job_result: {job.result}, job_data: {job.meta} {banner}")

    def check_bots_completed(self):
        print(f"{banner} CHECK BOTS {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        bots_completed, running_bots = Scheduler.check_bots_completed(self.event_id)
        return {'api_status': 'success', 'bots_completed': bots_completed, 'running_bots': running_bots}
        
    # def run_bots(self):
    #     print(f"{banner} RUN BOTS {banner}")
    
    # def check_bots(self):
    #     print(f"{banner} CHECK BOTS {banner}")

    def kill_bots(self):
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        kill_successful, stubburn_bots = Scheduler.kill_bots(self.event_id)
        return {'api_status': 'success', 'kill_successful': kill_successful, 'stubburn_bots': stubburn_bots}

    def schedule_evaluation(self):
        print(f"{banner} CALCULATE RESULTS {banner}")
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}

        force = False
        #job = q.enqueue(Scheduler.run_evaluation, args=(self.event_id))
        job = q.enqueue(Scheduler.run_evaluation, args=(event_id, force))
        print(f"{banner} Calculate Results Status:: job_status: {job.get_status()}, job_result: {job.result}, job_data: {job.meta} {banner}")
    
    # def calculate_results(self):
    #     print(f"{banner} CALCULATE RESULTS {banner}")
    
    def schedule_competition_phase(self):
        """
        Deprecated, for debugging only
        """
        force = request.args.get('force', default=False, type=bool)
        event = Scheduler.get_event_info(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}

        job = q.enqueue(Scheduler.run_competition_phase, args=(self.event_id, force))
        return {'api_status': 'success', 'job_id': job.id}   
    
    def end_competition(self):
        print(f"{banner} ENDING COMPETITION {banner}")
        event = Scheduler.get_event_info(self.event_id)
        event = Scheduler.end_competition(self.event_id)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        return {'api_status': 'success', 'message': 'MetaML bots downloaded for '}
        print(event)
        if event is None:
            return {'api_status': 'failure', 'message': 'event not found'}
        
        job = q.enqueue(Scheduler.end_competition, args=(self.event_id,))
        print(job)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-event_id',
                        type=str,
                        help='Event ID')
    parser.add_argument('-competition_phase',
                        type=str,
                        help="Competition Phase")
    
    args = parser.parse_args()
    event_id = args.event_id
    competition_phase = args.competition_phase
    event_id = event_id.strip('\"')
    competition_phase = competition_phase.strip('\"')

    num_metaml_bots = 3
    
    print("\n")
    print(f"{banner} -- EVENT ID -- >>{event_id}<< -- {banner}")
    print(f"{banner} -- COMPETITION PHASE -- >>{competition_phase}<< -- {banner}")
    print("\n")
    
    new_competition = RobothonCompetitionAPI(event_id=event_id, competition_phase=competition_phase)
    if competition_phase == "DownloadBots":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        # new_competition.download_all_bots()
    elif competition_phase == "ValidateBots":
        # print(f"-------- COMPETITION PHASE: {competition_phase}")
        # new_competition.validate_all_bots()
        if num_metaml_bots > 0:
            new_competition.download_metaml_bots(num_metaml_bots)
    elif competition_phase == "GenerateBotRunScripts":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        #new_competition.generate_bot_run_scripts()
    elif competition_phase == "StartAllServerProcesses":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        #new_competition.start_all_server_processes()
    elif competition_phase == "RunBots":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        # new_competition.schedule_run_bots()
    elif competition_phase == "CalculateResults":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        # new_competition.schedule_evaluation()
    elif competition_phase == "CheckBots":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        #new_competition.check_bots()
    elif competition_phase == "CheckProcesses":
        print(f"-------- COMPETITION PHASE: {competition_phase}")
        #new_competition.check_processes_status()
    elif competition_phase == "StopAllServerProcesses":
        # print(f"-------- COMPETITION PHASE: {competition_phase}")
        # print("------------------ Killing bots -------------------------")
        # new_competition.kill_bots()
        # print("------------------ Stopping server processes -------------------------")
        # new_competition.stop_all_server_processes()
        # print("------------------ Ending competition -------------------------")
        new_competition.end_competition()
        print("------------------ Competition ended -------------------------")