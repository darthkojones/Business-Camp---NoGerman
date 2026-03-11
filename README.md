# Harmonized Tariff Codes Classification Tool

<a className="gh-badge" href="https://datahub.io/core/harmonized-system"><img src="https://badgen.net/badge/icon/View%20on%20datahub.io/orange?icon=https://datahub.io/datahub-cube-badge-icon.svg&label&scale=1.25" alt="badge" /></a>

This project provides an internal tool for viewing unmatched SAP export materials and the customs tariff data. 

## Features
- **Frontend**: SvelteKit application using TailwindCSS and Flowbite-Svelte. Currently displays a table with all products available in database.
- **Backend**: FastAPI Python backend, supplying basic data endpoints (`/materials`, `/tariffs`).
- **Database**: Containerized PostgreSQL database.
- **Data Seeding**: Automatically populates the PostgreSQL database from `data/Export_SAP_200MM.csv` and `data/CostumsData.csv` on startup.

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