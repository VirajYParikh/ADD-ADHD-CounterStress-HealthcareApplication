from configparser import ConfigParser
import pandas as pd
import fnmatch
import os
import random
import argparse
import logging
import glob
from DBUtil.MySQLDBConn import MySQLDBConn

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

class RunBotsHandler:
    logger = None
    event_id = 0
    qualified_bots_exec_file_list = []
    bot_competition_exec_path = None

    def __init__(self, event_id):
        # Configure logging
        self.configureLogging()
        self.readConfigFile()

        if DEBUG:
            self.logger.info("RunBotsHandler: Set up Bots for Competition Execution")

        self.event_id = event_id

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
        self.bot_competition_exec_path = os.path.abspath(sysconfigparse.get('BOTS', 'bot_competition_exec_path'))

    def getQualifiedBots(self, event_id):
        bots_file_paths = glob.glob(f"{self.bot_competition_exec_path}/*.py")
        qualified_bot_usernames = [os.path.basename(bot_file_path).replace('.py', '') for bot_file_path in bots_file_paths]
        mysqlconn, db_cursor = connect_to_mysqldb()
        strategy_info_query = """SELECT HC_CompetitionEventParticipant.robot_username, HC_CompetitionEventParticipant.robot_password, HC_CompetitionEventParticipant.event_id_id, HC_MachineLearningModelType.mlmodel_name
        FROM HC_CompetitionEventParticipant
        JOIN HC_MachineLearningModelType
        ON HC_CompetitionEventParticipant.implemented_algorithm_id = HC_MachineLearningModelType.mlmodel_type_id
        WHERE HC_CompetitionEventParticipant.event_id_id = %s""" % event_id
        db_cursor.execute(strategy_info_query)
        strategy_info = db_cursor.fetchall()
        db_cursor.close()
        mysqlconn.closeDB()

        df = pd.DataFrame(strategy_info, columns=['id', 'password', 'event_id', 'strategy'])
        df['event_id'] = df['event_id'].astype('str')

        if DEBUG:
            self.logger.info(f"Strategy Info Dataframe\n\n {df}")

        final_qualified_bot_list = df[df['id'].isin(qualified_bot_usernames)].reset_index(drop=True)
        return final_qualified_bot_list

    def generateBotBatchScripts(self, qualified_bots, competition_mode):
        if DEBUG:
            self.logger.info("Run Bots Handler")

        # List of possible actions, symbols, size and maxtime to configure bots - can expand this list
        action = ['buy', 'sell']
        symbol = ['ZNH0:MBO', 'ZFH0:MBO']
        size = [25, 50, 100]
        maxtime = [60, 120, 300, 600]

        # Compeitition is in test mode
        if (competition_mode == 1):
            maxtime = [15, 30, 45, 60]

        # Generate batch (.sh) scripts for each qualifying bot
        for i in range(len(qualified_bots)):
            current_script_filename = 'run_%s_bots_event_%s.sh' % (
                qualified_bots['id'][i], self.event_id)
            self.qualified_bots_exec_file_list.append(current_script_filename)
            if not os.path.exists(self.bot_competition_exec_path + '/' + current_script_filename):
                with open(self.bot_competition_exec_path + '/' + current_script_filename, mode='w', encoding='utf-8') as f:

                    if DEBUG:
                        self.logger.info('Qualified bots execution script for participant %s, event %s was created!' % (qualified_bots['id'][i], self.event_id))

                    f.close()

            with open(self.bot_competition_exec_path + '/' + current_script_filename, mode='w', encoding='utf-8') as f:
                for j in range(30):
                    # (ORIG) f.writelines('python %s.py --action=\'%s\' --symbol \'%s\' --size %s --maxtime %s --strategy %s --bot_id %s --username %s --password \'%s\' &\n' %
                    f.writelines('python %s/%s.py --action=\'%s\' --symbol \'%s\' --size %s --maxtime %s --strategy %s --bot_id %s --username %s --password \'%s\' &\n' %
                                 (
                                     self.bot_competition_exec_path,
                                     qualified_bots['id'][i],
                                     random.choice(action),
                                     random.choice(symbol),
                                     random.choice(size),
                                     random.choice(maxtime),
                                     qualified_bots['strategy'][i].replace(
                                         ' ', ''),
                                     qualified_bots['id'][i] +
                                     '_eventID_' + str(self.event_id),
                                     # 'test',
                                     # 'test')
                                     qualified_bots['id'][i],
                                     qualified_bots['password'][i])
                                 )
                f.close()

            os.system('chmod a+rwx %s/run_%s_bots_event_%s.sh' %
                      (self.bot_competition_exec_path, qualified_bots['id'][i], self.event_id))
            # with open(self.bot_competition_exec_path + '/run_%s_bots_event_%s.sh' % (qualified_bots['id'][i], self.event_id), mode='r', encoding='utf-8') as f:
            #     if DEBUG:
            #         self.logger.info(f.read())
            #     f.close()

        if DEBUG:
            self.logger.info(
                f"Final list of qualifying bots batch script files: {self.qualified_bots_exec_file_list}")

        self.prepareCompetitionBatchScript()

        if DEBUG:
            self.logger.info(
                "----------------------------- RunBotsHandler: Reached end of generateBotBatchScripts() in Validation Phase -----------------------------")

    def prepareCompetitionBatchScript(self):
        # Create a competition event run script that executes all qualifying bots batch scripts
        if DEBUG:
            self.logger.info('Qualifying bots batch script files for competition event # %s' % self.event_id)
            self.logger.info(self.qualified_bots_exec_file_list)

        if not os.path.exists(self.bot_competition_exec_path + '/run_event_%s_competition.sh' % self.event_id):
            with open(self.bot_competition_exec_path + '/run_event_%s_competition.sh' % self.event_id, mode='w', encoding='utf-8') as f:
                if DEBUG:
                    self.logger.info('competition batch for event %s created!' % (self.event_id))

                f.close()

        with open(self.bot_competition_exec_path + '/run_event_%s_competition.sh' % self.event_id, mode='w', encoding='utf-8') as f:
            for i in self.qualified_bots_exec_file_list:
                # (ORIG) f.writelines('./%s &\n' % i)
                f.writelines('%s/%s &\n' % (self.bot_competition_exec_path, i))

            f.close()

        os.system('chmod a+rwx %s/run_event_%s_competition.sh' % (self.bot_competition_exec_path, self.event_id))
        # with open('%s/run_event_%s_competition.sh' % (self.bot_competition_exec_path, self.event_id), mode='r', encoding='utf-8') as f:
        #     self.logger.info(f.read())
        #     f.close()
        if DEBUG:
            self.logger.info(
                "----------------------------- RunBotsHandler: Reached end of prepareCompetitionBatchScript() in Validation Phase -----------------------------")

    def competition_stress_detection(id,maxtime,event_id,validated_code_path):
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resultpath = os.path.join(proj_root, 'bots/result/competition_'+ str(event_id) +'/det/'+ id)
        apipath = os.path.join(proj_root, 'bots/')
        validated_file = validated_code_path+'/%s.py'%id
        command = ['python', validated_file, '--maxtime', str(args.maxtime), '--result_path', resultpath, '--data_api', apipath, '--mode','1']
        
        if DEBUG:
            self.logger.info("Stress Detection: Start BOT: ", id)
        try:
            p = subprocess.run(command, timeout = args.maxtime,capture_output=True)
            if p.returncode == 0:
                return 1
            else:
                return 0
                        
        except subprocess.TimeoutExpired:
            return 0
        except:
            return 0
        
    def competition_action_evaluation(id,maxtime,event_id,validated_code_path):
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resultpath = os.path.join(proj_root, 'bots/result/competition_'+ str(event_id) +'/act/'+ id)
        apipath = os.path.join(proj_root, 'bots/')
        validated_file = validated_code_path+'/%s.py'%id
        command = ['python', validated_file, '--maxtime', str(args.maxtime), '--result_path', resultpath, '--data_api', apipath, '--mode','2']
        if DEBUG:
            self.logger.info("Action Evaluation: Start BOT: ",id)
        try:
            p = subprocess.run(command, timeout = args.maxtime,capture_output=True)
            if p.returncode == 0:
                return 1
            else:
                return 0
                        
        except subprocess.TimeoutExpired:
            return 0
        except:
            return 0

    def runCompetitionBots(self):
        if DEBUG:
            self.logger.info(f"Running bots for the Global Markets Competition # {self.event_id}")

        # TODO: look in bots_competition/__main__.py to see how to run these bots - maybe consider generating scripts for these similar to citi

        # Run the qualifying bots in the Global Markets competition event
        os.system(self.bot_competition_exec_path + '/run_event_%s_competition.sh' % self.event_id)
        # os.chdir(self.bot_competition_exec_path)
        #os.system('./run_event_%s_competition.sh' % self.event_id)

if __name__ == "__main__":
    myargparser = argparse.ArgumentParser()
    myargparser.add_argument('--event_id',
                             type=str,
                             const='text',
                             nargs='?',
                             default='text')
    args = myargparser.parse_args()

    rbh = RunBotsHandler()
    rbh.prepare_competition_batch()