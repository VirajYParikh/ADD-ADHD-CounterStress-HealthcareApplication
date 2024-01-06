from RobothonCompetition.DBUtil.InfluxDBConn import InfluxDBConn
import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from statsmodels.tsa.stattools import acf
import pandas as pd
from seglearn.base import TS_Data
from seglearn.pipe import Pype
from seglearn.transform import FeatureRep, Segment

"""
This code calculates the high level statistics using package seglearn
"""

            
def extract_seglearn_feature(df, window_size=6, segment=False):
        time_series_data = df[['activity', 'calories', 'distance', 'heart_rate', 'steps', 'stress']].values
        n_series = 1  # Update this based on your data
        n_timestamps = len(df)
        n_features = time_series_data.shape[1]
        if segment:
                time_series_data = time_series_data.reshape((n_series, n_timestamps, n_features))
                print(time_series_data.shape)
                segmenter = Segment(width=window_size, step=1)
                segmenter.fit(time_series_data)
                X_seg = segmenter.transform(time_series_data)[0]
                print(X_seg.shape)
        else:
                # pass in data as a whole
                X_seg = time_series_data.reshape((1, n_timestamps, n_features))
                print(X_seg.shape)
        # extract feature
        # default: 6 base feature https://dmbee.github.io/seglearn/_modules/seglearn/feature_functions.html#base_features
        # can set to all_features() 
        feature_rep = FeatureRep()
        X_features = feature_rep.fit_transform(X_seg)
        # print(X_features.shape)
        # print(X_features)
        return X_features



# from(bucket: "ArchSimHealthData")
        # |> range(start:2001-01-01T05:00:00.000Z)
        # |> filter(fn: (r) => r._measurement == "health_data")
        # |> filter(fn: (r) => r.user_id == "1")
        # |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        # |> limit(n:100)
        # |> keep(columns: ["heart_rate", "steps","distance","calories","stress","activity","_time"])


## generate statistics on the time series data
# auto correlation

def compute_features(df):
        # data processing

        # time domain features
        # the lag is defaulted to 6, 30, 60

        # todo: check the length of df to avoid index out of range
        autocorr_stress = acf(df['stress'], nlags=60)
        lags = [6, 30, 60]
        autocorr_lag = [autocorr_stress[i] for i in lags]

        # peaks
        num_peaks = (np.diff(np.sign(np.diff(df['stress']))) < 0).sum()

        # return feature vector
        feature_vector = np.array([num_peaks]+autocorr_lag)
        
        return feature_vector



if '__name__' == '__name__':
        # grab data from influxDB
        query = 'from(bucket: "ArchSimHealth")\
            |> range(start:2001-01-01T05:00:00.000Z) \
            |> filter(fn: (r) => r._measurement == "health_data")\
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") \
            |> keep(columns: ["heart_rate", "steps","distance","calories","stress","activity","_time", "stress_level"])' 
        instance = InfluxDBConn()
        validation_result = instance.openInfluxDBBotBucket().query_api().query_data_frame(query)
        print(validation_result.describe())
        print(extract_seglearn_feature(validation_result, segment=False))

