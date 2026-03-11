# Harmonized Tariff Codes Classification Tool

<a className="gh-badge" href="https://datahub.io/core/harmonized-system"><img src="https://badgen.net/badge/icon/View%20on%20datahub.io/orange?icon=https://datahub.io/datahub-cube-badge-icon.svg&label&scale=1.25" alt="badge" /></a>

This project provides an internal tool for viewing unmatched SAP export materials and the customs tariff data. 

## Features
- **Frontend**: SvelteKit application using TailwindCSS and Flowbite-Svelte. Currently displays a table with all products available in database.
- **Backend**: FastAPI Python backend, supplying basic data endpoints (`/materials`, `/tariffs`, `/clusters`).
- **Database**: Containerized PostgreSQL database.
- **Data Seeding**: Automatically populates the PostgreSQL database from `data/Export_SAP_200MM.csv` and `data/CostumsData.csv` on startup.
- **AI-Powered Tariff Matching**: LLM-assisted cluster-to-tariff code matching using OpenAI API for intelligent classification suggestions.

## Getting Started

### Prerequisites
- Docker & Docker Compose

### Running the Application
To run the entire stack (Database, Backend API, Frontend UI), simply run:
```bash
docker compose up --build -d
```

Once the containers are built and the database has been seeded, you can access:
- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

*(Note: Data seeding may take a few seconds on the first run as it loads the CSV files into PostgreSQL).*

### Configuring OpenAI API (Required for AI Matching)

To use the AI-powered tariff matching feature, you need to set up your OpenAI API key:

1. Copy the example environment file:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. Edit `backend/.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-openai-api-key-here
   ```

3. Restart the backend container to apply the changes:
   ```bash
   docker compose restart backend
   ```

### Using the AI Tariff Matching Feature

Once configured, you can use the tariff matching endpoint:

1. **Get all clusters**: `GET http://localhost:8000/clusters`
2. **Get tariff suggestions for a cluster**: `POST http://localhost:8000/clusters/{cluster_id}/suggest-tariffs`

Example using curl:
```bash
# Get all clusters
curl http://localhost:8000/clusters

# Get AI suggestions for cluster CL-001
curl -X POST "http://localhost:8000/clusters/CL-001/suggest-tariffs?model=gpt-4o-mini&use_cache=true"
```

The API will return ranked tariff code suggestions with:
- Tariff code
- Confidence score (0.0 - 1.0)
- Reasoning for the match
- Section information

**Available Models:**
- `gpt-4o-mini` (default, cost-efficient)
- `gpt-4` (higher accuracy, more expensive)
- `gpt-3.5-turbo` (fastest, lowest cost)

## Development Workflow

This project is configured for **Live-Reloading**. You do not need to restart the Docker containers when modifying the code:

- **Frontend Development**: Any changes made inside the `frontend/` directory (e.g., Svelte components, CSS) will automatically trigger a hot-reload in your browser thanks to Vite.
- **Backend Development**: Any changes made inside the `backend/` directory (e.g., FastAPI endpoints, models) will automatically restart the backend server thanks to FastAPI's dev mode.

Both directories are mounted as volumes in the `docker-compose.yml`, syncing your local filesystem with the containers.

**When to Rebuild:**
You only need to rebuild the containers (`docker compose up --build -d`) if you:
- Add a new Python package to `backend/requirements.txt`
- Add a new Node package to `frontend/package.json`
- Change the `Dockerfile` or `docker-compose.yml`