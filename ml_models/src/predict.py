"""
Production Inference Script
Loads serialized model weights and preprocessor parameters to execute fast inference.
Usage:
    python src/predict.py
"""

import os
import sys
import json
import numpy as np
from typing import Union, List

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -25, 25)))

def relu(z):
    return np.maximum(0, z)

class ProductionPredictor:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.metadata_path = os.path.join(models_dir, "model_metadata.json")
        self.weights_path = os.path.join(models_dir, "best_model.npz")
        
        if not os.path.exists(self.metadata_path) or not os.path.exists(self.weights_path):
            raise FileNotFoundError("Model artifacts not found. Please run 'python src/train.py' first.")
            
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
            
        self.weights_data = np.load(self.weights_path)
        self.scaler_mean = self.weights_data["scaler_mean"]
        self.scaler_std = self.weights_data["scaler_std"]
        self.architecture = self.metadata["best_model_architecture"]

    def preprocess(self, X: np.ndarray) -> np.ndarray:
        return (X - self.scaler_mean) / self.scaler_std

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.preprocess(X)
        
        if self.architecture == "Deep_MLP_Neural_Network":
            a = X_scaled
            layer = 0
            while f"W_{layer}" in self.weights_data:
                W = self.weights_data[f"W_{layer}"]
                b = self.weights_data[f"b_{layer}"]
                z = np.dot(a, W) + b
                # Last layer has sigmoid activation, intermediate have ReLU
                if f"W_{layer + 1}" in self.weights_data:
                    a = relu(z)
                else:
                    a = sigmoid(z)
                layer += 1
            p1 = a.flatten()
            return np.column_stack([1.0 - p1, p1])
            
        elif self.architecture == "Logistic_Regression_L2":
            w = self.weights_data["weights"]
            b = self.weights_data["bias"][0]
            linear = np.dot(X_scaled, w) + b
            p1 = sigmoid(linear)
            return np.column_stack([1.0 - p1, p1])
            
        else:
            raise NotImplementedError(f"Architecture {self.architecture} not supported in stand-alone predictor.")

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs[:, 1] >= 0.5).astype(int)

if __name__ == "__main__":
    print("[*] Loading Champion Model for Inference...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    
    predictor = ProductionPredictor(models_dir=models_dir)
    print(f"[*] Successfully loaded: {predictor.architecture}")
    print(f"[*] Input Feature Count: {predictor.metadata['n_features']}")
    
    # Run test prediction on 3 random samples
    sample_inputs = np.random.randn(3, predictor.metadata["n_features"])
    predictions = predictor.predict(sample_inputs)
    probabilities = predictor.predict_proba(sample_inputs)
    
    print("\n--- SAMPLE INFERENCE RESULTS ---")
    for i in range(len(sample_inputs)):
        print(f"Sample #{i+1}: Predicted Class = {predictions[i]} (Confidence: {probabilities[i][predictions[i]]*100:.2f}%)")
