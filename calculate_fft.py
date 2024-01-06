from RobothonCompetition.DBUtil.InfluxDBConn import InfluxDBConn
# from Data_Simulator.health_data_simulator import generate_healthdata
import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from statsmodels.tsa.stattools import acf
import json
import os
import glob
from typing import List, Dict, Tuple
from tqdm import tqdm
import pickle
import time
from scipy import fft, signal
import logging

WINDOW_SIZE = 300
RESAMPLING_RATE = 0.1

logger = logging.getLogger('Fingerprint')

"""
Caculate fingerprint of given time series data
returns panda DataFrame with following values:
hash: hash value of fingerprint
timestamp: start time of the window at which the hash was generated
frequency: frequency info of the match
bot_ids: list of bot ids matched

optional:
time_col: time data column, default use 0th column
value_col: value data column, default use 1st column
window_size: size of the window (in seconds) to use when creating the fingerprint
resampling_rate: resampling rate for fingerprint
group_by: default not grouped 

"""
# function to perform fft transform 
def create_constellation(dataframe, vol_column, Fs=0.1, window_length=300):
    time_series_data = dataframe[vol_column].values
    # Parameters
    window_length_seconds = window_length
    window_length_samples = int(window_length_seconds * Fs)
    window_length_samples += window_length_samples % 2
    num_peaks = 15

    # Pad the song to divide evenly into windows
    amount_to_pad = window_length_samples - time_series_data.size % window_length_samples

    song_input = np.pad(time_series_data, (0, amount_to_pad))

    # Perform a short time fourier transform
    frequencies, times, stft = signal.stft(
        song_input, Fs, nperseg=window_length_samples, nfft=window_length_samples, return_onesided=True
    )

    constellation_map = []

    for time_idx, window in enumerate(stft.T):
        # Spectrum is by default complex. 
        # We want real values only
        spectrum = abs(window)
        # Find peaks - these correspond to interesting features
        # Note the distance - want an even spread across the spectrum
        peaks, props = signal.find_peaks(spectrum, prominence=0, distance=10)

        # Only want the most prominent peaks
        # With a maximum of 15 per time slice
        n_peaks = min(num_peaks, len(peaks))
        # Get the n_peaks largest peaks from the prominences
        # This is an argpartition
        # Useful explanation: https://kanoki.org/2020/01/14/find-k-smallest-and-largest-values-and-its-indices-in-a-numpy-array/
        largest_peaks = np.argpartition(props["prominences"], -n_peaks)[-n_peaks:]
        for peak in peaks[largest_peaks]:
            frequency = frequencies[peak]
            constellation_map.append([time_idx, frequency])

    return constellation_map

def create_stress_hashes(constellation_map, session_id=None):
    hashes = []
    # Define the range and bins for stress levels
    frequency_bits = 5  # Number of bits for frequency binning
    upper_frequency = 100  # Assuming 500 Hz is the upper limit of frequency in your data
    n_sampling_window = 6 # Number of sampling window to perform the combinatorics

    # Iterate through the constellation map
    for idx, (time_idx, frequency) in enumerate(constellation_map):
        # Iterate over the next 'n' points to create combinatorial pairs 
        for next_time_idx, next_frequency in constellation_map[idx: idx + n_sampling_window]:
            time_diff = next_time_idx - time_idx
            # Filter out pairs with inappropriate time differences
            if time_diff <= 0 or time_diff > 10:
                continue

            # Binning frequencies
            freq_binned = int(frequency / upper_frequency * (2 ** frequency_bits))
            next_freq_binned = int(next_frequency / upper_frequency * (2 ** frequency_bits))

            # Generate a hash
            # 20-bit hash: 10 bits for frequency and 10 bits for time diff
            hash = freq_binned | (next_freq_binned << frequency_bits) | (time_diff << 2*frequency_bits)
            hashes.append([hash, time_idx])

    return hashes
 

# function to parse the input before feeding into create_constellation for fft
# directly copied form MetaML
def calculate_fingerprint(df: pd.DataFrame, **kwargs):
        # parse the args
        logger.debug(f"calculate fft fingerprint with args: {kwargs}")

        # set column to use as timestamp
        time_col_name = kwargs.get('time_col')
        logger.debug(df.dtypes)
        df = df.drop_duplicates(subset=time_col_name).set_index(time_col_name)
        print(df)

        # set which column to use as the values
        value_col_name = kwargs.get('value_col')
        value_col = df.columns.get_loc(value_col_name) if value_col_name else 1

        # set window size for the fft fingerprint
        window_size = kwargs.get('window_size', WINDOW_SIZE)

        # set resampling rate for the fingerprint
        resampling_rate = kwargs.get('resampling_rate', RESAMPLING_RATE)

        # set column to group by 
        group_by = kwargs.get('group_by')

        logger.debug(f"parsed kwargs")

        it = iter(df.groupby(group_by))

        database = pd.DataFrame(columns=['hashes', 'time', 'seq_id', 'bot_id', 'competition_id', 'github_url'])

        for sym_code, sym_df in it:
                logger.debug(f"Iterating: {sym_code}, {len(sym_df)}, {sym_df.dtypes}")
                try:
                        sym_df = sym_df.resample('500U')
                except Exception as e:
                        logger.debug(f"something wrong: {e}")

                sym_df = sym_df.fillna('nearest')

                #read the sequence, create the constellation and hashes
                logger.debug("creating constellation")
                constellation_map = create_constellation(dataframe=sym_df, col_name=value_col)
                logger.debug("creating hashes")
                # hashes = create_hashes(constellation_map=constellation_map, bot_id=bot_id, sequence_identifier=seq_id)

# if '__name__' == '__name__':
#         # print('test data')
#         # print(test_df)
#         # print(compute_features(test_df))
#         # print(validation_result)
#         query = 'from(bucket: "ArchSimHealth")\
#                 |> range(start:2001-01-01T05:00:00.000Z) \
#                 |> filter(fn: (r) => r._measurement == "health_data")\
#                 |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") \
#                 |> keep(columns: ["heart_rate", "steps","distance","calories","stress","activity","_time", "stress_level"])' 
#         instance = InfluxDBConn()
#         validation_result = instance.openInfluxDBBotBucket().query_api().query_data_frame(query)
#         print(validation_result)
#         map = create_constellation(validation_result, 'stress')
#         print(map)
#         hashes = create_stress_hashes(map, "test")
#         for i, (hash, (time, _)) in enumerate(hashes.items()):
#                 if i > 10: 
#                         break
#         print(f"Hash {hash} occurred at {time}")



        


