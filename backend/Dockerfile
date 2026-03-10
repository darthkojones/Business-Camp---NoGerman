FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for pandas & psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The application code will be mounted via volume in docker-compose for live-reload
# But we copy it here as a fallback/default
COPY . .

# Setting the command to execute seed script and then run FastAPI
CMD bash -c "python seed.py && fastapi dev main.py --host 0.0.0.0 --port 8000"
