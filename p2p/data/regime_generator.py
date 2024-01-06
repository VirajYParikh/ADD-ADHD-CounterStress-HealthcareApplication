from Get_regime import Regime
import argparse
import random
import pandas as pd
import multiprocessing as mp
import os
from os.path import exists
import sys
sys.path.append('../')


def generate_regime(sym, action, size, maxtime):
    # get current market regime
    R1=Regime()
    health_regime=R1.get_regime()

    record = pd.DataFrame([pd.Series({
        'size': size,
        'maxtime': maxtime,
        'regime': health_regime,
    })])
    print(record)
    path = f"{sym}-{action}.csv"
    record.to_csv(path, mode='a', header=(not os.path.exists(path)))


if __name__ == '__main__':
    myargparser = argparse.ArgumentParser()
    myargparser.add_argument('--symbol', type=str, const="ZNH0:MBO", nargs='?', default="ZNH0:MBO")
    myargparser.add_argument('--action', type=str, const="sell", nargs='?', default="sell")
    myargparser.add_argument('--maxsize', type=int, const=100, nargs='?', default=500)
    myargparser.add_argument('--minsize', type=int, const=20, nargs='?', default=50)
    myargparser.add_argument('--maxtime', type=int, const=24, nargs='?', default=120)
    myargparser.add_argument('--mintime', type=int, const=12, nargs='?', default=15)
    args = myargparser.parse_args()
    comp_size = random.randrange(args.minsize, args.maxsize, 5)
    comp_maxtime = random.randrange(args.mintime, args.maxtime, 3)
    generate_regime(args.symbol, args.action, comp_size, comp_maxtime)

