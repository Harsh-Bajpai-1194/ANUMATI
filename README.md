# ANUMATI - AI supported AICTE Approval process portal v1.0.0  
  
## Project Overview  

* **Core, server, API, security, authentication:** This portal requires a highly secure, role-based backend architecture. You will need to build robust APIs to handle heavy document uploads and implement strict authentication (like JWT) because you are dealing with official government and institutional data.
* **SQL and MongoDB both:** This is the perfect use case for a hybrid database approach. You can use SQL for structured, relational data (user accounts, college hierarchies, strict approval statuses) and MongoDB to store unstructured, dynamic data (varied institutional application forms, JSON logs, and AI evaluation outputs).
* **Data cleaning, EDA, Basic ML & TensorFlow:** The AI component focuses on automated document verification. The ML side of the team will need to perform extensive Data Cleaning and Exploratory Data Analysis (EDA) on historical AICTE documents. From there, TensorFlow can be used to build models that automatically read text (OCR), verify signatures, or detect anomalies in the uploaded PDFs to speed up the approval process.
* **Frontend & Backend:** The web team will build the full lifecycle—a clean frontend dashboard for colleges to track their approval progress in real-time, powered by the backend server routing the ML results.

## Project Structure

The project is structured as a monorepo with distinct services. Below is a more detailed breakdown of the intended directory structure:

```plaintext
/
├── backend/
│   ├── src/
│   │   ├── api/         # API routes (e.g., Express routes)
│   │   ├── config/      # Configuration files (db, auth)
│   │   ├── controllers/ # Route handlers
│   │   ├── middleware/  # Authentication (JWT), error handling
│   │   ├── models/      # Database schemas/models (SQL)
│   │   └── services/    # Business logic
│   ├── .env.example
│   └── package.json
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── assets/      # Images, fonts, etc.
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page-level components
│   │   ├── services/    # API communication
│   │   └── App.js       # Main application component
│   ├── .env.example
│   └── package.json
│
├── ml/
│   ├── notebooks/       # Jupyter notebooks for EDA
│   ├── src/
│   │   ├── ocr/         # OCR logic
│   │   ├── signature/   # Signature verification logic
│   │   └── anomaly/     # Anomaly detection logic
│   ├── .env.example
│   └── requirements.txt
│
├── .github/
│   └── workflows/       # CI/CD workflows
│
├── .gitignore
└── CHANGELOG
└── README.md
└── requirements.txt
└── VERSION
```

## Getting Started

### Prerequisites

Ensure you have the following installed on your local machine:
*   [Node.js](https://nodejs.org/) (v18.x or higher)
*   [Python](https://www.python.org/) (v3.9.x or higher)
*   [Docker](https://www.docker.com/products/docker-desktop/) (for running databases)
*   [Git](https://git-scm.com/)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ANUMATI.git
    cd ANUMATI
    ```

2.  **Set up Databases:**
    This project uses SQL (e.g., PostgreSQL) and MongoDB. The easiest way to run them is via Docker. You can create a `docker-compose.yml` file to manage them.

3.  **Install Dependencies:**
    Install dependencies for each service from the root directory.
    ```bash
    # Install backend dependencies
    cd backend && npm install && cd ..

    # Install frontend dependencies
    cd frontend && npm install && cd ..

    # Install ML service dependencies
    cd ml && pip install -r requirements.txt && cd ..
    ```

4.  **Environment Variables:**
    Each service (`backend`, `frontend`, `ml`) will require its own `.env` file for configuration. You should create `.env.example` files in each directory to document the required variables.