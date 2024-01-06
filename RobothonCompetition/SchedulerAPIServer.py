# -*- coding: utf-8 -*-
# Author: Ziyang Zeng

from configparser import ConfigParser
import Scheduler
from flask import Flask, request
from redis import Redis
from rq import Queue
import requests

configparse = ConfigParser()
configparse.read('../config/db_config.ini')
REDIS_URL = configparse.get('REDIS', 'redis_url')

sysconfigparse = ConfigParser()
sysconfigparse.read('../config/sys_config.ini')
VALIDATION_MAX_TRIES = int(sysconfigparse.get(
    'BOTS', 'validation_max_tries', fallback=3))


redis_conn = Redis.from_url(REDIS_URL)
q = Queue(connection=redis_conn)

app = Flask(__name__)


def count_words_at_url(url):
    resp = requests.get(url)
    return len(resp.text.split())


@app.route("/")
def hello_world():
    return {'api_status': 'success'}


@app.route("/health")
def health():
    return {'api_status': 'success'}


@app.route("/get_job_status", methods=['GET'])
def get_job_status():
    job_id = request.args.get('job_id')
    job = q.fetch_job(job_id)
    if job is None:
        return {'api_status': 'failure', 'message': 'job id not found'}
    return {'api_status': 'success', 'job_status': job.get_status(), 'job_result': job.result, 'job_data': job.meta}


@app.route("/cancel_job", methods=['POST'])
def cancel_job():
    body = request.get_json()
    job_id = body.get('job_id', '')
    job = q.fetch_job(job_id)
    if job is None:
        return {'api_status': 'failure', 'message': 'job id not found'}
    job.cancel()
    return {'api_status': 'success', 'job_status': job.get_status()}


@app.route("/request_bot_test", methods=['POST'])
def test_bot():
    force = request.args.get('force', default=False, type=bool)
    body = request.get_json()
    print(body)
    event_id = body.get('event_id', '')
    robot_username = body.get('robot_username', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}

    job = q.enqueue(Scheduler.test_in_sandbox_env,
                    args=(event_id, robot_username))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/request_bot_validation", methods=['POST'])
def validate_bot():
    force = request.args.get('force', default=False, type=bool)
    body = request.get_json()
    event_id = body.get('event_id', '')
    robot_username = body.get('robot_username', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    sandbox_env_used = Scheduler.get_sandbox_env_used(
        event_id, robot_username, 'validation')
    if sandbox_env_used >= VALIDATION_MAX_TRIES:
        return {'api_status': 'failure', 'message': f'all {VALIDATION_MAX_TRIES} validation tries used up'}
    job = q.enqueue(Scheduler.validate_in_sandbox_env,
                    args=(event_id, robot_username))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/get_sandbox_status", methods=['GET'])
def get_sandbox_status():
    event_id = request.args.get('event_id')
    robot_username = request.args.get('robot_username')
    event = Scheduler.get_event_info(event_id)
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


@app.route("/generate_bot_run_scripts", methods=['POST'])
def generate_bot_run_scripts():
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    job = q.enqueue(Scheduler.generate_bot_run_scripts, args=(event_id,))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/start_processes", methods=['POST'])
def start_all_server_processes():
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    job = q.enqueue(Scheduler.start_all_server_processes, args=(event_id,))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/stop_processes", methods=['POST'])
def stop_all_server_processes():
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    job = q.enqueue(Scheduler.stop_all_server_processes, args=(event_id,))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/checkprocessesstatus", methods=['GET'])
def check_processes_status():
    event_id = request.args.get('event_id', default='')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    running, running_processes = Scheduler.check_processes_status(event_id)
    return {'api_status': 'success', 'running': running, 'running_processes': running_processes}


@app.route("/run_bots", methods=['POST'])
def schedule_run_bots():
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    job = q.enqueue(Scheduler.run_bots, args=(event_id,))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/check_bots_completed", methods=['GET'])
def check_bots_completed():
    event_id = request.args.get('event_id', default='')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    bots_completed, running_bots = Scheduler.check_bots_completed(event_id)
    return {'api_status': 'success', 'bots_completed': bots_completed, 'running_bots': running_bots}


@app.route("/kill_bots", methods=['POST'])
def kill_bots():
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}
    kill_successful, stubburn_bots = Scheduler.kill_bots(event_id)
    return {'api_status': 'success', 'kill_successful': kill_successful, 'stubburn_bots': stubburn_bots}


@app.route("/calculate_results", methods=['POST'])
def schedule_evaluation():
    force = request.args.get('force', default=False, type=bool)
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}

    job = q.enqueue(Scheduler.run_evaluation, args=(event_id, force))
    return {'api_status': 'success', 'job_id': job.id}


@app.route("/schedule_competition_phase", methods=['POST'])
def schedule_competition_phase():
    """
    Deprecated, for debugging only
    """
    force = request.args.get('force', default=False, type=bool)
    body = request.get_json()
    event_id = body.get('event_id', '')
    event = Scheduler.get_event_info(event_id)
    if event is None:
        return {'api_status': 'failure', 'message': 'event not found'}

    job = q.enqueue(Scheduler.run_competition_phase, args=(event_id, force))
    return {'api_status': 'success', 'job_id': job.id}
