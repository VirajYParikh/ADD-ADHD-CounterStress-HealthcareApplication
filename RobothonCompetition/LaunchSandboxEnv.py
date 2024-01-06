from unittest import result
from configparser import ConfigParser
import pandas as pd
import time
import os
import docker
import subprocess
import argparse

from DBUtil.MySQLDBConn import MySQLDBConn
from DBUtil.InfluxDBConn import InfluxDBConn
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxStructureEncoder
from EmailUtil.EmailSender import EmailSender

# TODO: check to see what image/container names are for the test environments - may need to create separate tages for GlblMkts vs. HealthCare

sysconfigparse = ConfigParser()
sysconfigparse.read('../config/sys_config.ini')

client = docker.from_env()
emailer = EmailSender()

# Influx check

# Influxconnection_try = InfluxDBConn()

# botAgentID = '01'
# with Influxconnection_try.openInfluxDBBotBucket() as _client:
#     query = """
#                 import "strings"
#                 from(bucket: "%s")
#                 |> range(start: -1h)
#                 |> filter(fn: (r) => strings.containsStr(v: r["AgentID"], substr: "%s") == true)
#         """ % (Influxconnection_try.getBucket(), botAgentID)
#     tables = _client.query_api().query(query, org=Influxconnection_try.getOrg())
#     output = json.dumps(tables, cls=FluxStructureEncoder, indent=2)
#     json_records = json.loads(output)

# SQL check

mysqlconn = MySQLDBConn()
db_cursor = mysqlconn.openDB()
mysqlconn.selectDB(db_cursor)

bot_list = []  # list of participant bots (Python files)
disqualified_bot_list = []
download_data = None

sandbox_env_bots_path = sysconfigparse.get('TESTENV', 'sandbox_env_bots_path')
# **********************************PATH CHANGE **********************************
path = sysconfigparse.get('TESTENV', 'bots_download_path')
bot_competition_exec_path = sysconfigparse.get(
    'BOTS', 'bot_competition_exec_path')
VALIDATION_MAX_TRIES = int(sysconfigparse.get(
    'BOTS', 'validation_max_tries', fallback=3))


def generate_bot_files(event_id):
    global download_data
    global sandbox_env_bots_path
    global path

    strategy_info_query = """SELECT healthcare_competitioneventparticipant.robot_username, healthcare_algorithmtype.algo_name, healthcare_competitioneventparticipant.robot_username, healthcare_competitioneventparticipant.robot_password
    FROM healthcare_competitioneventparticipant
    JOIN healthcare_algorithmtype
    ON healthcare_competitioneventparticipant.implemented_algorithm_id = healthcare_algorithmtype.algo_type_id
    WHERE healthcare_competitioneventparticipant.event_id_id = %s""" % event_id

    db_cursor.execute(strategy_info_query)
    strategy_info = db_cursor.fetchall()
    db_cursor.close()

    db_cursor0 = mysqlconn.getConn().cursor()
    competition_mode_query = """SELECT test_mode_enabled FROM healthcare_competitionmode"""
    db_cursor0.execute(competition_mode_query)
    competition_mode_data = db_cursor0.fetchall()
    db_cursor0.close()
    competition_mode = competition_mode_data[0][0]

    db_cursor5 = mysqlconn.getConn().cursor()
    download_recs = """SELECT robot_username, code_url, event_id_id
                FROM healthcare_competitioneventparticipant
                WHERE event_id_id = %s""" % event_id
    db_cursor5.execute(download_recs)
    data = db_cursor5.fetchall()
    db_cursor5.close()

    download_data = pd.DataFrame(
        data, columns=['participant_username', 'code_url', 'event_id'])
    download_data['event_id'] = download_data['event_id'].astype('str')

    print(download_data)
    print(download_data['code_url'][0])
    df = pd.DataFrame(strategy_info, columns=[
        'id', 'password', 'event_id', 'strategy'])
    df['event_id'] = df['event_id'].astype('str')

    df = pd.DataFrame(strategy_info, columns=[
                      'Bot', 'Strategy', 'Username', 'Password'])
    df['Bot'] = df['Bot']+".py"

    bot_info_file_path = f"{path}/BotInfo.csv"
    df.to_csv(bot_info_file_path, encoding='utf-8')


def test_bots_results(bot, bots_results_path, mode, test_env_used):
    path = bots_results_path
    isExist = os.path.exists(path)

    if not isExist:
        os.mkdir(path)
        results_copy_cmd = f"sudo docker cp {bot}:/SandboxTestEnv/SimRunEnv/BotFiles/Results/. {bots_results_path}"
        os.system(results_copy_cmd)

    path_to_status_file = f"{path}/{bot}_status.csv"
    path_to_errors_file = f"{path}/{bot}_errors.csv"
    path_to_results_file = f"{path}/{bot}_results.csv"

    res_list_path = f"{path}"
    print(res_list_path)
    results_names_list = os.listdir(res_list_path)
    print("Results path list")
    print(results_names_list)
    if not os.path.exists(path_to_status_file) or (os.path.exists(path_to_errors_file) and not os.path.exists(path_to_results_file)):
        print("The Bot with username " + bot + " is invalid ")
        result = False
    else:
        print("The Bot with username " + bot + " is valid")
        result = True

    db_cursor1 = mysqlconn.getConn().cursor()
    participant_user_info_query = """SELECT au.first_name, au.last_name, au.email
    FROM auth_user AS au, healthcare_competitioneventparticipant AS cep
    WHERE cep.event_id_id=%s AND cep.robot_username=\'%s\' AND cep.user_id=au.id;""" % (event_id, bot)
    db_cursor1.execute(participant_user_info_query)
    user_data = db_cursor1.fetchall()
    db_cursor1.close()
    participant_firstname = user_data[0][0]
    participant_lastname = user_data[0][1]
    participant_email = user_data[0][2]

    print("The email of user " + bot + " is : " + participant_email)

    to_email = participant_email

    subject = "Healthcare Robothon Competition - Bot Status"

    if not os.path.exists(path_to_status_file) or (os.path.exists(path_to_errors_file) and not os.path.exists(path_to_results_file)):
        errors_read = 'Unknown internal error'
        if os.path.exists(path_to_errors_file):
            errors_read = pd.read_csv(path_to_errors_file)
            errors_read.columns = errors_read.iloc[0]
            errors_read = errors_read.iloc[:, 1]
            errors_read = [i for i in errors_read if pd.isna(i) != True]
        if mode == 'test':
            message = """Hello %s %s,\n
            Unfortunately, your bot did not qualify for the Healthcare Robothon Competition.
            See below for the reason(s) your bot failed to qualify for the competition.
            You can continue submitting bots during testing phase of the competition event.\n
            Failed reason(s): %s\n\n
            Good luck!\n
            The Healthcare Robothon Team
            """ % (participant_firstname, participant_lastname, errors_read)
        elif mode == 'validation':
            tries_left = max(VALIDATION_MAX_TRIES-test_env_used, 0)
            if tries_left == 0:
                message = """Hello %s %s,\n
                Unfortunately, your bot did not qualify for the Healthcare Robothon Competition.
                See below for the reason(s) your bot failed to qualify for the competition.\n
                Failed reason(s): %s\n\n
                And you have used all your %s tries. Only your latest successfully validated bot will be considered for the competition.\n\n
                Good luck!\n
                The Healthcare Robothon Team
                """ % (participant_firstname, participant_lastname, errors_read, VALIDATION_MAX_TRIES)
            else:
                message = """Hello %s %s,\n
                Unfortunately, your bot did not qualify for the Healthcare Robothon Competition.
                See below for the reason(s) your bot failed to qualify for the competition.
                You have %s tries left to validate your bot.\n\n
                Failed reason(s): %s\n\n
                Good luck!\n
                The Healthcare Robothon Team
                """ % (participant_firstname, participant_lastname, tries_left, errors_read)
    else:
        if mode == 'test':
            message = """Hello %s %s,\n
            Your Bot ran successfully and is ready to participate in the competition.
            When the validation phase starts, you will have %s tries then to validate your bot during validation phase.
            Good luck!\n
            The Healthcare Robothon Team
            """ % (participant_firstname, participant_lastname, VALIDATION_MAX_TRIES)
        elif mode == 'validation':
            tries_left = max(3-test_env_used, 0)
            if tries_left == 0:
                message = """Hello %s %s,\n
                Your Bot is validated and is ready to participate in the competition.
                Good luck!\n
                The Healthcare Robothon Team
                """ % (participant_firstname, participant_lastname)
            else:
                message = """Hello %s %s,\n
                Your Bot is validated and is ready to participate in the competition.
                You have %s tries left if you want to improve on your bot.\n\n
                Good luck!\n
                The Healthcare Robothon Team
                """ % (participant_firstname, participant_lastname, tries_left)

    try:
        emailer.sendEmail(to_email, subject, message)
    except Exception as e:
        print(f"Error sending email: {e}")
        pass

    return result


def prepare_validated_bot_file(result, bot):
    global path
    global bot_competition_exec_path
    downloaded_botfile_path = f"{path}/{bot}.py"
    destination_botfile_path = f"{bot_competition_exec_path}/{bot}.py"

    if result:
        # When result is True in validation mode, copy the bot to the ArchSimTrading folder
        copy_command = f"cp {downloaded_botfile_path} {destination_botfile_path}"
        print(f"Copying bot file to ArchSimTrading folder: {copy_command}")
        os.system(copy_command)


def update_used_counter_in_database(bot, mode):
    counter_column = "validation_count" if mode == "validation" else "num_test_environment_used"
    db_cursor2 = mysqlconn.getConn().cursor()
    current_test_env_used_query = """SELECT %s
                                FROM healthcare_competitioneventparticipant
                                WHERE event_id_id=%s AND robot_username =\'%s\'""" % (counter_column, event_id, bot)
    db_cursor2.execute(current_test_env_used_query)
    query_data = db_cursor2.fetchall()
    db_cursor2.close()
    test_env_used = query_data[0][0]
    test_env_used += 1

    db_cursor3 = mysqlconn.getConn().cursor()
    results_update_query = """UPDATE healthcare_competitioneventparticipant
                            SET %s = \'%s\'
                            WHERE event_id_id=%s AND robot_username = \'%s\'""" % (counter_column, test_env_used, event_id, bot)

    db_cursor3.execute(results_update_query)
    db_cursor3.close()

    db_cursor4 = mysqlconn.getConn().cursor()
    current_test_env_used_query = """SELECT %s
                                FROM healthcare_competitioneventparticipant
                                WHERE event_id_id=%s AND robot_username =\'%s\'""" % (counter_column, event_id, bot)
    db_cursor4.execute(current_test_env_used_query)
    query_data = db_cursor4.fetchall()
    db_cursor4.close()
    test_env_used = query_data[0][0]
    print(counter_column + ": " + str(test_env_used))
    return test_env_used


class Test_Bots_Script:
    mode = None
    sandbox_env_bots_path = None
    bots_download_path = None
    bots_results_path = None

    def __init__(self, user_id, mode):
        self.mode = mode
        self.readConfigFile()
        self.test_bots(user_id)

    def readConfigFile(self):
        sysconfigparse = ConfigParser()
        sysconfigparse.read('../config/sys_config.ini')
        self.sandbox_env_bots_path = sysconfigparse.get(
            'TESTENV', 'sandbox_env_bots_path')
        self.bots_download_path = sysconfigparse.get(
            'TESTENV', 'bots_download_path')
        self.bots_results_path = sysconfigparse.get(
            'TESTENV', 'bots_results_path')

    def clean_up_result_csvs(self, bot):
        # Clean up result csvs
        path_to_results_file = f"{self.bots_results_path}/{bot}_results.csv"
        path_to_status_file = f"{self.bots_results_path}/{bot}_status.csv"
        path_to_error_file = f"{self.bots_results_path}/{bot}_errors.csv"
        if os.path.exists(path_to_results_file):
            os.remove(path_to_results_file)
        if os.path.exists(path_to_status_file):
            os.remove(path_to_status_file)
        if os.path.exists(path_to_error_file):
            os.remove(path_to_error_file)

    def test_bots(self, user_id):
        if user_id == None:
            bots_list = download_data['participant_username']
        else:
            bots_list = [user_id]

        for bot in bots_list:
            self.clean_up_result_csvs(bot)

            print(
                "****************************************************************************")
            print(
                f"ROOT BOTS PATH (sandbox_env_bots_path): {self.sandbox_env_bots_path}")
            print(
                "****************************************************************************")

            container_cmd = f"sudo docker run --name {bot} -e BOT={bot} -e EVENTID={event_id} -v {self.sandbox_env_bots_path}:/SandboxTestEnv/SimRunEnv/BotFiles/ robo:latest"

            print(
                "****************************************************************************")
            print(f"ROOT BOTS PATH (container_cmd): {container_cmd}")
            print(
                "****************************************************************************")

            os.system(container_cmd)

        time.sleep(1)

        for bot in bots_list:
            test_env_used = update_used_counter_in_database(bot, self.mode)
            result = test_bots_results(
                bot, self.bots_results_path, self.mode, test_env_used)
            # if self.mode == "validation":
            prepare_validated_bot_file(result, bot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-user_id',
                        type=str,
                        nargs='?',
                        default=None
                        )
    parser.add_argument('-event_id',
                        type=int,
                        nargs='?',
                        default=None
                        )
    parser.add_argument('-mode',
                        type=str,
                        default="test",
                        nargs='?',
                        choices=['test', 'validation'])
    args = parser.parse_args()

    event_id = args.event_id
    generate_bot_files(event_id)
    Test_Bots_Script(args.user_id, args.mode)
    mysqlconn.closeDB()

    docker_prune_cmd = 'sudo docker system prune -f'
    subprocess.Popen(docker_prune_cmd, shell=True,
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    BotInfo_remove_command = f"rm {path}/BotInfo.csv"
    os.system(BotInfo_remove_command)
