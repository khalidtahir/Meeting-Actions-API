FROM python:3.11-slim

WORKDIR /app

RUN mkdir -p /app/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app contents so that "from config" etc. resolve (run from /app)
COPY app/ ./

# SQLite in /app/data (mount volume in compose)
ENV DATABASE_URL=sqlite:////app/data/meetings.db

EXPOSE 8000

# Run from /app so config, database, routes, etc. are on the path
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
