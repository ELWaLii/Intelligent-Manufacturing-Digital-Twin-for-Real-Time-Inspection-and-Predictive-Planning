# KAVE Intelligent Manufacturing — UML & System Diagrams

The following diagrams illustrate the architecture, behavior, and structural components of the KAVE Intelligent Manufacturing Digital Twin using Mermaid.js.

## 1. Class Diagram
Illustrates the core system entities and their relationships.
```mermaid
classDiagram
    class Dashboard {
        +render_vision_ui()
        +render_simulation_ui()
        +render_chatbot()
    }
    class VisionEngine {
        -device : String
        -backbone : WideResNet50_2
        +process_image_padim(img)
        +process_image_patchcore(img)
    }
    class PredictionEngine {
        -xgb_model : XGBClassifier
        +predict_wear(sensor_data)
    }
    class ChatAgent {
        -llm : GeminiFlash
        -sql_db : PostgreSQL
        -ts_db : InfluxDB
        +query_database(prompt)
    }
    
    Dashboard --> VisionEngine : REST API
    Dashboard --> ChatAgent : LangChain
    Dashboard --> PredictionEngine : REST API
```

## 2. Object Diagram
Shows an instance snapshot of the system in production.
```mermaid
objectDiagram
    object RedisStream {
        name = "results_stream"
        throughput = "30 FPS"
    }
    object PaDiMWorker {
        state = "listening"
        model = "Gaussian Stats"
    }
    object APIEndpoint {
        route = "/predict"
        model = "PatchCore KNN"
    }
    
    PaDiMWorker --|> RedisStream : Consumes/Publishes
    APIEndpoint --|> PaDiMWorker : Shares WideResNet Backbone
```

## 3. Component Diagram
Details the microservice boundaries.
```mermaid
componentDiagram
    package "Frontend" {
        [Streamlit Dashboard]
        [Grafana]
    }
    package "AI Microservices" {
        [Vision Engine]
        [Prediction Engine]
    }
    package "Databases" {
        [PostgreSQL]
        [InfluxDB]
        [Redis]
    }
    
    [Streamlit Dashboard] --> [Vision Engine] : HTTP POST
    [Streamlit Dashboard] --> [Prediction Engine] : HTTP POST
    [Streamlit Dashboard] --> [PostgreSQL] : Read Logs
    [Vision Engine] --> [Redis] : Pub/Sub
    [Prediction Engine] --> [InfluxDB] : Read Telemetry
```

## 4. Deployment Diagram
Shows the Docker network architecture.
```mermaid
flowchart TB
    subgraph Host[Host Machine (Docker Engine)]
        subgraph Network[kave_network]
            UI[kave_dashboard :8501]
            Grafana[kave_grafana :3000]
            Vision[kave_vision_engine :8000]
            Pred[kave_prediction_engine :8001]
            PG[(kave_db :5432)]
            Influx[(kave_influx_db :8086)]
            Redis[(kave_redis :6379)]
        end
    end
    UI --> Vision
    UI --> PG
    UI --> Influx
    Vision --> Redis
    Vision --> PG
    Grafana --> Influx
    Grafana --> PG
```

## 5. Package Diagram
Shows code organization within the repository.
```mermaid
classDiagram
    namespace Services {
        class dashboard
        class vision_engine
        class prediction_engine
        class iot_bridge
    }
    namespace DataProcessing {
        class ai_training
        class data_generation
    }
    dashboard --> vision_engine
    iot_bridge --> prediction_engine
```

## 6. Composite Structure Diagram
Internal structure of the Vision Engine.
```mermaid
blockBeta
  columns 3
  API["FastAPI App"]:1
  space:1
  Redis["Redis Consumer"]:1
  
  block:Backbone
    WRN["WideResNet-50-2 Backbone"]
  end
  
  API -- "Feature Extraction" --> Backbone
  Redis -- "Feature Extraction" --> Backbone
  
  Backbone -- "PatchCore KNN" --> API
  Backbone -- "PaDiM Stats" --> Redis
```

## 7. Use Case Diagram
User interactions with the digital twin.
```mermaid
usecaseDiagram
    actor PlantManager as "Plant Manager"
    actor QualityInspector as "Quality Inspector"
    
    usecase UC1 as "View Live CNC Dashboards"
    usecase UC2 as "Upload Part for Deep Inspection"
    usecase UC3 as "Chat with AI Agent (Gemini)"
    usecase UC4 as "Simulate Production Scheduling"
    
    PlantManager --> UC1
    PlantManager --> UC3
    PlantManager --> UC4
    QualityInspector --> UC2
    QualityInspector --> UC1
```

## 8. Sequence Diagram
Dual-Pipeline flow (Real-Time vs Manual).
```mermaid
sequenceDiagram
    actor Camera as Edge Camera
    actor User as Dashboard User
    participant Redis as Redis Stream
    participant VE as Vision Engine
    participant DB as PostgreSQL
    
    %% Real-Time Flow
    Note over Camera, DB: Real-Time Stream Flow (PaDiM)
    Camera->>Redis: Publish Frame
    Redis->>VE: Consume Frame (Background Thread)
    VE->>VE: Extract WideResNet Features
    VE->>VE: PaDiM Distance Calculation (< 50ms)
    VE->>Redis: Publish Result (Score + Heatmap)
    VE->>DB: Log Defect (If Anomaly)
    
    %% Manual Flow
    Note over User, VE: Manual Inspection Flow (PatchCore)
    User->>VE: POST /predict (Image)
    VE->>VE: Extract WideResNet Features
    VE->>VE: PatchCore KNN Search (~500ms)
    VE-->>User: Return Score + Heatmap
    VE->>DB: Log Manual Inspection Result
```

## 9. Activity Diagram
Defect logging process.
```mermaid
stateDiagram-v2
    [*] --> ReceiveImage
    ReceiveImage --> ExtractFeatures : WideResNet
    ExtractFeatures --> CalculateScore
    CalculateScore --> IsAnomaly?
    
    state IsAnomaly? {
        direction LR
        Yes --> LogToDatabase
        No --> DropFrame
    }
    
    LogToDatabase --> PublishAlert
    PublishAlert --> [*]
    DropFrame --> [*]
```

## 10. State Machine Diagram
Camera/Stream state.
```mermaid
stateDiagram-v2
    [*] --> Disconnected
    Disconnected --> Connecting : Toggle Live Feed
    Connecting --> Streaming : Redis Ping Success
    Streaming --> Analyzing : Frame Received
    Analyzing --> Streaming : PaDiM Complete
    Streaming --> Disconnected : Toggle Off / Error
```

## 11. Communication Diagram
Interaction between components during AI Chat.
```mermaid
flowchart LR
    User([User]) -- "1: Asks Question" --> Streamlit
    Streamlit -- "2: Invokes Langchain" --> Gemini
    Gemini -- "3: Decides Tool" --> Tools
    Tools -- "4a: SQL Query" --> Postgres
    Tools -- "4b: Flux Query" --> InfluxDB
    Postgres -- "5a: Data Return" --> Gemini
    InfluxDB -- "5b: Data Return" --> Gemini
    Gemini -- "6: Synthesizes Answer" --> Streamlit
    Streamlit -- "7: Displays Markdown" --> User
```

## 12. Timing Diagram
Latency comparison of the dual pipeline.
```mermaid
gantt
    title Inference Latency Comparison
    dateFormat  s
    axisFormat %S
    
    section PaDiM (Stream)
    Feature Extraction :a1, 0, 0.02s
    Mahalanobis Dist   :a2, after a1, 0.01s
    Redis Publish      :a3, after a2, 0.01s
    
    section PatchCore (API)
    Feature Extraction :b1, 0, 0.02s
    Coreset KNN Search :b2, after b1, 0.5s
    HTTP Response      :b3, after b2, 0.05s
```
