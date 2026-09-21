# ANUMATI Project Roadmap & Execution Plan

**ANUMATI** is an AI-supported portal designed to streamline, automate, and accelerate the AICTE approval process for educational institutions.

---

## 1. Project Current Status Overview

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1: Architecture & Setup** | Monorepo structure, Prisma SQL & MongoDB schemas, config files | **Completed** |
| **Phase 2: Backend APIs** | Routing, upload endpoints, controllers, auth middleware | **In Progress** |
| **Phase 3: Machine Learning & OCR** | PDF text extraction, signature verification, anomaly detection | **Foundational / Notebooks** |
| **Phase 4: Frontend UI & Dashboards**| Upload UI, institute tracking, evaluator dashboard | **In Progress** |
| **Phase 5: E2E Integration & Deploy**| Inter-service communication, CI/CD, production deployment | **Early Stages** |

---

## 2. Immediate Milestone: Option A — End-to-End Document Upload Flow

Establish the vertical pipeline connecting the React frontend upload interface directly to the Express backend with persistent storage and metadata handling.

### Backend Tasks
- [ ] **Dependency Setup**: Install `multer` in `backend/` for multi-part file uploads (`multipart/form-data`).
- [ ] **Upload Middleware (`src/middleware/uploadMiddleware.js`)**:
  - Configure disk storage to `backend/uploads/` with timestamped unique filenames.
  - Strict PDF mimetype validation (`application/pdf`).
  - Size limitation: 15MB max.
- [ ] **Document Controller (`src/controllers/documentController.js`)**:
  - `uploadDocument`: Process uploaded file, build response payload (file ID, path, size, upload timestamp).
  - Provide hook for triggering AI evaluation in Phase 3.
  - `getDocumentStatus`: Fetch document and verification status.
- [ ] **API Routing (`api/routes.js` & `src/server.js`)**:
  - Mount `/api/documents/upload` to the upload controller and middleware.
  - Configure CORS properly to accept requests from frontend dev servers.
  - Error-handling middleware for file size and format violations.

### Frontend Tasks
- [ ] **API Service Layer (`src/services/api.js`)**:
  - Create reusable HTTP service for document upload with `FormData`.
  - Handle upload progress, network errors, and server response mapping.
- [ ] **Upload Component Integration (`src/pages/PdfUploadComponent.jsx`)**:
  - Connect UI upload button to backend `POST /api/documents/upload`.
  - Add upload progress spinner and real-time upload state (`idle`, `uploading`, `success`, `error`).
  - Render server-confirmed uploaded files list with status badges and deletion triggers.

---

## 3. Subsequent Milestone: Option B — Python ML Service Integration

Bridge the Node.js backend with the machine learning and OCR verification pipeline.

### Tasks
- [ ] **Expose ML Service via FastAPI / Flask (`ml/`)**:
  - Create a lightweight Python web service wrapping `ml.py`, OCR, and signature detection models.
  - Define endpoint: `POST /evaluate` receiving PDF path/file and returning structured JSON.
- [ ] **Backend AI Dispatcher**:
  - After a document is uploaded, backend sends an evaluation task to the ML service.
  - Store model findings (OCR confidence, anomaly flags, extracted entities) in MongoDB using the `AiEvaluation` model.
- [ ] **Prisma & MongoDB Linkage**:
  - Link SQL `application_status_logs.mongo_ai_evaluation_ref` with MongoDB document `_id`.

---

## 4. Milestone: Option C — Authentication & Role-Based Access Control (RBAC)

Secure government and institutional data with role segregation.

### Tasks
- [ ] **JWT Auth in Backend**:
  - Endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.
  - Hash passwords using `bcrypt`.
- [ ] **RBAC Middleware**:
  - Roles: `applicant` (Institutions), `evaluator` (AICTE scrutiny committee), `admin`.
- [ ] **Frontend Route Guards**:
  - Store JWT in secure storage/cookies.
  - Protected routes in React Router (`/upload`, `/dashboard`, `/evaluator-view`).

---

## 5. Milestone: Full Dashboards & Verification Review

Provide visibility for both institutions and AICTE evaluators.

### Tasks
- [ ] **Applicant Dashboard (`frontend/src/pages/Dashboard.js`)**:
  - Real-time application stage tracker (Submitted -> AI Checked -> Scrutiny -> Approved/Rejected).
  - Document status and resubmission requests.
- [ ] **Evaluator View (`frontend/src/pages/EvaluatorView.js`)**:
  - Side-by-side view: original uploaded PDF vs. extracted data and anomaly alert tags.
  - Action buttons: Approve, Reject, Return for correction with feedback comments.

---

## 6. Milestone: CI/CD, Containerization & Production Deployment

- [ ] **Dockerization**:
  - Multi-container `docker-compose.yml` (Frontend, Backend, ML Service, PostgreSQL, MongoDB).
- [ ] **CI/CD Pipelines**:
  - Automated linting, test runners, and container builds via `.github/workflows/`.
