from ManageServer.ServerHandler import ServerHandler
from time import sleep
import os
import logging



DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory

class RobothonHandler:
    logger = None
    serverHandler = None
    banner = '*'*20

    def __init__(self, *args, **kwargs):
        # kwargs2 = kwargs.copy()
        # print(kwargs2)

        # configure logging
        self.configureLogging()

        # instantiate ServerHandler
        self.serverHandler = ServerHandler()
        
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

    def startAllServerProcesses(self, *args, **kwargs):
        self.logger.info(f"{self.banner} RobothonHandler: starting all robothon server processes... {self.banner}")
        #from ManageServer.ServerHandler import ServerHandler
        #self.serverHandler = ServerHandler(logger=self.logger)
        #self.serverHandler = ServerHandler()
        self.serverHandler.startInfluxDB()
        sleep(20)

    def stopAllServerProcesses(self, *args, **kwargs):
        self.logger.info(f"{self.banner} RobothonHandler: stopping all robothon server processes... {self.banner}")

    def getProcessRunningPIDs(self, event_id: str, process: str):
        python_script_name = f'{process}.py'
        pids = []
        for proc in psutil.process_iter():
            try:
                # check if process name equals processName
                cmdline = ' '.join(proc.cmdline()).lower()
                if 'python' in cmdline and f'/{python_script_name}' in cmdline:
                    pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                self.logger.error(f"An error occurred: {e}")
                pass
        return pids
    
    def checkProcessesStatus(self, event_id: str):
        # TODO: update the process list for HealthCare
        processes = ['market_maker', 'rabbitmq_receiver', 'replayagent_influxdb']
        running_processes = []
        for process in processes:
            pids = self.getProcessRunningPIDs(event_id, process)
            if len(pids) > 0:
                running_processes.append(process)
        return len(running_processes) > 0, running_processes
    
    def requestSandboxEnv(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        robot_username = kwargs["robo_user"]
        mode = kwargs["mode"]  # 'test' or 'validation'
        from RunSandboxEnvironment.SandboxEnvHandler import SandboxEnvHandler
        teHandler = SandboxEnvHandler(event_id)
        if mode == 'validation':
            teHandler.validateSandboxTestEnv(robot_username)
        else:
            teHandler.requestSandboxEnvironment(robot_username)

    def runSandboxEnv(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        from RunSandboxEnvironment.SandboxEnvHandler import SandboxEnvHandler
        teHandler = SandboxEnvHandler(event_id)
        self.logger.info(f"{self.banner} RobothonHandler: running bots in sandbox test environment... {self.banner}")
        # teHandler.fetchParticipantDownloadInfo()
        teHandler.runSandboxTestEnv()

    def downloadBots(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        from DownloadBots.DownloadHandler import DownloadHandler
        downloadHandler = DownloadHandler(event_id)
        self.logger.info(f"{self.banner} RobothonHandler: downloading submitted bots... {self.banner}")
        downloadHandler.fetchParticipantDownloadInfo()

    def downloadMetaMLBots(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        num_bots = kwargs["num_bots"]
        from DownloadBots.DownloadHandler import DownloadHandler
        downloadHandler = DownloadHandler(event_id)
        self.logger.info(
            f"{self.banner} RobothonHandler: downloading metaml bots... {self.banner}")
        downloadHandler.downloadMetaMLBots(num_bots)

    def downloadOneBot(self, event_id, robot_username):
        from DownloadBots.DownloadHandler import DownloadHandler
        downloadHandler = DownloadHandler(event_id)
        downloadHandler.fetchParticipantDownloadInfo(robot_username=robot_username)

    #def validateBots(self, *args, **kwargs):
    def validateBots(self, event_id, robot_username):
        #event_id = kwargs["event_id"]
        from ValidateBots.ValidateHandler import ValidateHandler
        self.logger.info(f"{self.banner} RobothonHandler: validating submitted bots... {self.banner}")
        validateHandler = ValidateHandler(event_id)
        validateHandler.validateBots()

    def getQualifiedBots(self, event_id: str):
        from RunBots.RunBotsHandler import RunBotsHandler
        runbotHandler = RunBotsHandler(event_id)
        qualified_bots = runbotHandler.getQualifiedBots(event_id)
        return qualified_bots
    
    def generateBotBatchScripts(self, event_id: str):
        from RunBots.RunBotsHandler import RunBotsHandler
        runbotHandler = RunBotsHandler(event_id)
        qualified_bots = runbotHandler.getQualifiedBots(event_id)
        self.logger.info(f"Qualified bots: {qualified_bots}")
        runbotHandler.generateBotBatchScripts(qualified_bots=qualified_bots, competition_mode=1)

    def runBots(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        self.logger.info(f"{self.banner} RobothonHandler: running qualified bots in competition... {self.banner}")
        from RunBots.RunBotsHandler import RunBotsHandler
        runbotHandler = RunBotsHandler(event_id)
        runbotHandler.runCompetitionBots()

    def calculateResults(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        self.logger.info(f"{self.banner} RobothonHandler: calculating bots results... {self.banner}")
        from CalculateResults.CalculateResultsHandler import CalculateResultsHandler
        calcResultsHandler = CalculateResultsHandler(event_id)
        # calcResultsHandler.storeBotResults()
        calcResultsHandler.calculateBotsPerformanceResults()

    def deleteBots(self, *args, **kwargs):
        self.logger.info(f"{self.banner} RobothonHandler: deleting bots... {self.banner}")
        from DeleteBots.DeleteBotsHandler import DeleteBotsHandler
        deleteHandler = DeleteHandler(event_id)
        deleteHandler.deleteAllBotsDirectories()

    def endCompetition(self, *args, **kwargs):
        event_id = kwargs["event_id"]
        self.logger.info(
            f"{self.banner} RobothonHandler: ending competition... {self.banner}")
        from EndCompetition.EndCompetitionHandler import EndCompetitionHandler
        # regime_path = os.path.join(self.regime_data_path, self.regime_data_csv_filename)
        endCompetitionHandler = EndCompetitionHandler(event_id)
        endCompetitionHandler.end()

    def getRobotScriptRunningPIDs(self, robot_username: str) -> list:
        '''
            Check for any running processes that match processName
        '''
        python_script_name = f'{robot_username}.py'.lower()
        pids = []
        # iterate over running processes
        for proc in psutil.process_iter():
            try:
                # check if process name equals processName
                cmdline = ' '.join(proc.cmdline()).lower()
                if 'python' in cmdline and f'/{python_script_name}' in cmdline:
                    pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                self.logger.error(f"An error occurred: {e}")
                pass
        return pids
    
    def checkRobotScriptRunning(self, robot_username: str) -> bool:
        pids = self.getRobotScriptRunningPIDs(robot_username)
        return len(pids) > 0

    def runFullTest(self, *args, **kwargs):
        self.logger.info(f"{self.banner} RobothonHandler: running all phases... {self.banner}")
        self.startAllServerProcesses()
        self.downloadBots()
        self.validateBots()
        self.runBots()
        self.calculateResults()
        sleep(40)
        self.deleteBots()
        self.stopAllServerProcesses()

if __name__ == "__main__":
    handler = RobothonHandler(event_id=1)
