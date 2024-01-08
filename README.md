# ADD/ADHD CounterStress Healthcare Application:

#### Author: Viraj Parikh & Siqing Tao
Credit to the previous authors: Hashir Bin Khalid and Martin Zhao

# Healthcare Robothon Competiton Platform
### Team:
- Viraj Parikh
- Siqing Tao
- Chengxi Li

Please Note: Due to confidentiality clauses we are not able to publish the entire working code on GitHub. However, this ReadMe.md will give you a gist of the product we are working on and the functionalities we have worked on.

## Introduction: 

The advances in technology in the field of wearables (IoT and Sensors) and AI/ML have resulted in the opening of a wide array of thought processes and ideas. We can apply these technologies in a variety of interesting ways like AR/VR glasses, Biometric recognition in Apple Watches, and so on. 


Team Meyers is currently working on an interesting application aimed at helping children diagnosed with ADD and ADHD. These children often go through abnormally high stress and heart rate occurrences because of the extraordinary way they perceive the world around them. This can be quite dangerous and may lead them to harm themselves or anything in their surroundings due to no fault of their own. 


Using the power of the Apple watch wearable that can sense and extract data like heart rates, stress levels, and other important information, one can leverage the detection ability of powerful ML models to tackle this effect smoothly and harmlessly. 


This is essentially the broader idea of the project where we harness the power of ML bots, train them on the time series data extracted from the user’s watch, and deploy a bot back onto the watch which would in turn given its knowledge, generate the best and appropriate response for example Audio message, Image, Emoji, Game etc. to help alleviate the user’s stress. 


Another very important aspect of the project is the competition platform. Developers essentially compete on this platform, and generate ML bots trained on the time series data available. The top-ranked bots are stored away for use while monitoring and deploying counter-stress measures in real-time. 


## MetaML and Meyers: 

MetaML is a storage system for past winning bots in competitions, which can stretch across multiple domains like healthcare, finance, blockchain, etc. And when we launch a new competition and collect new bots, we want to be able to pull past winning bots into the competition, so that we are constantly borrowing past knowledge.

###### How can we tell what past bots are suitable for the current competition? - We use Fingerprints! 

The current solution is to generate a fingerprint-based on data used for the current competition, which the MetaML team could use to search past bots having similar fingerprints. Hence, a fingerprint, on a broader level, is a feature that helps provide pieces of identification for the bots stored in the MetaML platform. 


Note: There is a separation of jobs between MetaML and Competition Platform: The competition platform is responsible for generating the fingerprint and MetaML is responsible for running a comparison check on the fingerprints to retrieve the most accurate bots about the time series data in question. 


## File Structure and Use

| Folder/File                                              | Description                                                                                                                               |
|----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| bots_competition/main                                    | Runs the competition phase. Runs each bot in stress detection phase first and then in action prediction phase                             |
| Core/core.py                                             | Integrate all function (Fall 2022 Update: add functions to setup p2p connection with MetaML platform and add MetaML bots into competition |
| Core/delete_bots.py                                      | Deletes downloaded and validated bots as well as result. Useful for testing                                                               |
| download_files/download_files.py                         | Downloads code for each participant                                                                                                       | 
| download_files/download_url.py                           | Helper code for dowload_files                                                                                                             | 
| download_files/download_url.py                           | Helper code for dowload_files                                                                                                             | 
| bots folder                                              | This folder is used for downloading, validation and storing results of bots. The script uses the folder itself.                           
| Bots_archive folder                                      | Some rough scripts to play with bots. Not part of platform                                                                                | 
| Data_Simulator/health_data_simulator.py                  | Generates data based on variables defined in the script and then stores it in a csv named simulateddata.csv                               |
| Data_Simulator/WriteOrdersData.py                        | Writes data from simulateddata.csv to the InfluxDB                                                                                        |
| Data_Simulator/BatchWriteOrdersData.py                   | Writes data from csvs in health_data folder to InfluxDB (Obsolete. Needs update)                                                          |
| result_db/main                                           | The main evaluation phase script                                                                                                          | 
| result_db/evaluate                                       | Calculates running time and accuracy for a bot                                                                                            | 
| result_db/connect_web_database and result_db/MySQLDBConn | Not related to results. Used by all different scripts to connect to MySQL                                                                 | 
| robothon_scheduler/Scheduler                             | Competition Scheduler which checks MySQL database and runs core platform script accordingly                                               |
| Validation/validation.py                                 | Validates both modes of each bot to check that it generates some result                                                                   |
| p2p folder                                               | Preparation environment for the p2p connection. (Credit to the MetaML team)                                                               |
| p2p/services/AddMetaML.py                                | Send bots request and receive and parse the response message. Store MetaML bots ready for competiton Stage.                               |
| TestEnv folder                                           | A sandbox environment testing Participants' bots. There is a Readme in this folder to further explain the structure.                      |
| config folder                                            | Add system config.                                                                                                                        |
### Description

#### To run the competition

- **robtohon_scheduler/Scheduler.py**: Just run the script and start a competition from the front end. The platform is designed for Linux.

#### Core

- **core.py**: integrate each function, and use python core.py -mode [mode] to start
  - help(1) - terminal help book
  - delete_bot(2) - Delete downloaded and validated bots (for testing) 
  - bot(3) - start competition
  - kill(4) - (N/A)
  - exit(5) - exit for terminal 
  - test(6) - N/A 
  - validation(7) - validation for bots
  - result_db(8) - calculate the results and store result in database
  - download_files(9) - download files from git links
  - 'connect_metaml(10) - setup p2p connect with metaml'
  - 'get_bots_from_metaml(11) - retrieve top K validated bots from MetaML platform'

### Robothon_Package_Code_Setup

Step 1: Activate virtual environment

```
conda activate py37_default
```

Step 2: Setup up p2p connection with MetaML in a different Terminal
```
python -core.py -mode 10 
```

Step 3: Automatically start competitions according to agenda

```
python ./Scheduler/scheduler.py
```

After running the scheduler.py, 
you can check that MetaML bots got successfully downloaded into designated folder as following screenshots
![Alt text](Image/load.png?raw=true "Title")

Store inside the folder

![Alt text](Image/validate_folder.jpg?raw=true "Title")

you can review the competition rank of bots from both participants and MetaML platform as following
![Alt text](Image/rank.png?raw=true "Title")
