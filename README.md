# Animal Vocalization Capture & Analysis Platform

A secure, ML-powered web platform enabling researchers to capture, store, analyze, and interpret animal vocalizations. The system provides translation and behavioral tagging with robust data protection, quality controls, and strict access management.

---

## Features

- **User Authentication & RBAC**: OAuth2/JWT-based login, role-based access control for researchers and admins.
- **Audio Upload**: Capture/upload animal vocalizations (WAV, MP3, FLAC, max 50MB) for supported species.
- **Secure Storage**: Audio files encrypted at rest (AES-256) in S3/MinIO; metadata in PostgreSQL.
- **ML Analysis**: Asynchronous translation and behavioral tagging (≥80% accuracy), quality checks for noise/overlap.
- **Results Dashboard**: View metadata, translation, tags, accuracy, and quality flags for each vocalization.
- **Quality Control**: Flag noisy/overlapping audio, provide partial results.
- **API Endpoints**: Upload, analysis trigger/result, supported species listing.
- **Rate Limiting**: 100 requests/min/user.
- **Audit Logging**: Comprehensive logging and audit trails for all data access.
- **Scalable Architecture**: Dockerized, supports horizontal scaling.

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Celery, Redis, PostgreSQL, S3/MinIO
- **Frontend**: React (TypeScript)
- **ML**: PyTorch/TensorFlow (integrated via Celery worker)
- **Security**: OAuth2/JWT, AES-256 encryption, TLS 1.2+
- **Containerization**: Docker, docker-compose
- **Testing**: pytest (backend), jest (frontend)
- **CI/CD**: GitHub Actions

---

## Directory Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── storage.py
│   │   ├── ml_worker.py
│   │   └── routes/
│   │       ├── audio_upload.py
│   │       ├── audio_analysis.py
│   │       └── species.py
│   ├── Dockerfile
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── index.css
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── upload/
│   │   └── analysis/
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── README.md
```

---

## Setup & Usage

### Prerequisites

- Docker & docker-compose
- Node.js (for frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/animal-vocalization-platform.git
cd animal-vocalization-platform
```

### 2. Environment Variables

- Copy `.env.example` to `.env` in `frontend/` and set `REACT_APP_API_URL`.
- Backend secrets (AES_KEY, AES_IV, S3 credentials) are set in `docker-compose.yml` for local dev. Change for production!

### 3. Build & Start All Services

```bash
docker-compose up --build
```

- **Backend API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (user/pass: minioadmin)
- **PostgreSQL**: localhost:5432 (user/pass: postgres)
- **Redis**: localhost:6379

### 4. Frontend Development

```bash
cd frontend
npm install
npm start
```

- Access UI at http://localhost:3000

### 5. Database Migration

- Use Alembic or SQLAlchemy to create tables if not auto-created.
- Example (from within backend container):

```bash
docker-compose exec backend python
>>> from app.models import Base
>>> from sqlalchemy import create_engine
>>> engine = create_engine("postgresql+psycopg2://postgres:postgres@db:5432/animal_vocalization")
>>> Base.metadata.create_all(engine)
```

---

## API Overview

- **POST /api/audio/upload**: Upload audio file (WAV/MP3/FLAC, ≤50MB, supported species)
- **GET /api/audio/supported-formats**: List supported formats
- **GET /api/audio/supported-species**: List supported species
- **POST /api/analysis/trigger/{audio_file_id}**: Trigger ML analysis
- **GET /api/analysis/result/{audio_file_id}**: Get analysis result
- **GET /api/species/**: List supported species

All endpoints require OAuth2/JWT authentication.

---

## Security Notes

- All audio and metadata encrypted at rest and in transit.
- RBAC enforced for all sensitive operations.
- Rate limiting: 100 requests/min/user.
- Input validation and sanitization for all fields.
- Change all demo secrets before production!

---

## Testing

### Backend

```bash
docker-compose exec backend pytest
```

### Frontend

```bash
cd frontend
npm test
```

---

## Troubleshooting

- **MinIO**: Access via http://localhost:9001 (minioadmin/minioadmin)
- **Database**: Ensure `animal_vocalization` DB exists and is migrated.
- **Celery Worker**: Check logs for ML analysis job status.
- **API Docs**: http://localhost:8000/docs

---

## License

MIT License

---

## Maintainers

- [Your Name] (@yourgithub)
- [Your Team/Org]

---

## Contributing

Pull requests welcome! Please see [CONTRIBUTING.md] for guidelines.

---

## Acknowledgements

- FastAPI, React, SQLAlchemy, Celery, MinIO, PostgreSQL, PyTorch/TensorFlow

---