from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxStructureEncoder
from configparser import ConfigParser
import os

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # ../RobothonCompetition/ directory
DB_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/db_config.ini') 

class InfluxDBConn:
    """
    Description: InfluxDBConn - establish connections to the InfluxDB database

    Args:
        host: hostname
        port: InfluxDB port
        org: organization
        token: authentication token

    Functions:
         openInfluxDB: Open a connection to the InfluxDB database
         closeInfluxDB: Close the InfluxDB connection
    """
    
    host = None
    port = None
    org = None
    token = None
    client = None
    url = None
    configparse = None
    
    def __init__(self, token=None):
        self.readConfigFile(token)
        self.openInfluxDB()

    def readConfigFile(self, token):
        self.configparse = ConfigParser()
        self.configparse.read(DB_CONFIG_FILE_PATH)
        #self.configparse.read('../config/db_config.ini')

        self.host = self.configparse.get('INFLUXDB', 'influxdb_host')
        self.port = self.configparse.get('INFLUXDB', 'influxdb_port')        
        self.org = self.configparse.get('INFLUXDB', 'influxdb_org')
        self.url = f'http://{self.host}:{self.port}'
        
        if token is None:
            self.token = self.configparse.get('INFLUXDB', 'influxdb_token')
        else:
            self.token = token

    def openInfluxDB(self):
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        return self.client

    def openInfluxDBBotBucket(self):
        self.token = self.configparse.get('BOTINFLUXDB', 'bot_influxdb_token')
        self.bucket = self.configparse.get('BOTINFLUXDB', 'bot_influxdb_bucket')     
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        return self.client

    def closeInfluxDB(self):
        self.client.close()
        
    def getOrg(self):
        return self.org
    
    def getBucket(self):
        return self.bucket