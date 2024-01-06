# -*- coding: utf-8 -*-
# Author: Ziyang Zeng

from configparser import ConfigParser
# import os

# COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory
# DB_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/db_config.ini')

# print("------------------------ SchedulerWorkerSettings.py\n")
# print(f"COMPETITION_ROOT_DIR: {COMPETITION_ROOT_DIR}")
# print(f"DB_CONFIG_FILE_PATH: {DB_CONFIG_FILE_PATH}")
# print("\n")

configparse = ConfigParser()
configparse.read('../config/db_config.ini')
# configparse.read(DB_CONFIG_FILE_PATH)

REDIS_URL = configparse.get('REDIS', 'redis_url')

QUEUES = ['high', 'default', 'low']
