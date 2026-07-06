# KAVE Intelligent Manufacturing — Digital Twin & Vision Inspection 🏭

![License](https://img.shields.io/badge/License-Proprietary-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker)
![PyTorch](https://img.shields.io/badge/PyTorch-AI-EE4C2C?logo=pytorch)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit)

##  Project Overview
**KAVE Intelligent Manufacturing** is a state-of-the-art Enterprise Digital Twin designed to monitor, inspect, and optimize modern CNC machining workflows. By fusing High-Frequency IoT telemetry, Machine Learning (XGBoost), and deep learning computer vision, KAVE provides a robust real-time command center for production floors.

The platform exists to solve two critical manufacturing challenges:
1. **Unplanned Downtime:** Predicting CNC tool wear before catastrophic failure.
2. **Quality Control Bottlenecks:** Instantly identifying defective parts (e.g., metal nuts) without slowing down the assembly line.

## Architecture Highlights
The core of our defect detection relies on a **Dual-Pipeline Vision Engine** that balances speed and accuracy using a shared `WideResNet-50-2` backbone:

- **PaDiM (Real-Time Streaming):** Handles extreme high-throughput video streams via Redis. By leveraging Mahalanobis distance over multivariate Gaussian distributions, PaDiM achieves sub-second latency for instant edge-camera inspection.
- **PatchCore (Manual Deep Inspection):** Handled via FastAPI REST endpoints for manual, on-demand high-precision anomaly detection using a K-Nearest Neighbors (KNN) memory bank. 
- **Gemini 1.5 Flash (AI Agent):** A dual-database Chatbot (PostgreSQL + InfluxDB) that translates human queries into complex SQL/Flux analytics instantly.

## Tech Stack
- **Infrastructure & Orchestration:** Docker, Docker Compose
- **Backend & APIs:** FastAPI, Python 3.10+
- **Frontend / UI:** Streamlit
- **Computer Vision & AI:** PyTorch, OpenCV, Albumentations, Gemini 1.5 Flash API
- **Machine Learning:** XGBoost (scikit-learn)
- **Data & Streaming:** Redis (Streams), InfluxDB (Time-series), PostgreSQL (Relational)
- **Monitoring & BI:** Grafana

## File Structure

```text
KAVE-Intelligent-Manufacturing/
├── docker-compose.yml
├── .env.example
├── README.md
├── FULL_DOCUMENTATION.md
├── UML_DIAGRAMS.md
├── data-processing/
│   ├── ai_training/               # Model training scripts (XGBoost, PaDiM)
│   └── data_generation/           # Data seeding for InfluxDB and Postgres
└── services/
    ├── dashboard/                 # Streamlit UI (Port 8501)
    │   ├── src/components/        # Gemini Chatbot & LangChain tools
    │   └── ui/                    # Streamlit pages (Vision, Simulation)
    ├── grafana/                   # Grafana Dashboards (Port 3000)
    ├── iot-bridge/                # CNC Sensor Ingest to InfluxDB
    ├── prediction-engine/         # XGBoost Predictive Planning API
    ├── vision-engine/             # Dual-Pipeline FastAPI (PaDiM + PatchCore)
    └── vision-producer/           # RTSP/Camera to Redis Stream ingest
```

##  Prerequisites & Installation

### 1. Prerequisites
- Docker Engine and Docker Compose V2
- NVIDIA GPU (Optional but recommended for PyTorch CUDA acceleration)
- Gemini API Key

### 2. Setup Environment
Clone the repository and configure the environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file to include your API keys:
```env
GEMINI_API_KEY="your_google_gemini_api_key_here"
POSTGRES_USER=admin
POSTGRES_PASSWORD=kave_pass
```

### 3. Build & Run the Platform
Deploy the entire microservice architecture using Docker Compose:
```bash
docker compose up -d --build
```

### 4. Access the Dashboards
- **Master Streamlit Dashboard:** [http://localhost:8501](http://localhost:8501)
- **Grafana IoT Analytics:** [http://localhost:3000](http://localhost:3000)
- **Vision Engine API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
