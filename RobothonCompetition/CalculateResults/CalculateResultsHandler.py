import json
import re
import warnings
import pandas as pd
import logging
import datetime
import argparse
from DBUtil.MySQLDBConn import MySQLDBConn
from DBUtil.InfluxDBConn import InfluxDBConn
from influxdb_client.client.flux_table import FluxStructureEncoder

warnings.filterwarnings("ignore")

DEBUG = True

# TODO: integrate code to calculate and store results (see result_db evaluate.py, __main__.py) - check if these bots write to the influxdb as well?

class CalculateResultsHandler:
    LOG_FILE_PATH = "../logs/robothon_healthcare.log"
    LOG_LEVEL = logging.DEBUG
    logger = None
    banner = '*'*20

    # MySQL DB Connection
    mysqlconn = None
    db_cursor = None

    # Influx DB Connection
    influxdbconn = None
    influxdb_cursor = None

    event_id = 0

    def __init__(self, event_id):
        # Configure logging
        self.configureLogging()

        if DEBUG:
            self.logger.info(
                "CalculateResultsHandler: Calculate Results Handler")

        self.event_id = event_id

        # Connect to MySQLDB
        self.mysqlconn = MySQLDBConn()
        self.db_cursor = self.mysqlconn.openDB()
        self.mysqlconn.selectDB(self.db_cursor)

        # Connect to InfluxDB
        self.influxdbconn = InfluxDBConn()
        #self.influxdb_cursor = self.influxdbconn.openInfluxDBBotBucket()

    def configureLogging(self):
        self.logger = logging.getLogger(self.LOG_FILE_PATH)
        self.logger.setLevel(self.LOG_LEVEL)
        fh = logging.FileHandler(self.LOG_FILE_PATH)
        fh.setLevel(self.LOG_LEVEL)
        ch = logging.StreamHandler()
        ch.setLevel(self.LOG_LEVEL)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def evaluate_det_model(classifier):    
        begin_time = datetime.datetime.now()
        mybotdata = bot_data.BotData(mode=2)
        
        result = mybotdata.fetchdataframe(1)
        dataset=result.iloc[:,2:]
        dataset['hour']=dataset._time.dt.hour
        dataset['mins']=dataset._time.dt.minute
        X_test = dataset[['calories','distance','heart_rate','steps','hour','mins']].values
        y_test = dataset[['stress']].values
        print("Test dataset shape:",X_test.shape,y_test.shape)
        
        # Feature Scaling
        sc = StandardScaler()
        X_test = sc.fit_transform(X_test)
        
        y_pred = classifier.predict(X_test)
        y_pred = (y_pred > 0.5)
        accuracy =  accuracy_score(y_test, y_pred)*100
        run_time = datetime.datetime.now() - begin_time
        print("DET RT",run_time, type(run_time))
        
        return run_time,accuracy    #time, accuracy
        
        
    def evaluate_act_model(classifier):    
        begin_time = datetime.datetime.now()
        mybotdata = bot_data.BotData(mode=2)
        
        result = mybotdata.fetchdataframe(1)
        dataset=result.iloc[:,2:]
        dataset['hour']=dataset._time.dt.hour
        dataset['mins']=dataset._time.dt.minute
        dataset['next_stress'] = dataset['stress'].shift(-1)
        dataset = dataset.loc[(dataset['stress']==1) & (dataset['next_stress']==0)]
        dataset = dataset.dropna()
            
        X_test = dataset[['calories','distance','heart_rate','steps','hour','mins']].values
        y_test = dataset[['activity']].values
        print("Test dataset shape:",X_test.shape,y_test.shape)
        pd.set_option("display.max_rows", None, "display.max_columns", None)
            
        # Feature Scaling
        sc = StandardScaler()
        X_test = sc.fit_transform(X_test)
        
        y_pred = classifier.predict(X_test)
        y_pred_class = np.argmax(y_pred,axis=1)
        print("Y shape",y_pred.shape, y_pred_class ,y_test.shape)
        print("Y pred:",y_pred[:5,:])
        print("Y test:",y_test[:5,:])
        print("Y pred class:",y_pred_class[:5])
        accuracy =  accuracy_score(y_test, y_pred_class)*100
        run_time = datetime.datetime.now() - begin_time
        print("ACT RT",run_time, type(run_time))
        return run_time,accuracy    #time, accuracy

    def fetchBotResults(self):
        #num_recs = '500'
        num_recs = '100'
        with self.influxdbconn.openInfluxDBBotBucket() as _client:
            query = """
                    from(bucket: "%s")
                        |> range(start: -10m)
                        |> filter(fn: (r) => r._measurement == "botresults" and (r._field == "AgentID" or r._field == "ExecAlgo" or r._field == "Symb" or r._field == "Action" or r._field == "ExecTargetQty" or r._field == "ExecSlices" or r._field == "ExecTime(secs)" or r._field == "ExecActualQty" or r._field == "TransactionCost" or r._field == "Penalty" or r._field == "BenchmarkPrice" or r._field == "BenchmarkVWAP"))
                        |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
                        |> drop(columns: ["_start","_stop", "_measurement"])
                        |> group()
                        |> sort(columns: ["_time"], desc: true)
                        |> limit(n: %s)
            """ % (self.influxdbconn.getBucket(), num_recs)
            tables = _client.query_api().query(query, org=self.influxdbconn.getOrg())
            output = json.dumps(tables, cls=FluxStructureEncoder, indent=2)
            json_records = json.loads(output)
            #records_only = json_records[0]['records'][0]
            if not json_records or len(json_records) == 0:
                self.logger.info("No records found in botresults table")
                return []
            records_only = json_records[0]['records']

            if DEBUG:
                self.logger.info(f"records_only: {records_only}")

            bot_results = []
            for rec in records_only:
                current_AgentID = rec['values']['AgentID']
                formatted_AgentID = current_AgentID.rsplit(
                    "--", 2)[0] if "--" in current_AgentID else current_AgentID

                if DEBUG:
                    self.logger.info(
                        "#################################################################################")
                    self.logger.info(f"formatted_AgentID: {formatted_AgentID}")

                result = {'AgentID': current_AgentID,
                          'ExecAlgo': rec['values']['ExecAlgo'],
                          'Symb': rec['values']['Symb'],
                          'Action': rec['values']['Action'],
                          'ExecTargetQty': rec['values']['ExecTargetQty'],
                          'ExecSlices': rec['values']['ExecSlices'],
                          'ExecTime(secs)': rec['values']['ExecTime(secs)'],
                          'ExecActualQty': rec['values']['ExecActualQty'],
                          'TransactionCost': rec['values']['TransactionCost'],
                          'Penalty': rec['values']['Penalty'],
                          'BenchmarkPrice': rec['values']['BenchmarkPrice'],
                          'BenchmarkVWAP': rec['values']['BenchmarkVWAP'],
                          'PublishedDateTime': rec['values']['_time']}
                bot_results.append(result)

            if DEBUG:
                self.logger.info(
                    "--------------------------------------------------------------------")
                self.logger.info(f"bot_results:\n\n{bot_results}")
                self.logger.info(
                    "--------------------------------------------------------------------")
                for br in bot_results:
                    print(f'-- Execution Bot Result -- {br}')
                self.logger.info(
                    "--------------------------------------------------------------------")

            return bot_results

    def storeBotResults(self):
        bot_results = self.fetchBotResults()
        if not bot_results:
            self.logger.info("No bot results to store")
            return
        df_bot_results = pd.DataFrame(bot_results)

        if DEBUG:
            self.logger.info(
                "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            self.logger.info(
                "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            self.logger.info(df_bot_results)
            self.logger.info(
                "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            self.logger.info(
                "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        col = df_bot_results.columns.values.tolist()
        col.append('event_id')
        insert_results = """INSERT INTO GlobalMarkets_competitionresult
        (`agent_id`, `symbol`, `exec_algorithm`, `action`, `exec_target_qty`, `exec_actual_qty`, `exec_slices`, `exec_time_in_secs`, `transaction_cost`, `penalty`, `benchmark_price`, `benchmark_vwap`, `publish_date`, `competition_event_id_id`)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        for i in range(len(df_bot_results)):
            self.db_cursor.execute(
                insert_results,
                (df_bot_results['AgentID'][i], df_bot_results['Symb'][i],
                 df_bot_results['ExecAlgo'][i], df_bot_results['Action'][i],
                 df_bot_results['ExecTargetQty'][i],
                 df_bot_results['ExecActualQty'][i],
                 df_bot_results['ExecSlices'][i],
                 df_bot_results['ExecTime(secs)'][i],
                 df_bot_results['TransactionCost'][i],
                 df_bot_results['Penalty'][i],
                 df_bot_results['BenchmarkPrice'][i],
                 df_bot_results['BenchmarkVWAP'][i],
                 str(datetime.datetime.now()), str(self.event_id)))

        if DEBUG:
            self.logger.info(
                "************************************** Web DB Storage **************************************")
            self.db_cursor.execute(
                """SELECT * FROM GlobalMarkets_competitionresult WHERE competition_event_id_id=%s;""" % (self.event_id))
            self.logger.info(self.db_cursor.fetchall())
            self.logger.info(
                "************************************** Close all database connections **************************************")

        self.mysqlconn.closeDB()

    def calculateBotsPerformanceResults(self):
        if DEBUG:
            self.logger.info(
                "************************************** Calculating Competition Results / Bots Performance **************************************")

        bot_results = self.fetchBotResults()
        if not bot_results:
            self.logger.info("No bot results found in the influxdb to calculate performance")
            return
        df_bot_results = pd.DataFrame(bot_results)

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_bot_results (DataFrame)(-- 0 --):\n\n{df_bot_results}")
            self.logger.info(
                "--------------------------------------------------------------------")

        #df_bot_results['AgentID_cleaned'] = df_bot_results['AgentID'].map(lambda x: (re.findall(r"(.+?)--", x.decode('utf-8')))[0])
        df_bot_results['AgentID_cleaned'] = df_bot_results['AgentID'].map(
            lambda x: (re.findall(r"(.+?)--", x))[0])

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_bot_results (DataFrame)(-- 1 --):\n\n{df_bot_results}")
            self.logger.info(
                "--------------------------------------------------------------------")

        df_bot_results['agent_id'] = df_bot_results['AgentID_cleaned'].map(
            lambda x: x.split('_eventID_')[0])

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_bot_results (DataFrame)(-- 2 --):\n\n{df_bot_results}")
            self.logger.info(
                "--------------------------------------------------------------------")

        # df_bot_results['event_id'] = df_bot_results['AgentID_cleaned'].map(lambda x: x.split('_eventID_')[1]) # (ORIG - perhaps event_id was appended in KDB version??)
        #df_bot_results['event_id'] = df_bot_results['AgentID_cleaned'].map(lambda x: x.split('_eventID_')[0])
        df_bot_results['event_id'] = df_bot_results['AgentID_cleaned'].map(
            lambda x: self.event_id)

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_bot_results (DataFrame)(-- 3 --):\n\n{df_bot_results}")
            self.logger.info(
                "--------------------------------------------------------------------")

        df_bot_results.drop(['AgentID', 'AgentID_cleaned'],
                            axis=1, inplace=True)

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_bot_results (DataFrame)(-- 4 --):\n\n{df_bot_results}")
            self.logger.info(
                "--------------------------------------------------------------------")

        if DEBUG:
            self.logger.info(
                "************************************** Evaluation result **************************************")

        df_event_bot_results = df_bot_results[df_bot_results['event_id'] == self.event_id].reset_index(
            drop=True)

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_event_bot_results (DataFrame)(-- 5 --):\n\n{df_event_bot_results}")
            self.logger.info(
                f"SIZE OF df_event_bot_results: {df_event_bot_results.size}")
            self.logger.info(
                "--------------------------------------------------------------------")

        df_eval_result = self.evaluateBotsResults(
            df_bot_results[df_bot_results['event_id'] == self.event_id].reset_index(drop=True))  # ORIG
        #df_eval_result = self.evaluateBotsResults(df_event_bot_results)

        if DEBUG:
            self.logger.info(
                "--------------------------------------------------------------------")
            self.logger.info(
                f"df_eval_result (DataFrame)(-- 6 --):\n\n{df_eval_result}")
            self.logger.info(
                f"df_eval_result columns: {df_eval_result.columns}")
            self.logger.info(
                "--------------------------------------------------------------------")

        if DEBUG:
            self.logger.info(
                "************************************** Start Web database and pass competition result **************************************")

        self.mysqlconn.selectDB(self.db_cursor)

        if DEBUG:
            self.logger.info(
                "************************************** Store Competition Results in Web database **************************************")

        insert_results = """INSERT INTO GlobalMarkets_competitionresult
        (`agent_id`, `symbol`, `exec_algorithm`, `action`, `exec_target_qty`, `exec_actual_qty`, `exec_slices`, `exec_time_in_secs`, `transaction_cost`, `penalty`, `benchmark_price`, `benchmark_vwap`, `score`, `rank`, `publish_date`, `competition_event_id_id`)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        for i in range(len(df_eval_result)):
            insert_result_query = insert_results % (df_eval_result['agent_id'][i], df_eval_result['Symb'][i],
                                                    df_eval_result['ExecAlgo'][i], df_eval_result['Action'][i],
                                                    df_eval_result['ExecTargetQty'][i],
                                                    df_eval_result['ExecActualQty'][i],
                                                    df_eval_result['ExecSlices'][i],
                                                    df_eval_result['ExecTime(secs)'][i],
                                                    df_eval_result['TransactionCost'][i],
                                                    df_eval_result['Penalty'][i],
                                                    df_eval_result['BenchmarkPrice'][i],
                                                    df_eval_result['BenchmarkVWAP'][i],
                                                    df_eval_result['score'][i], df_eval_result['rank'][i],
                                                    df_eval_result['PublishedDateTime'][i], df_eval_result['event_id'][i])
            self.logger.info(f"Insert result query: {insert_result_query}")
            self.db_cursor.execute(
                insert_results,
                (df_eval_result['agent_id'][i], df_eval_result['Symb'][i],
                 df_eval_result['ExecAlgo'][i], df_eval_result['Action'][i],
                 df_eval_result['ExecTargetQty'][i],
                 df_eval_result['ExecActualQty'][i],
                 df_eval_result['ExecSlices'][i],
                 df_eval_result['ExecTime(secs)'][i],
                 df_eval_result['TransactionCost'][i],
                 df_eval_result['Penalty'][i],
                 df_eval_result['BenchmarkPrice'][i],
                 df_eval_result['BenchmarkVWAP'][i],
                 df_eval_result['score'][i], df_eval_result['rank'][i],
                 df_eval_result['PublishedDateTime'][i], df_eval_result['event_id'][i]))

        if DEBUG:
            self.logger.info(
                "************************************** Web DB Storage **************************************")
            self.db_cursor.execute(
                """SELECT * FROM GlobalMarkets_competitionresult WHERE competition_event_id_id=%s;""" % (self.event_id))
            self.logger.info(self.db_cursor.fetchall())
            self.logger.info(
                "************************************** Close all database connections **************************************")

        self.mysqlconn.closeDB()

    def getBotsRank(self, data, feature, ascending):
        """
        Description: getBotsRank returns the rank (absolute rank and percentile), for the rank ratio, the lowest, and the highest
        Args:
            data: cleaned trading bots performance result
            feature: required rank column
            ascending: control the rank logic, for some features, e.g., CompletionQtyRatio, the larger, the better, for others, e.g., TransactionCostRatio, the lower, the better
        Returns:
            Ranked results table
        """
        data['%sRankAbs' % feature] = data[feature].rank(
            method='min', ascending=ascending)
        data['%sRank' % feature] = data['%sRankAbs' % feature] / len(data)
        return data

    def evaluateBotsResults(self, data):
        data_val = data[(data['TransactionCost'] > -0.15) &
                        (data['TransactionCost'] < 0.15)].reset_index(drop=True)
        transcost_results_count = data_val.size

        if DEBUG:
            self.logger.info(
                "************************************** Bots transactions performance with TransactionCost > -0.15 and < 0.15 **************************************")
            self.logger.info(data_val)
            self.logger.info(
                f"size of dataframe (TransactionCost > -0.15 and < 0.15): {transcost_results_count}")
            self.logger.info(
                "************************************** View Results **************************************")

        res_all = None
        if transcost_results_count == 0:
            self.logger.info(
                f"{self.banner} No bots returned with the Transaction Cost > -0.15 and < 0.15 {self.banner}")

            result = data[['TransactionCost', 'event_id', 'agent_id', 'ExecAlgo']].groupby(
                by=['event_id', 'agent_id', 'ExecAlgo']).count()
            res = result.reset_index().rename(
                columns={'TransactionCost': 'TransactionCost(count)'})
            res['TransactionCost(good_count)'] = 0
            res['GoodTransRatio'] = res['TransactionCost(good_count)'] / \
                res['TransactionCost(count)']
            res_all = res[['event_id', 'agent_id', 'ExecAlgo',
                           'TransactionCost(count)', 'GoodTransRatio']]
        else:
            # If there are bots returned with a Transaction Cost > -0.15 and < 0.15 then calculate the good_count
            good_count = data_val[['TransactionCost', 'event_id', 'agent_id', 'ExecAlgo']].groupby(
                by=['event_id', 'agent_id', 'ExecAlgo']).agg(['count', 'mean'])
            good_count_res = good_count.reset_index()
            good_count_size = good_count_res.size
            if DEBUG:
                self.logger.info(
                    f"size of dataframe (good_count_size): {good_count_size}")
                self.logger.info(good_count)
                self.logger.info(
                    "************************************** Snapshot of good records **************************************")
                self.logger.info(f"Dataframe (good_count): {good_count}")

            if good_count_size == 0:
                self.logger.info(
                    f"{self.banner} Cannot calculate aggregate mean from Transaction Cost - no bots returned with the Transaction Cost > -0.15 and < 0.15 {self.banner}")
            else:
                result = data[['TransactionCost', 'event_id', 'agent_id', 'ExecAlgo']].groupby(
                    by=['event_id', 'agent_id', 'ExecAlgo']).count()
                res = result.reset_index().rename(
                    columns={'TransactionCost': 'TransactionCost(count)'})
                res['TransactionCost(good_count)'] = good_count_res['TransactionCost']['count']
                res['GoodTransRatio'] = res['TransactionCost(good_count)'] / \
                    res['TransactionCost(count)']
                res_all = res[['event_id', 'agent_id', 'ExecAlgo',
                               'TransactionCost(count)', 'GoodTransRatio']]

        if DEBUG:
            self.logger.info(
                "************************************** Final Results records **************************************")
            self.logger.info(res_all)
            self.logger.info(
                "************************************** Final Results records **************************************")

        col = data.columns.values.tolist()
        res_all = self.getBotsRank(res_all, 'GoodTransRatio', True)
        res_all['score'] = 0.5 * res_all['GoodTransRatioRank']
        res_all['rank'] = res_all['score'].rank(method='min', ascending=True)
        col.append('score')
        col.append('rank')
        data = pd.merge(data, res_all[['event_id', 'agent_id', 'ExecAlgo', 'score', 'rank']], on=[
                        'event_id', 'agent_id', 'ExecAlgo'])

        if DEBUG:
            self.logger.info(
                "************************************** Final data **************************************")
            self.logger.info(data)
            self.logger.info(
                "************************************** Final data **************************************")

        return data[col]


if __name__ == "__main__":
    myargparser = argparse.ArgumentParser()
    myargparser.add_argument('--event_id',
                             type=str,
                             const='text',
                             nargs='?',
                             default='text')
    args = myargparser.parse_args()
    crh = CalculateResultsHandler()
