# Sweepzy - Civic Impact Platform

> **🚀 Open Source Portfolio Project** - This repository showcases my full-stack development capabilities, system architecture design, and problem-solving approach through a real-world application. Built to demonstrate proficiency in modern Python backends, AI/ML integration, geospatial systems, and scalable architecture patterns for potential collaborators and employers.

Sweepzy is a scalable, full-stack geospatial platform designed to empower communities to identify, verify, and clean up litter using AI-powered image detection. It features a gamified user flow, ML-based litter detection, and a robust admin verification system.

**Live Demo:** https://sweepzy-fe.vercel.com

> **Note:** The frontend repository for this project is currently private due to ongoing client discussions and potential commercialization. The frontend is built with Next.js 14, TypeScript, and TailwindCSS, featuring responsive design, real-time updates, and optimized geospatial visualizations. For job opportunities or collaboration inquiries, please contact me directly to discuss frontend code access.

## System Architecture

The system is built as a distributed application ensuring high availability and low-latency geospatial queries.

### High-Level Design
* **Frontend:** Next.js (React) for server-side rendering and SEO-optimized user dashboards.
* **Backend:** FastAPI (Python) for high-performance async API handling.
* **Database:** PostgreSQL with **PostGIS** extension for spatial indexing (querying "litter near me" in O(log n)).
* **AI/ML:** ONNX-based computer vision models for automated litter detection.
* **Caching:** Redis to cache frequent geospatial reads and user session data.
* **Queue:** Background worker processes for image processing and ML inference.
* **Authentication:** JWT-based auth with role-based access control.

## Tech Stack & Key Features

* **Backend:** Python 3.11, FastAPI, SQLAlchemy (Async), Pydantic
* **ML/AI:** ONNX Runtime, OpenCV, TensorFlow, Scikit-learn, NumPy
* **Frontend:** TypeScript, Next.js 14, TailwindCSS
* **Data:** PostgreSQL (PostGIS), Redis, Alembic (migrations)
* **Authentication:** JWT, PassLib, BCrypt
* **DevOps:** Docker, GitHub Actions (CI), Fly.io
* **Background Tasks:** Redis Queue (RQ), APScheduler

## Getting Started Locally

### Prerequisites
* Docker
* Python 3.11+ (for local development)
* PostgreSQL with PostGIS extension
* Redis server

### Quick Start (Docker)
1.  **Clone the repo:**
    ```bash
    git clone https://github.com/NishalDev/Sweepzy-be.git
    cd Sweepzy-be
    ```

2.  **Environment Setup:**
    Create a `.env` file with your configuration:
    ```bash
    # Database
    DATABASE_URL=postgresql://user:password@localhost:5432/sweepzy
    
    # Redis
    REDIS_URL=redis://localhost:6379
    
    # JWT Secret
    SECRET_KEY=your-secret-key-here
    
    # CORS Origins
    CORS_ORIGINS=http://localhost:3000,https://sweepzy-fe.vercel.com
    ```

3.  **Run with Docker:**
    ```bash
    docker build -t sweepzy .
    docker run -p 8080:8080 --env-file .env sweepzy
    ```
    
4.  **Or run locally:**
    ```bash
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    
    * The API will be available at `http://localhost:8000`
    * Interactive API Documentation at `http://localhost:8000/docs`
    * Alternative API Documentation at `http://localhost:8000/redoc`

## Project Structure

```bash
├── api/                    # API route modules (attendance, badges, cleanup_events, etc.)
├── config/                 # Configuration files (database, settings, logging)
├── database/               # Database session and initialization
├── helpers/                # Utility helpers (mail, SAM service, tokens)
├── middlewares/            # FastAPI middlewares (auth, validation, etc.)
├── models/                 # SQLAlchemy database models
├── scripts/                # Utility scripts (auto upload, coverage analysis, etc.)
├── services/               # Business logic services
├── tasks/                  # Background task definitions
├── templates/              # Email templates
├── utils/                  # Shared utilities (cache, geo, query params)
├── weights/                # ML model weights (ONNX files)
├── alembic/                # Database migration files
├── main.py                 # FastAPI application entry point
├── worker_main.py          # Background worker process
└── requirements.txt        # Python dependencies
```

## Key Features

* **AI-Powered Litter Detection**: Computer vision models for automated litter identification
* **Geospatial Analytics**: PostGIS-powered location-based queries and analysis
* **Gamification**: Points, badges, and leaderboards to encourage community participation
* **Admin Verification**: Robust system for verifying user reports and managing content
* **Background Processing**: Async task processing for image analysis and report generation
* **Role-Based Access**: Comprehensive permission system for different user types
* **Real-time Notifications**: Event-driven notification system

## Testing

This project uses **Pytest** for backend integration testing.

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Database Setup

The project uses PostgreSQL with PostGIS extension. Run these commands to set up your database:

```sql
-- Create database
CREATE DATABASE sweepzy;

# Connect to the database and enable PostGIS
\c sweepzy;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

Then run Alembic migrations:
```bash
alembic upgrade head
```

## Deployment

### Using Fly.io (Recommended)

The project includes a `fly.toml` configuration for easy deployment to Fly.io:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly deploy
```

### Using Docker

```bash
# Build the image
docker build -t sweepzy .

# Run with environment variables
docker run -p 8080:8080 \
  -e DATABASE_URL=your_db_url \
  -e REDIS_URL=your_redis_url \
  -e SECRET_KEY=your_secret_key \
  sweepzy
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `REDIS_URL` | Redis connection string | Yes | - |
| `SECRET_KEY` | JWT signing secret | Yes | - |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | No | `*` |
| `DEBUG` | Enable debug mode | No | `False` |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

**For Commercial Use:** While GPL v3.0 permits commercial use under copyleft terms, this software represents significant intellectual property developed for portfolio demonstration. For proprietary commercial applications or alternative licensing arrangements, please contact the author directly.

## Contact

For employment opportunities, collaboration, or technical inquiries, please reach out:
- **Email:** nishaldevadiga2003@gmail.com
- **Project Support:** team.sweepzy@gmail.com

I'm actively seeking software development opportunities and welcome discussions about this project, my technical approach, or potential roles.