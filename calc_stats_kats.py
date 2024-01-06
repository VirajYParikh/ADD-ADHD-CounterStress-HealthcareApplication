from RobothonCompetition.DBUtil.InfluxDBConn import InfluxDBConn
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from statsmodels.tsa.stattools import acf
import pandas as pd
# from seglearn.base import TS_Data
# from seglearn.pipe import Pype
# from seglearn.transform import FeatureRep, Segment
from kats.consts import TimeSeriesData
from kats.detectors.robust_stat_detection import RobustStatDetector
from kats.tsfeatures.tsfeatures import TsFeatures
import csv
# from kats.tsfeatures.tsfeatures import TsFeatures
# from kats.tsfeatures.custom_transformed_features import CTFSettings


"""
This code makes use of the Kats library and its features to compare two different time series
data
"""

def process_timseries_data(df):
       
        model = TsFeatures(bocp_detector=False)
        
        time_col = '_time'
        values_col = ['activity', 'calories', 'distance', 'heart_rate', 'steps', 'stress']


        # Dropping the useless columns from the timeseries data
        df = df.drop(["result"], axis=1)
        
        # Converting all the time series columns into numeric type for processing by kats
        object_columns = df.select_dtypes(include=['object']).columns
        df[object_columns] = df[object_columns].apply(pd.to_numeric, errors='coerce')  
        
        # preparing the final dataframe on which the other 
        result_df = pd.DataFrame(columns=['feature'])

        for value in values_col:
                df_temp = df[[time_col,value]]
                df_temp = df_temp.rename(columns={value:'value'})
                # df_temp = TimeSeriesData(df_temp,time_col_name="_time")
                # processing the features
                output_features = model.transform(df_temp)
                # output_features = output_features.add_prefix(f"{value}_")
                initial_df = pd.DataFrame(list(output_features.items()), columns=['feature', value])
                # appending on the existing dataframe
                result_df = pd.merge(result_df,initial_df, on="feature", how="outer")
                
                
        final_df = result_df.drop(['feature'], axis = 1)
        final_df.dropna(inplace=True)
        result = final_df.to_numpy()
        print(result_df)
        print("----------------------In 2dimensional array-------------------------", end=" ")
        print(result)
        return result



if '__name__' == '__name__':
        # grab data from influxDB
        query = 'from(bucket: "ArchSimHealth")\
            |> range(start:2001-01-01T05:00:00.000Z) \
            |> filter(fn: (r) => r._measurement == "health_data")\
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") \
            |> keep(columns: ["heart_rate", "steps","distance","calories","stress","activity","_time", "stress_level"])' 
        instance = InfluxDBConn()
        validation_result = instance.openInfluxDBBotBucket().query_api().query_data_frame(query)
        # Dropping the useless columns from the timeseries data
        # validation_result = validation_result.drop(["result"], axis=1)
        
        # # Converting all the time series columns into numeric type for processing by kats
        # object_columns = validation_result.select_dtypes(include=['object']).columns
        # validation_result[object_columns] = validation_result[object_columns].apply(pd.to_numeric, errors='coerce')  
        
        process_timseries_data(validation_result)

