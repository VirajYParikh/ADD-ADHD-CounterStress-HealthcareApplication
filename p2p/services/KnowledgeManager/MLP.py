from KnowledgeManager import KnowledgeManager
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler


class MLP(KnowledgeManager):
    def __init__(self, symbol, action):
        super(MLP, self).__init__(symbol, action)
        self.name = 'MLP'
        self.model = MLPClassifier(
            hidden_layer_sizes=(30, 30, 30),
            random_state=1
        )

    def fit(self):
        self.model.fit(self.X_train, self.y_train)

    def predict(self, x_test):
        return self.model.predict(x_test)
