import pandas as pd
import struct


class Regime:

    def get_regime(self):
        df = pd.read_csv("simulateddata.csv").drop(
            ["timestamp", "steps", "distance(miles)", "user_id"],
            axis=1)

        X = df.values
        X = X.reshape((df.shape[0] // 5, df.shape[1] * 5))
        df1 = X[0:10, :]
        return df1
