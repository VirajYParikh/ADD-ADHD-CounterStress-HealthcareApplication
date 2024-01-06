import KnowledgeManager
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix


class KNN(KnowledgeManager):
    def __init__(self, symbol, action, n_neighbors=3):
        super(KNN, self).__init__(symbol, action)
        self.name = 'KNN'
        self.model = KNeighborsClassifier(n_neighbors=n_neighbors)

    def fit(self):
        self.model.fit(self.X_train, self.y_train)

    def predict(self, x_test):
        return self.model.prefict(x_test)
