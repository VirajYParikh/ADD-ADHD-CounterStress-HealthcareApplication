import os
import shutil
import argparse
import logging
from configparser import ConfigParser
import os

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory
SYS_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/sys_config.ini')

class DeleteBotsHandler:
    logger = None
    bots_download_path = None
    bots_validate_path = None
    bots_result_path = None
    bots_result_val_path = None
    event_id = 0

    def __init__(self, event_id):
        self.logger.info("DeleteBotsHandler: Delete Bots Handler")
        self.event_id = event_id
        self.configureLogging()
        self.readConfigFile()

    def configureLogging(self):
        LOG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'logs/robothon_glblmkts.log')
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
        configparse.read(SYS_CONFIG_FILE_PATH)
        self.bots_download_path = '%s/competition_%s' % (sysconfigparse.get('BOTS', 'bots_download_path'), self.event_id)
        self.bots_validate_path = '%s/competition_%s' % (sysconfigparse.get('BOTS', 'bots_validate_path'), self.event_id)
        self.bots_result_path = '%s/competition_%s' % (sysconfigparse.get('BOTS', 'bots_result_path'), self.event_id)
        self.bots_result_val_path = '%s/competition_%s' % (sysconfigparse.get('BOTS', 'bots_result_val_path'), self.event_id)

    def deleteDownloadedBots(self):
        try:
            shutil.rmtree(self.bots_download_path)
            if DEBUG:
                self.logger.info("Download directory deleted")
        except OSError as e:
            self.logger.error("Error: %s : %s" % (self.bots_download_path, e.strerror))

    def deleteValidatedBots(self):
        try:
            shutil.rmtree(self.bots_validate_path)
            if DEBUG:
                self.logger.info("Validate directory deleted")
        except OSError as e:
            self.logger.error("Error: %s : %s" % (self.bots_validate_path, e.strerror))

    def deleteResultsBots(self):
        try:
            shutil.rmtree(self.bots_result_path)
            if DEBUG:
                self.logger.info("Result directory deleted")
        except OSError as e:
            self.logger.error("Error: %s : %s" % (self.bots_result_path, e.strerror))

    def deleteResultsValBots(self):
        try:
            shutil.rmtree(self.bots_result_val_path)
            if DEBUG:
                self.logger.info("Result Validation directory deleted")
        except OSError as e:
            self.logger.error("Error: %s : %s" % (self.bots_result_val_path, e.strerror))

    def deleteAllBotsDirectories(self):
        self.deleteDownloadedBots()
        self.deleteValidatedBots()
        self.deleteResultsBots()
        self.deleteResultsValBots()

if __name__ == "__main__":
    myargparser = argparse.ArgumentParser()
    myargparser.add_argument('--event_id',
                             type=str,
                             const="1",
                             nargs='?',
                             default='1',
                             help='times')
    args = myargparser.parse_args()

    dhandler = DeleteBotsHandler(event_id=1)
    dhandler.deleteAllBotsDirectories()
