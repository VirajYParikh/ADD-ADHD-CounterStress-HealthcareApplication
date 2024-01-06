from os import path
from pathlib import Path
import subprocess
import sys
import os
import pathlib
import psutil
import time
import logging

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # ../RobothonCompetition/ directory
SCRIPTS_PATH = COMPETITION_ROOT_DIR + "/Scripts/"

class ServerHandler:
    logger = None

    # TODO: see how event_id is being passed via kwargs to DownloadHandler from RobothonHandler
    #       and see if can pass logger handle to all classes via __init__ using kwargs

    def __init__(self):
        # Configure logging
        self.configureLogging()

        # Activate Python venv
        # self.activatePythonVenv()

        # Check if RabbitMQ server is running
        self.checkRabbitMQServerRunning()

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

    def activatePythonVenv(self):
        # TODO: figure out how to refresh shell so can activate the venv
        #       problem is when try to run activate command, it first
        #       expects to run 'conda init <SHELL_NAME=bash>' but
        #       need to restart the shell when run the init command - need
        #       to figure out how to fix this
        #subprocess.run(cmd, capture_output=False, shell=True)
        #cmd = "conda init bash; conda activate py37_default"
        cmd = "conda activate py37_default"
        self.logger.info(f"ServerHandler: activating Python venv with command: {cmd}")
        #subprocess.run(cmd, capture_output=False, shell=True, execute='/bin/bash')
        #subprocess.run(cmd, capture_output=False, shell=True)
        subprocess.run(cmd, capture_output=False)

    def checkIfProcessRunning(self, processName):
        '''
            Check for any running processes that match processName
        '''
        processNames = [processName] if type(processName) == str else processName
        processNames = [processName.lower() for processName in processNames]
        # iterate over running processes
        for proc in psutil.process_iter():
            #print(f'******** current process name: {proc.name()}')
            #self.logger.debug(f'ServerHandler: current process name: {proc.name()}')
            try:
                # check if process name equals processName
                if processNames.count(proc.name().lower()) > 0:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                self.logger.error(f"An error occurred: {e}")
                pass
        return False

    def findProcessIDByName(self, processName):
        '''
            Get a list of all PIDs of all running processes that match processName
        '''
        listOfProcessObjects = []

        # iterate over all running processes
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
                self.logger.debug(f'pinfo: {pinfo}')
                # check if process name matches processName
                if processName.lower() in pinfo['name'].lower():
                    listOfProcessObjects.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return listOfProcessObjects

    def getProcessInfo(self, processName):
        self.logger.debug("---- ServerHandler: find PIDs of a running process by name ----")
        listOfProcessIds = self.findProcessIDByName(processName)
        if len(listOfProcessIds) > 0:
            self.logger.debug('ServerHandler: Process Exists | PID and other process details: ')
            for elem in listOfProcessIds:
                processID = elem['pid']
                processName = elem['name']
                processCreationTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(elem['create_time']))
                self.logger.debug(f'ServerHandler: {processID}, {processName}, {processCreationTime}')
        else:
            self.logger.debug(f'ServerHandler: No Running Process(es) found for {processName}')

        # Find PIDs of all the running instances of process that contains 'influxdb' in it's name
        procObjList = [procObj for procObj in psutil.process_iter() if 'influxdb' in procObj.name().lower()]
        for elem in procObjList:
            print(elem)

    def getPID(self, proc_pattern):
        pid = None
        # TODO: does not work - replace with other code
        pid = subprocess.run(["pidof", "-s", proc_pattern], stdout=subprocess.PIPE).stdout
        #pid = check_output(["pidof","-s",proc_pattern])
        return pid

    def checkRabbitMQServerRunning(self):
        processNames = ["rabbitmq-server", "beam.smp"]
        if self.checkIfProcessRunning(processNames):
            self.logger.info("ServerHandler: the rabbitmq-server is already running!")
        else:
            self.logger.info("ServerHandler: starting rabbitmq-server...")
            # Start up rabbitmq-server (assumes it is currently down)
            cmd = "rabbitmq-server start"
            subprocess.run(cmd, capture_output=False, shell=True)

    def startInfluxDB(self):
        processName = "influxd"
        if self.checkIfProcessRunning(processName):
            self.logger.info("ServerHandler: the InfluxDB database is already running!")
        else:
            self.logger.info("ServerHandler: starting InfluxDB...")
            # TODO: add code to startup InfluxDB
        # self.getProcessInfo(processName)

# TODO: add functions to start processes required for the healthcare robothon


if __name__ == "__main__":
    serverHandler = ServerHandler()
