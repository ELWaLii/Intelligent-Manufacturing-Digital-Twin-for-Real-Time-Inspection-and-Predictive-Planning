**Real-Time Inspection and Predictive Planning (KAVE)**

##  Project Overview
The **Intelligent Manufacturing Digital Twin** is an event-driven, scalable architecture designed for modern smart factories (Industry 4.0). It seamlessly merges high-frequency IoT sensor telemetry with real-time Computer Vision (CV) to detect machinery anomalies, inspect product quality, and allow factory managers to simulate future production scenarios using Machine Learning.

##  Key Features
* **IoT Telemetry Streaming:** Real-time ingestion of machine parameters (temperature, vibration) using Python edge simulators and Apache Kafka.
* **Computer Vision Inspection:** Automated defect detection on the assembly line using OpenCV and YOLOv8, separating heavy image payloads from lightweight JSON metadata streams.
* **Real-time Anomaly Detection:** Hot-path ML processing (Scikit-Learn) to identify critical equipment failures in milliseconds.
* **Predictive "What-If" Simulation:** A FastAPI-driven simulation engine powered by XGBoost, allowing managers to tweak input parameters and forecast production outcomes.
* **Unified Monitoring Dashboard:** A comprehensive Grafana UI visualizing live sensor data, real-time defect images, and simulation forecasts.


```text
##  Modular Repository Structure
We employ a modular monorepo strategy to prevent merge conflicts and isolate domain-specific logic:

├── 1_edge_simulators/       # Python scripts simulating IoT sensors & Industrial Cameras
├── 2_message_broker/        # Dockerized Apache Kafka infrastructure
├── 3_data_processing/       # Kafka Consumers & ML Inference (Scikit-Learn/XGBoost)
├── 4_simulation_api/        # FastAPI backend for Grafana "What-If" inputs
├── 5_database/              # Azure SQL  schemas and queries
├── 6_grafana_dashboards/    # Exported Grafana JSON dashboard templates
└── docs/                    # System architecture 
## Technology Stack
Edge/Simulators: Python, OpenCV, Ultralytics (YOLOv8)

Ingestion & Messaging: Apache Kafka, kafka-python

Data Processing & AI: Pandas, Scikit-Learn, XGBoost, PyTorch

Backend API: FastAPI, Uvicorn

Database & Storage: Azure SQL (Metadata), Azure Blob Storage (Images)

Visualization: Grafana (Dynamic Image & Data Manipulation Panels)

## Getting Started (Local Development)
1. Prerequisites
Docker & Docker Compose
Python 3.10+

Git

2. Installation & Setup
Clone the repository and set up your virtual environment:

git clone https://github.com/ELWaLii/Intelligent-Manufacturing-Digital-Twin-for-Real-Time-Inspection-and-Predictive-Planning.git
cd Intelligent-Manufacturing-Digital-Twin-for-Real-Time-Inspection-and-Predictive-Planning

python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
3. Spin up Infrastructure
Start the local Kafka broker and Database via Docker:

cd 2_message_broker
docker-compose up -d
(More detailed instructions for running specific Edge Simulators and ML Consumers will be added as modules are actively developed).

 ## Contributors
Eng / Mostafa Ashraf WaliAllah
Eng / Basmala AbuElhamd Mahmmud
Eng / Ibrahim Yussif Mahmmud
Eng / Ola Alaa Mohammed
Eng / Mahammed Hamed Ibrahim
Eng / Mahmmud Mohammed Qotb
