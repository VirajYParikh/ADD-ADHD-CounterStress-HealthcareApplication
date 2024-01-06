# metadata constituts 2 parts:
# 1. taxanomy for metaML
# 2. user information
import MySQLdb
import os
import json

# define a function to load .env file
def load_env_file(env_path):
    """
    Reads a .env file and returns the variables as a dictionary.
    """
    env_vars = {}
    with open(env_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

# Path to your .env file
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # root directory
DB_ENV_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'AppEasePlatform/backendapi/.env') 


def prepare_metadata(patient_id):
    env_vars = load_env_file(DB_ENV_FILE_PATH)

    # Retrieve environment variables
    hostname = env_vars.get('DB_HOST')
    port = int(env_vars.get('DB_PORT'))
    database = env_vars.get('DB_NAME')
    username = env_vars.get('DB_USER')
    password = env_vars.get('DB_PASSWORD')

    # connect to mySQL db
    try:
        # Establishing a connection to the database
        db = MySQLdb.connect(host=hostname, port=port, db=database, user=username, passwd=password)
        cursor = db.cursor()
        query = "SELECT * FROM AppEaseDataCollection WHERE personRandomDigit = %s"
        patient_id = patient_id
        cursor.execute(query, (patient_id,))
        data = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        patient_info = [{column_names[i]: value for i, value in enumerate(row)} for row in data]

    except MySQLdb.Error as e:
        print(f"Error connecting to MySQL Database: {e}")

    finally:
        # Closing the connection
        if db:
            db.close()

    metadata = {}
    # define MetaML taxonomy
    metadata["business_taxonomy"] = {
        # MetaML: industry domain
        "domain": "healthcare",
        # MetaML: business application
        "subdomain": "psychiatry",
        "application": "asd/adhd stress detection"
    }
    if patient_info:
        metadata['business_taxonomy']['context'] = patient_info[0]
    
    metadata['technical_taxonomy'] = {}

    metadata = json.dumps(metadata)
    
    return metadata


# print(prepare_metadata(1))
    
    