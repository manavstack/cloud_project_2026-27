"""
High-Performance Machine Learning Models Architecture
Includes:
- L2-Regularized Logistic Regression (GLM Baseline)
- Multi-Layer Perceptron Neural Network (Deep Architecture with Adam & ReLU)
- Random Forest Classifier (Bootstrap Aggregation Ensemble)
- Gradient Boosting Classifier (Sequential Residual Gradient Descent)
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple

# ==========================================
# 1. Regularized Logistic Regression (Baseline)
# ==========================================
class LogisticRegressionModel:
    """
    L2-Regularized Logistic Regression trained with Mini-Batch Gradient Descent.
    Reference: Hastie, Tibshirani, Friedman (2009). The Elements of Statistical Learning.
    """
    def __init__(self, lr: float = 0.05, l2_reg: float = 1e-4, epochs: int = 200, batch_size: int = 128):
        self.lr = lr
        self.l2_reg = l2_reg
        self.epochs = epochs
        self.batch_size = batch_size
        self.weights = None
        self.bias = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionModel":
        n_samples, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0.0
        
        for _ in range(self.epochs):
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y[indices]
            
            for i in range(0, n_samples, self.batch_size):
                X_batch = X_shuffled[i:i + self.batch_size]
                y_batch = y_shuffled[i:i + self.batch_size]
                
                # Forward pass
                linear = np.dot(X_batch, self.weights) + self.bias
                probs = 1.0 / (1.0 + np.exp(-np.clip(linear, -25, 25)))
                
                # Gradients
                errors = probs - y_batch
                dw = (np.dot(X_batch.T, errors) / len(X_batch)) + (self.l2_reg * self.weights)
                db = np.mean(errors)
                
                # Update
                self.weights -= self.lr * dw
                self.bias -= self.lr * db
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        linear = np.dot(X, self.weights) + self.bias
        p1 = 1.0 / (1.0 + np.exp(-np.clip(linear, -25, 25)))
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


# ==========================================
# 2. Multi-Layer Perceptron (Neural Network)
# ==========================================
class MLPNeuralNetwork:
    """
    Deep Multi-Layer Perceptron with ReLU activations and Adam Optimization.
    Reference: Rumelhart, Hinton, Williams (1986); Kingma & Ba (2014) Adam.
    """
    def __init__(
        self, 
        hidden_dims: List[int] = [64, 32], 
        lr: float = 0.005, 
        epochs: int = 150, 
        batch_size: int = 64,
        l2_reg: float = 1e-4
    ):
        self.hidden_dims = hidden_dims
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.l2_reg = l2_reg
        self.weights = []
        self.biases = []

    def _relu(self, Z: np.ndarray) -> np.ndarray:
        return np.maximum(0, Z)

    def _relu_grad(self, Z: np.ndarray) -> np.ndarray:
        return (Z > 0).astype(float)

    def _sigmoid(self, Z: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(Z, -25, 25)))

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MLPNeuralNetwork":
        np.random.seed(42)
        n_samples, n_features = X.shape
        dims = [n_features] + self.hidden_dims + [1]
        
        # He initialization
        self.weights = [
            np.random.randn(dims[i], dims[i+1]) * np.sqrt(2.0 / dims[i])
            for i in range(len(dims) - 1)
        ]
        self.biases = [np.zeros((1, dims[i+1])) for i in range(len(dims) - 1)]
        
        # Adam momentum terms
        m_w = [np.zeros_like(w) for w in self.weights]
        v_w = [np.zeros_like(w) for w in self.weights]
        m_b = [np.zeros_like(b) for b in self.biases]
        v_b = [np.zeros_like(b) for b in self.biases]
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        t = 0
        
        y_col = y.reshape(-1, 1)

        for _ in range(self.epochs):
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y_col[indices]

            for i in range(0, n_samples, self.batch_size):
                t += 1
                X_b = X_shuffled[i:i + self.batch_size]
                y_b = y_shuffled[i:i + self.batch_size]
                m = len(X_b)
                
                # Forward propagation
                activations = [X_b]
                zs = []
                for layer in range(len(self.weights) - 1):
                    z = np.dot(activations[-1], self.weights[layer]) + self.biases[layer]
                    zs.append(z)
                    activations.append(self._relu(z))
                
                # Output layer
                z_out = np.dot(activations[-1], self.weights[-1]) + self.biases[-1]
                zs.append(z_out)
                a_out = self._sigmoid(z_out)
                activations.append(a_out)
                
                # Backward propagation
                dZ = a_out - y_b
                grads_w = []
                grads_b = []
                
                for layer in reversed(range(len(self.weights))):
                    dW = (np.dot(activations[layer].T, dZ) / m) + (self.l2_reg * self.weights[layer])
                    dB = np.sum(dZ, axis=0, keepdims=True) / m
                    grads_w.insert(0, dW)
                    grads_b.insert(0, dB)
                    
                    if layer > 0:
                        dA = np.dot(dZ, self.weights[layer].T)
                        dZ = dA * self._relu_grad(zs[layer - 1])
                
                # Adam Parameter Updates
                for l in range(len(self.weights)):
                    m_w[l] = beta1 * m_w[l] + (1 - beta1) * grads_w[l]
                    v_w[l] = beta2 * v_w[l] + (1 - beta2) * (grads_w[l] ** 2)
                    m_b[l] = beta1 * m_b[l] + (1 - beta1) * grads_b[l]
                    v_b[l] = beta2 * v_b[l] + (1 - beta2) * (grads_b[l] ** 2)
                    
                    m_w_hat = m_w[l] / (1 - beta1 ** t)
                    v_w_hat = v_w[l] / (1 - beta2 ** t)
                    m_b_hat = m_b[l] / (1 - beta1 ** t)
                    v_b_hat = v_b[l] / (1 - beta2 ** t)
                    
                    self.weights[l] -= self.lr * m_w_hat / (np.sqrt(v_w_hat) + eps)
                    self.biases[l] -= self.lr * m_b_hat / (np.sqrt(v_b_hat) + eps)
                    
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        a = X
        for layer in range(len(self.weights) - 1):
            z = np.dot(a, self.weights[layer]) + self.biases[layer]
            a = self._relu(z)
        z_out = np.dot(a, self.weights[-1]) + self.biases[-1]
        p1 = self._sigmoid(z_out).flatten()
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


# ==========================================
# 3. Decision Tree & Random Forest Classifier
# ==========================================
class DecisionNode:
    def __init__(self, feature=None, threshold=None, left=None, right=None, value=None):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    @property
    def is_leaf(self):
        return self.value is not None

class DecisionTreeClassifierCustom:
    def __init__(self, max_depth: int = 8, min_samples_split: int = 10, max_features: Optional[int] = None):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.root = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "DecisionTreeClassifierCustom":
        self.root = self._grow_tree(X, y)
        return self

    def _gini(self, y: np.ndarray) -> float:
        if len(y) == 0:
            return 0.0
        p = np.mean(y)
        return 1.0 - (p**2 + (1 - p)**2)

    def _grow_tree(self, X: np.ndarray, y: np.ndarray, depth: int = 0) -> DecisionNode:
        n_samples, n_features = X.shape
        n_classes = len(np.unique(y))

        if depth >= self.max_depth or n_classes == 1 or n_samples < self.min_samples_split:
            return DecisionNode(value=np.mean(y))

        # Select random subset of features (Breiman's Random Forest principle)
        feat_indices = np.arange(n_features)
        if self.max_features and self.max_features < n_features:
            feat_indices = np.random.choice(n_features, self.max_features, replace=False)

        best_feat, best_thresh, best_gini = None, None, 1.0
        current_gini = self._gini(y)

        for feat in feat_indices:
            values = np.unique(X[:, feat])
            if len(values) > 10:
                # Subsample thresholds for speed
                thresholds = np.percentile(values, np.linspace(10, 90, 9))
            else:
                thresholds = values

            for thresh in thresholds:
                left_mask = X[:, feat] <= thresh
                y_left, y_right = y[left_mask], y[~left_mask]
                if len(y_left) == 0 or len(y_right) == 0:
                    continue
                gini_split = (len(y_left) * self._gini(y_left) + len(y_right) * self._gini(y_right)) / n_samples
                if gini_split < best_gini:
                    best_gini = gini_split
                    best_feat = feat
                    best_thresh = thresh

        if best_feat is None or (current_gini - best_gini) < 1e-4:
            return DecisionNode(value=np.mean(y))

        left_mask = X[:, best_feat] <= best_thresh
        left_child = self._grow_tree(X[left_mask], y[left_mask], depth + 1)
        right_child = self._grow_tree(X[~left_mask], y[~left_mask], depth + 1)
        return DecisionNode(feature=best_feat, threshold=best_thresh, left=left_child, right=right_child)

    def _traverse(self, x: np.ndarray, node: DecisionNode) -> float:
        if node.is_leaf:
            return node.value
        if x[node.feature] <= node.threshold:
            return self._traverse(x, node.left)
        return self._traverse(x, node.right)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probs_1 = np.array([self._traverse(x, self.root) for x in X])
        return np.column_stack([1.0 - probs_1, probs_1])

class RandomForestClassifierModel:
    """
    Random Forest Ensemble with bagging and randomized feature subspaces.
    Reference: Breiman, Leo (2001). "Random Forests". Machine Learning.
    """
    def __init__(self, n_estimators: int = 25, max_depth: int = 7, min_samples_split: int = 8):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.trees: List[DecisionTreeClassifierCustom] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestClassifierModel":
        np.random.seed(42)
        n_samples, n_features = X.shape
        max_features = int(np.sqrt(n_features)) + 1
        self.trees = []

        for _ in range(self.n_estimators):
            # Bootstrap sample (sampling with replacement)
            boot_idx = np.random.choice(n_samples, n_samples, replace=True)
            X_boot, y_boot = X[boot_idx], y[boot_idx]
            
            tree = DecisionTreeClassifierCustom(
                max_depth=self.max_depth, 
                min_samples_split=self.min_samples_split, 
                max_features=max_features
            )
            tree.fit(X_boot, y_boot)
            self.trees.append(tree)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        all_probs = np.array([tree.predict_proba(X) for tree in self.trees])
        return np.mean(all_probs, axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
