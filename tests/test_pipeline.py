import os
import sys
import numpy as np

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from data_loader import DataLoader
from models import LogisticRegressionModel, MLPNeuralNetwork, RandomForestClassifierModel
from predict import ProductionPredictor

def test_data_loader_split():
    loader = DataLoader()
    X = np.random.randn(100, 5)
    y = np.random.randint(0, 2, 100)
    X_tr, X_te, y_tr, y_te = loader.split_train_test(X, y, test_size=0.2)
    assert len(X_tr) + len(X_te) == 100
    assert 78 <= len(X_tr) <= 82

def test_logistic_regression():
    X = np.random.randn(50, 4)
    y = np.random.randint(0, 2, 50)
    model = LogisticRegressionModel(epochs=10)
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == 50
    assert set(np.unique(preds)).issubset({0, 1})

def test_mlp_neural_net():
    X = np.random.randn(50, 4)
    y = np.random.randint(0, 2, 50)
    model = MLPNeuralNetwork(hidden_dims=[16], epochs=10)
    model.fit(X, y)
    probs = model.predict_proba(X)
    assert probs.shape == (50, 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))

def test_production_predictor():
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    predictor = ProductionPredictor(models_dir=models_dir)
    dummy_input = np.random.randn(2, predictor.metadata["n_features"])
    preds = predictor.predict(dummy_input)
    assert len(preds) == 2
