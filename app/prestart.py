# One-time database initialization to avoid concurrent DDL across workers
from app.infrastructure.db import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized (or already up-to-date)")
