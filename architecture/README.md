# Architecture Diagrams: Edge-Assisted Smart Campus Energy Management using Federated Learning

The Phase I architecture diagrams for **Feature 2: Edge-Assisted Smart Campus Energy Management using Federated Learning** are provided as editable SVG source files matching the project convention:

- **`AWS_Architecture.svg`** — AWS cloud & on-premises Greengrass service interactions, data flow, encrypted storage, FedProx serverless aggregation, MPC optimization, monitoring, and authenticated API access.
- **`System_Architecture.svg`** — End-to-end system workflow from campus physical sensors/DERs through edge DP-SGD learning, secure multiparty aggregation, MPC optimization, and closed-loop BMS control.
- **`Workflow.svg`** — Feature 2 delivery workflow pipeline across telemetry ingestion, local private training, secure synchronization, cloud aggregation, demand-response optimization, and building actuation.

SVG is intentionally used so labels and service placements can be revised without quality loss before final report export.

---

## 1. Feature 2 Architecture Overview

### A. AWS Cloud & Edge Architecture (`AWS_Architecture.svg`)
- **Campus Edge (IoT Greengrass v2)**: Substation edge nodes poll 1Hz smart meters, solar PV inverters, and battery storage over Modbus/BACnet. Raw data is strictly retained in local SQLite/TimescaleDB on the edge to protect student privacy (GDPR/FERPA).
- **Edge DP-SGD Training**: Local BiLSTM forecaster trains locally and perturbs weight updates with $(\epsilon, \delta)$-Differential Privacy noise ($C=1.5, \sigma=0.8$).
- **AWS IoT Core**: Mutual TLS 1.3 broker verifying X.509 device certificates for secure MQTT weight transmission.
- **Serverless FL Orchestration**: **AWS Step Functions** coordinates training rounds ($K \ge 4$ client check-in) and triggers **Amazon ECS Fargate** executing the **FedProx** algorithm with SMPC unmasking and trimmed mean Byzantine filtering.
- **Energy Optimization**: **AWS Lambda** executes a 24-hour rolling horizon **Model Predictive Control (MPC)** solver to calculate optimal battery charge/discharge setpoints and HVAC precooling schedules based on Time-of-Use tariffs.
- **Closed-Loop Actuation**: Setpoints are dispatched via **AWS IoT Device Shadows** down to Greengrass edge controllers for physical Modbus/BACnet execution.

### B. Complete System Architecture (`System_Architecture.svg`)
Organized in an aligned two-tier pipeline:
1. **Campus IoT Sources** $\rightarrow$ **Edge Source Parsers** $\rightarrow$ **Local Edge Store** $\rightarrow$ **Edge DP-SGD Forecaster** (Zero raw observations leave edge).
2. **FedProx Cloud Aggregator** $\rightarrow$ **Multi-Objective MPC Engine** $\rightarrow$ **Closed-Loop BMS Actuation** $\rightarrow$ Continuous closed-loop feedback loop.

### C. Feature 2 Delivery Workflow (`Workflow.svg`)
Sequential 6-stage delivery pipeline:
`Telemetry` $\rightarrow$ `Edge DP Train` $\rightarrow$ `Secure Sync` $\rightarrow$ `FedProx Aggr` $\rightarrow$ `MPC Optimize` $\rightarrow$ `BMS Actuate`.

---

## 2. Mathematical Formulations

### FedProx (Non-IID Building Adaptation)
$$\min_{w} h_k(w; w^t) = f_k(w) + \frac{\mu}{2} \|w - w^t\|^2, \quad \mu = 0.01$$

### Differential Privacy (DP-SGD)
$$\bar{g}_t = g_t / \max\left(1, \frac{\|g_t\|_2}{C}\right), \quad \tilde{g}_t = \frac{1}{B} \left(\sum_{i=1}^B \bar{g}_t(x_i) + \mathcal{N}(0, \sigma^2 C^2 \mathbf{I})\right)$$

### MPC Cost Minimization Objective
$$\min \sum_{t=1}^{24} \left[ C_{\text{grid}}(t) \cdot P_{\text{grid}}(t) + \beta \cdot \max(P_{\text{grid}}) - \gamma \cdot P_{\text{solar}}(t) + \lambda \cdot \text{Discomfort}(t) \right]$$

---

## 3. Adding to Git Repository

```bash
# 1. Navigate to your repository
cd path/to/cloud_project_2026-27

# 2. Copy the architecture directory
cp -r /path/to/architecture .

# 3. Stage, commit, and push
git add architecture/
git commit -m "feat(student): add Feature 2 edge-assisted smart campus FL architecture and workflow"
git push origin <your-feature-branch>
```
