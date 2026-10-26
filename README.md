<p align="center">
  <img src="frontend/src/assets/AICTE.png" alt="AICTE Logo" width="140" />
</p>

<h1 align="center">ANUMATI</h1>
<h3 align="center">AI-Supported AICTE Approval Process Portal</h3>

<p align="center">
  <b>Automated Network for Unified Management and AI-Tracked Institutions</b><br />
  A high-throughput, secure, intelligent portal streamlining and automating the AICTE institutional approval lifecycle.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue.svg" alt="Version" />
  <img src="https://img.shields.io/badge/Node.js-v18+-green.svg" alt="Node" />
  <img src="https://img.shields.io/badge/Python-v3.13-yellow.svg" alt="Python" />
  <img src="https://img.shields.io/badge/PostgreSQL-Prisma-indigo.svg" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/MongoDB-Mongoose-brightgreen.svg" alt="MongoDB" />
  <img src="https://img.shields.io/badge/FastAPI-ML_Service-teal.svg" alt="FastAPI" />
</p>

---

## 📌 Project Overview

* **Core, Server, API, Security & Authentication:** This portal requires a highly secure, role-based backend architecture. You will need to build robust APIs to handle heavy document uploads and implement strict authentication (like JWT) because you are dealing with official government and institutional data.
* **Hybrid Database (PostgreSQL + MongoDB):** This is the perfect use case for a hybrid database approach. PostgreSQL is utilized for structured, relational records (user accounts, college hierarchies, strict approval statuses via Prisma), while MongoDB persists dynamic forms, institutional payloads, JSON anomaly logs, and AI evaluation outputs via Mongoose.
* **Automated Document Verification & Machine Learning:** The AI component focuses on automated document verification. The ML side performs PDF processing, OCR text extraction via PyMuPDF and Tesseract, signature and official seal verification, and automated compliance checking against AICTE rule books to accelerate the scrutiny workflow.
* **Modern Reactive Web Interfaces:** A clean, responsive frontend dashboard enables colleges to track their approval progress in real-time, while providing an evaluator interface for AICTE committee members to inspect anomalies and approve or reject submissions.

---

## 🏛️ System Architecture

ANUMATI employs an asynchronous, event-driven architecture with dedicated microservices and hybrid data persistence.

### Architecture Overview
<p align="center">
  <img src="frontend/src/assets/PROJECT_ARCHITECTURE.jpg" alt="ANUMATI Project Architecture" width="550" />
</p>

### End-to-End System Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Presentation Tier"]
        College["College / Institutional Applicant"]
        Evaluator["AICTE Scrutiny Committee Evaluator"]
        ReactApp["React 18 SPA\n(Upload UI, Status Tracking & Evaluator View)"]
    end

    subgraph APILayer["Backend Gateway Tier (Node.js / Express)"]
        ExpressServer["Express.js Server\n(Port 5000)"]
        AuthMiddleware["JWT Auth & Role-Based Access Control"]
        UploadMiddleware["Multer Storage Middleware\n(PDF Validation, 15MB Limit)"]
        DocumentController["Document Controller"]
        AIDispatcher["AI Evaluation Dispatcher\n(Axios Multipart Stream)"]
    end

    subgraph DatabaseLayer["Hybrid Persistence Tier"]
        PostgresDB[("PostgreSQL Database\n(Prisma ORM: Users, Documents, Status Logs)")]
        MongoDB[("MongoDB Database\n(Mongoose ODM: Dynamic Forms & AI Reports)")]
    end

    subgraph MLLayer["AI & ML Verification Tier (Python / FastAPI)"]
        FastAPIServer["FastAPI Microservice\n(Port 8000)"]
        PDFProcessor["PyMuPDF Parser\n(Digital PDF Extract & Rasterizer)"]
        OCREngine["Tesseract OCR Engine\n(Image Preprocessing & Extraction)"]
        RuleEngine["AICTE Rule Verification Engine"]
        DocClassifier["Document Classification Model"]
        SignatureDetector["Signature & Official Stamp Detector"]
        ReportGenerator["Verification Report Generator\n(Structured JSON)"]
    end

    College -->|"Upload Application PDF"| ReactApp
    Evaluator -->|"Review & Scrutiny Actions"| ReactApp
    ReactApp -->|"REST API Requests"| ExpressServer

    ExpressServer --> AuthMiddleware
    AuthMiddleware --> UploadMiddleware
    UploadMiddleware --> DocumentController

    DocumentController -->|"Store Document Metadata"| PostgresDB
    DocumentController -->|"Stream PDF (openAsBlob)"| AIDispatcher

    AIDispatcher -->|"POST /evaluate"| FastAPIServer
    FastAPIServer --> PDFProcessor
    PDFProcessor --> OCREngine
    OCREngine --> RuleEngine
    RuleEngine --> DocClassifier
    RuleEngine --> SignatureDetector
    DocClassifier --> ReportGenerator
    SignatureDetector --> ReportGenerator

    ReportGenerator -->|"Evaluation JSON Response"| AIDispatcher
    AIDispatcher -->|"Persist AI Findings"| MongoDB
    AIDispatcher -->|"Log Status Transition"| PostgresDB
    AIDispatcher -->|"Real-time Feedback"| ReactApp
```

### Document Verification Pipeline

```mermaid
flowchart TD
    Start(["College Submits PDF Document"]) --> Ingest["Ingestion & Validation (Multer: 15MB, PDF Only)"]
    Ingest --> Meta["Persist Document Metadata in PostgreSQL"]
    Meta --> Dispatch["Stream PDF to ML Microservice (FastAPI /evaluate)"]
    Dispatch --> PDFProc["PDF Processing & Digital Text Short-Circuit (PyMuPDF)"]
    PDFProc --> OCR["OCR Text Extraction (Tesseract 5.x)"]
    OCR --> Clean["Text Cleaning & Normalization"]
    Clean --> RuleEngine{"AICTE Rule Verification Engine"}

    RuleEngine --> Classify["Document Classification (ML / Heuristic)"]
    RuleEngine --> SigDetect["Signature Detection & Stroke Verification"]
    RuleEngine --> StampDetect["Official Rubber Stamp / Seal Detection"]

    Classify --> Aggregator["Report Aggregator & Anomaly Scorer"]
    SigDetect --> Aggregator
    StampDetect --> Aggregator

    Aggregator --> JSONOutput["Structured AI Verification Report (JSON)"]
    JSONOutput --> FastAPIReply["FastAPI Response (HTTP 200)"]
    FastAPIReply --> PersistMongo[("MongoDB: Save AiEvaluation Report")]
    FastAPIReply --> PersistSQL[("PostgreSQL: Update application_status_logs")]
    PersistSQL --> RealTimeUI(["Instant Status Update on Evaluator & College Dashboard"])
```

---

## 🛠️ Full-Stack Development (FSD) Roadmap & Tech Stack

<p align="center">
  <img src="frontend/src/assets/FSD_ROADMAP.jpg" alt="FSD Roadmap" width="800" />
</p>

### Layered Tech Stack Architecture

```mermaid
flowchart LR
    subgraph Presentation["1. Frontend & Client Tier"]
        HTML["HTML5"] --> CSS["CSS3 / Responsive UI"]
        CSS --> JS["JavaScript / React 18"]
        JS --> Tests["Unit Testing & Dashboards"]
    end

    subgraph Backend["2. Application & API Tier"]
        Node["Node.js & Express.js"]
        Auth["JWT & RBAC Security"]
        Upload["Multer Multi-part Handler"]
        Prisma["Prisma ORM (SQL)"]
        Mongoose["Mongoose ODM (NoSQL)"]
    end

    subgraph AI["3. Intelligence & ML Tier"]
        FastAPI["FastAPI Microservice"]
        PyMuPDF["PyMuPDF (fitz) Engine"]
        Tesseract["Tesseract OCR Engine"]
        DocAI["AICTE Rule & Anomaly Detector"]
    end

    subgraph Persistence["4. Storage & Production Tier"]
        Postgres[("PostgreSQL")]
        Mongo[("MongoDB")]
        Docker["Docker Containers"]
        CI["GitHub Actions CI/CD"]
    end

    Presentation <-->|"REST APIs"| Backend
    Backend <-->|"HTTP / Multipart Stream"| AI
    Backend --> Persistence
    AI --> Persistence
```

---

## 🗺️ Project Roadmap & Execution Timeline

For complete details on current milestones and engineering plans, see [ROADMAP.md](ROADMAP.md).

### High-Level Milestone Phases
<p align="center">
  <img src="frontend/src/assets/PROJECT_ROADMAP.jpg" alt="ANUMATI Project Roadmap" width="550" />
</p>

### Detailed Timeline & Module Schedule
<p align="center">
  <img src="frontend/src/assets/COMPLETE_TIMELINE.jpg" alt="ANUMATI Complete Timeline" width="700" />
</p>

---

## 📁 Project Structure

The project is structured as a monorepo with distinct services. Below is a breakdown of the directory structure:

```plaintext
/
├── backend/
│   ├── api/             # API routes (e.g., Express routes)
│   ├── prisma/
│   │   ├── migrations/
│   │   └── schema.prisma
│   ├── scripts/
│   │   └── test-db.js
│   ├── src/
│   │   ├── config/          # Configuration files (db, auth)
│   │   │   ├── db.js        # Prisma client (SQL)
│   │   │   └── mongo.js     # MongoDB connection setup
│   │   ├── controllers/     # Route handlers
│   │   ├── generated/
│   │   ├── middleware/      # Authentication (JWT), upload, error handling
│   │   ├── services/        # Business logic & AI dispatcher
│   │   ├── models/          # MongoDB Schemas
│   │   │   ├── AiEvaluation.js
│   │   │   └── DynamicApplicationForm.js
│   │   └── server.js
│   ├── .env.example
│   ├── package-lock.json
│   ├── package.json
│   └── prisma.config.ts
│
├── frontend/
│   ├── public/
│   │   ├── dashboard.html
│   │   └── index.html
│   ├── src/
│   │   ├── assets/          # Architecture diagrams, logos, roadmap assets
│   │   │   ├── AICTE.png
│   │   │   ├── COMPLETE_TIMELINE.jpg
│   │   │   ├── FSD_ROADMAP.jpg
│   │   │   ├── PROJECT_ARCHITECTURE.jpg
│   │   │   └── PROJECT_ROADMAP.jpg
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page-level components
│   │   ├── services/        # API communication
│   │   ├── App.js           # Main application component
│   │   ├── App.jsx
│   │   └── index.js
│   ├── home.html
│   ├── package-lock.json
│   ├── webpack.config.js
│   └── package.json
│
├── ml/
│   ├── app.py               # FastAPI server exposing /evaluate
│   ├── notebooks/           # Jupyter notebooks for EDA
│   ├── src/
│   │   ├── ocr/             # OCR logic
│   │   ├── signature/       # Signature & stamp verification logic
│   │   └── anomaly/         # Anomaly detection & rule engine
│   ├── docs/                # Benchmark & model architecture evaluations
│   ├── ml.py
│   └── requirements.txt
│
├── .github/
│   └── workflows/           # CI/CD workflows
├── .gitignore
├── CHANGELOG.md
├── README.md
├── ROADMAP.md
├── SECURITY.md
└── VERSION.md
```

---

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed on your local machine:
*   [Node.js](https://nodejs.org/) (v18.x or higher)
*   [Python](https://www.python.org/) (v3.9.x or higher, preferably 3.11–3.13)
*   [Docker](https://www.docker.com/products/docker-desktop/) (for running databases)
*   [Git](https://git-scm.com/)
*   [MongoDB](https://www.mongodb.com/try/download/community) (Local installation via Compass/Docker, or a free cloud cluster via MongoDB Atlas)
*   [PostgreSQL](https://www.postgresql.org/) (Local installation or Docker container)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Harsh-Bajpai-1194/ANUMATI.git
    cd ANUMATI
    ```

2.  **Set up Databases:**
    1. Ensure you have **PostgreSQL** running locally (or via Docker) for relational data.
    2. Ensure you have **MongoDB** running locally, or create a free shared cluster on MongoDB Atlas for unstructured data.
    3. Copy the example environment variables file:
       ```bash
       cp backend/.env.example backend/.env
       ```
    4. Update `DATABASE_URL` (PostgreSQL) and `MONGODB_URI` (MongoDB) in `backend/.env` with your connection strings.
    5. Run the Prisma migrations to set up the PostgreSQL schema:
       ```bash
       cd backend
       npx prisma migrate dev
       cd ..
       ```

3.  **Install Dependencies:**
    Install dependencies for each service from the root directory:
    ```bash
    # Install backend dependencies
    cd backend && npm install && cd ..

    # Install frontend dependencies
    cd frontend && npm install && cd ..

    # Install ML service dependencies
    cd ml && pip install -r requirements.txt && cd ..
    ```

4.  **Environment Variables:**
    Each service (`backend`, `frontend`, `ml`) requires its own `.env` file for configuration. Check `.env.example` in each directory to document the required variables.

5.  **Running the Services:**
    ```bash
    # Terminal 1: Backend Server (Port 5000)
    cd backend && npm run dev

    # Terminal 2: ML Microservice (Port 8000)
    cd ml && uvicorn app:app --host 0.0.0.0 --port 8000 --reload

    # Terminal 3: Frontend Development Server
    cd frontend && npm start
    ```

> [!NOTE]
> **Server Execution & Graceful Disconnect:** The backend server maintains active connections to both PostgreSQL and MongoDB simultaneously. It includes a graceful shutdown protocol. To stop the server cleanly and disconnect the databases without hanging ports, always use `Ctrl+C`.
