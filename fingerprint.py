from prepare_metadata import prepare_metadata
from calculate_fft import create_stress_hashes, create_constellation
# from calculate_statistics import extract_seglearn_feature
from RobothonCompetition.DBUtil.InfluxDBConn import InfluxDBConn
from calc_stats_kats import process_timseries_data

import json
import numpy as np


def process_fingerprint(patient_id):

    # retrieve the simulation data
    patient_id = patient_id
    query = f'from(bucket: "ArchSimHealth")\
                    |> range(start:2001-01-01T05:00:00.000Z) \
                    |> filter(fn: (r) => r._measurement == "health_data")\
                    |> filter(fn: (r) => r.user_id == "{float(patient_id)}")\
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") \
                    |> keep(columns: ["heart_rate", "steps","distance","calories","stress","activity","_time", "stress_level"])' 
    instance = InfluxDBConn()
    stress_data = instance.openInfluxDBBotBucket().query_api().query_data_frame(query)
    print(stress_data)

    # get the start and end timestamp to compute fingerprint id
    start_timestamp = stress_data['_time'].iloc[0].strftime('%Y%m%d%H%M%S')
    end_timestamp = stress_data['_time'].iloc[-1].strftime('%Y%m%d%H%M%S')
    fingerprint_id = str(patient_id)+'_'+start_timestamp+'_'+end_timestamp


    # prepare simulation data and compute the fingerprint from the simulation data
    # for testing purpose, simulation data is stress time series data for patient id 1
    # retrive the dict of fft hashes
    map = create_constellation(stress_data, 'stress')
    hashes = create_stress_hashes(map)
    hashes_json = json.dumps(hashes)
    statistics = process_timseries_data(stress_data)
    metadata = prepare_metadata(patient_id)

    # prepare the payload to MetaML

    # Check if the output of statistics is of type numpy.ndarray (NumPy array)
    if isinstance(statistics, np.ndarray):
        # Convert to list
        statistics = statistics.tolist()

    raw = {
        "fingerprint": {
            "fingerprint_id": fingerprint_id,
            "fingerprint_type": "time_series",
            "fft": hashes,
            "statistics": statistics
        },
        "metadata": metadata,
        "num_bots": 3
    }
    payload = json.dumps(raw)
    return payload