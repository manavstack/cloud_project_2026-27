# 📚 Machine Learning Theoretical Formulations & References

This document provides formal mathematical formulations and foundational literature citations for all models implemented and evaluated in this repository.

---

## 1. Multi-Layer Perceptron (Deep Neural Network)

### Theoretical Formulation
The Multi-Layer Perceptron maps input vectors $\mathbf{x} \in \mathbb{R}^d$ to class probabilities $\hat{y} \in [0, 1]$ across $L$ layers:
$$\mathbf{z}^{(l)} = \mathbf{W}^{(l)} \mathbf{a}^{(l-1)} + \mathbf{b}^{(l)}$$
$$\mathbf{a}^{(l)} = \text{ReLU}(\mathbf{z}^{(l)}) = \max(0, \mathbf{z}^{(l)}), \quad \forall l \in \{1, \dots, L-1\}$$
$$\hat{y} = \sigma(\mathbf{z}^{(L)}) = \frac{1}{1 + e^{-\mathbf{z}^{(L)}}}$$

### Optimization & Loss Function
Parameters are optimized via Binary Cross-Entropy loss with $L_2$ weight regularization:
$$\mathcal{L}(\theta) = -\frac{1}{N} \sum_{i=1}^N \left[ y_i \log \hat{y}_i + (1 - y_i) \log(1 - \hat{y}_i) \right] + \frac{\lambda}{2} \sum_{l=1}^L \|\mathbf{W}^{(l)}\|_F^2$$
Gradients are computed using Backpropagation and updated via the **Adam** (Adaptive Moment Estimation) optimizer:
$$m_t = \beta_1 m_{t-1} + (1 - \beta_1) g_t, \quad v_t = \beta_2 v_{t-1} + (1 - \beta_2) g_t^2$$
$$\hat{m}_t = \frac{m_t}{1 - \beta_1^t}, \quad \hat{v}_t = \frac{v_t}{1 - \beta_2^t}$$
$$\theta_t = \theta_{t-1} - \frac{\eta}{\sqrt{\hat{v}_t} + \epsilon} \hat{m}_t$$

### Foundational References
1. **Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986).**  
   *Learning representations by back-propagating errors.* Nature, 323(6088), 533–536. [DOI: 10.1038/323533a0](https://doi.org/10.1038/323533a0)
2. **Kingma, D. P., & Ba, J. (2014).**  
   *Adam: A Method for Stochastic Optimization.* International Conference on Learning Representations (ICLR). [arXiv:1412.6980](https://arxiv.org/abs/1412.6980)
3. **He, K., Zhang, X., Ren, S., & Sun, J. (2015).**  
   *Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification.* IEEE ICCV, 1026–1034.

---

## 2. Random Forest Classifier

### Theoretical Formulation
An ensemble of $B$ randomized decision trees $\{T_b\}_{b=1}^B$ grown on bootstrap samples $\mathcal{D}_b^*$:
$$\hat{y} = \frac{1}{B} \sum_{b=1}^B T_b(\mathbf{x})$$
At each node split, a random subset of $m \approx \sqrt{p}$ features is sampled to decorrelate individual trees. Splits minimize node Gini Impurity:
$$I_G(t) = 1 - \sum_{k=1}^K p(k|t)^2$$

### Foundational References
1. **Breiman, Leo (2001).**  
   *Random Forests.* Machine Learning, 45(1), 5–32. [DOI: 10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324)
2. **Breiman, Leo (1996).**  
   *Bagging Predictors.* Machine Learning, 24(2), 123–140. [DOI: 10.1007/BF00058655](https://doi.org/10.1007/BF00058655)
3. **Hastie, T., Tibshirani, R., & Friedman, J. (2009).**  
   *The Elements of Statistical Learning: Data Mining, Inference, and Prediction.* Springer Series in Statistics.

---

## 3. Regularized Logistic Regression (GLM Baseline)

### Theoretical Formulation
Generalized Linear Model using logit link function:
$$\log \left(\frac{P(Y=1|\mathbf{x})}{1 - P(Y=1|\mathbf{x})}\right) = \mathbf{w}^T \mathbf{x} + b$$
Subject to Ridge ($L_2$) penalty:
$$\min_{\mathbf{w}, b} -\sum_{i=1}^N \left( y_i \log \sigma(\mathbf{w}^T \mathbf{x}_i + b) + (1 - y_i) \log(1 - \sigma(\mathbf{w}^T \mathbf{x}_i + b)) \right) + \frac{\lambda}{2} \|\mathbf{w}\|_2^2$$

### Foundational References
1. **Cox, D. R. (1958).**  
   *The Regression Analysis of Binary Sequences.* Journal of the Royal Statistical Society: Series B, 20(2), 215–232.
2. **Pedregosa, F., et al. (2011).**  
   *Scikit-learn: Machine Learning in Python.* Journal of Machine Learning Research (JMLR), 12, 2825–2830.
