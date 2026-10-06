FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2 and gunicorn
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Optional: create tables on image build (we'll also do it on runtime)
# RUN python -c "import db; db.init_db()"

EXPOSE 8000
