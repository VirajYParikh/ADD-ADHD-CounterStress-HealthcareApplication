import argparse
import sys
import pandas as pd
from keras.models import Sequential
from keras.layers import Dense
from sklearn.preprocessing import StandardScaler
from sklearn import tree
import importlib
import tensorflow as tf
import os
import pandas as pd
import numpy as np
from sklearn import svm
import pickle
import coremltools

if __name__ == "__main__":
    myargparser = argparse.ArgumentParser()
    myargparser.add_argument('--maxtime', type=int, const=120, nargs='?', default=120)
    myargparser.add_argument('--mode', type=int, const=120, nargs='?', default=1) # 1: Stress Detection, 2: Action evaluation
    myargparser.add_argument('--bot_id', type=str, const='text', nargs='?', default=1)
    myargparser.add_argument('--data_api', type=str, const='text', nargs='?', default='')
    myargparser.add_argument('--event_id', type=int, const=1, nargs='?', default=1)
    myargparser.add_argument('--result_path', type=str, const='text', nargs='?', default='')
                             
    
    args = myargparser.parse_args()
    sys.path.append(args.data_api)
    bot_data = importlib.import_module('BotData')

    print(args.maxtime)
    print(args.bot_id)
    print(args.data_api)
    if args.mode==1:
        mybotdata = bot_data.BotData()
        result = mybotdata.fetchdataframe(1)
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        dataset=result.iloc[:,2:]
        dataset['hour']=dataset._time.dt.hour
        dataset['mins']=dataset._time.dt.minute
        X = dataset[['calories','distance','heart_rate','steps','hour','mins']].values
        y = dataset[['stress']].values
        print(X.shape,y.shape)
        X_train,y_train = X,y
        #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 0)
        sc = StandardScaler()
        X_train = sc.fit_transform(X_train)
        #X_test = sc.transform(X_test)
        classifier = Sequential()
        classifier.add(Dense(3, kernel_initializer = 'uniform', activation = 'relu', input_dim = 6))
        classifier.add(Dense(7, kernel_initializer = 'uniform', activation = 'relu'))
        classifier.add(Dense(1, kernel_initializer = 'uniform', activation = 'sigmoid'))
        classifier.compile(optimizer = 'adam', loss = 'binary_crossentropy', metrics = ['accuracy'])
        classifier.fit(X_train, y_train, batch_size = 10, epochs = 100)
        filelocation = args.result_path
        classifier.save(filelocation)
    elif args.mode==2:
        mybotdata = bot_data.BotData()
        result = mybotdata.fetchdataframe(2)
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        dataset=result.iloc[:,2:]
        #dataset = pd.read_csv('test8-3.csv')
        X = dataset[['calories','distance','heart_rate','steps','stress']].values
        y = dataset[['activity']].values

        X_train,y_train = X,y
        clf = svm.SVC(C=0.8, kernel='rbf', gamma=20, decision_function_shape='ovr')
        clf.fit(X_train, y_train)   
        filelocation = args.result_path
        filename = 'bot1.sav'
        with open(filelocation+'/'+filename, 'wb') as f:
            pickle.dump(clf,f)
        coreml_model = coremltools.converters.sklearn.convert(clf,
                                                         ['calories','distance','heart_rate','steps','stress'],
                                                         'activity')
        coreml_model.save('bot1.mlmodel')

