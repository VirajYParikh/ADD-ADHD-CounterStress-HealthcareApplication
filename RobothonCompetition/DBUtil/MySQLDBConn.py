import MySQLdb
from configparser import ConfigParser
import os

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # ../RobothonCompetition/ directory
DB_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/db_config.ini') 

class MySQLDBConn:
    """
    Description: MySQLConn - establish connections to the MySQLDB web database

    Args:
        host: hostname
        port: web database port
        username: web database username
        password: web database password

    Functions:
         OpenDB: Open a connection to the MySQL database
         CloseDB: Close the MySQL connection
    """

    host = None
    port = None
    username = None
    password = None
    database = None
    dbconn = None
    cursor = None

    def __init__(self):        
        self.readConfigFile()
        #self.openDB()

    def readConfigFile(self):
        configparse = ConfigParser()
        configparse.read(DB_CONFIG_FILE_PATH)
        #configparse.read('../config/db_config.ini')
        self.host = configparse.get('MYSQLDB', 'mysql_host')
        self.port = configparse.get('MYSQLDB', 'mysql_port')
        self.username = configparse.get('MYSQLDB', 'mysql_username')
        self.password = configparse.get('MYSQLDB', 'mysql_password')
        self.database = configparse.get('MYSQLDB', 'mysql_database')

    def openDB(self):
        self.dbconn = MySQLdb.connect(host=self.host, port=int(self.port), user=self.username, password=self.password)
        self.dbconn.autocommit(True)
        self.cursor = self.dbconn.cursor()
        return self.cursor

    def selectDB(self, db_cursor, databasename=None):
        if databasename is None:
            query = """USE %s""" % self.database
        else:
            query = """USE %s""" % databasename
        db_cursor.execute(query)

    def getConn(self):
        return self.dbconn

    def commitToDb(self):
        self.dbconn.commit()
    
    def closeDB(self):
        self.dbconn.close()


if __name__ == "__main__":
    print("MySQLDBConn - test database connection...")
    mysqlconn = MySQLDBConn()
    #test = mysqlconn.openDB()