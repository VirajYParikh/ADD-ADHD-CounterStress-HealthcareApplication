import pandas as pd
import numpy as np
import ast
from pyts.image import GramianAngularField
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import pickle


class KnowledgeManager:
    def __init__(self, symbol, action):
        self.symbol = symbol
        self.action = action
        self.transformer = GramianAngularField()

    def load_data(self):
        path = f'./data/{self.symbol}-{self.action}.csv'
        data = pd.read_csv(path)
        # load features
        data['regime'] = data['regime'].apply(lambda x: np.array(ast.literal_eval(x)))
        cols = ['size', 'maxtime', 'regime']
        self.features = np.array([self.feature_extractor(rec[0], rec[1], rec[2]) for rec in data[cols].to_numpy()])
        self.labels = data['strategy'].to_numpy()

    def feature_extractor(self, size, maxtime, regime):
        m, _ = regime.shape
        # padding to (10, 22)
        feature = np.c_[np.full(m, size), np.full(m, maxtime), regime]
        # transform to image (10, 22, 22)
        feature = self.transformer.transform(feature)
        # resize to (4840, )
        feature = feature.flatten()
        return feature

    def train(self):
        self.X_train, self.y_train = self.features, self.labels
        self.fit()

    def save_model(self):
        path = f'../Models/{self.name}-{self.symbol}-{self.action}.pkl'
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)

    def load_model(self):
        path = f'../Models/{self.name}-{self.symbol}-{self.action}.pkl'
        with open(path, 'rb') as f:
            self.model = pickle.load(f)

    def evaluate(self):
        self.X_train, X_test, self.y_train, y_test = \
            train_test_split(self.features, self.labels, test_size=0.2)
        self.fit()
        y_pred = self.predict(X_test)
        print(confusion_matrix(y_test, y_pred))
        print(classification_report(y_test, y_pred))

