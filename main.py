from fastapi import FastAPI
from contextlib import asynccontextmanager
from adapters.db import Database
from config import Config

# Ensure database directory exists
Config.ensure_db_directory()

# Global database instance
db = Database(Config.DATABASE_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization."""
    # Initialize database on startup
    db.get_connection()  # This will create schema if needed
    print("Database initialized successfully")
    
    yield
    
    # Cleanup on shutdown
    db.close()
    print("Database connection closed")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok", "system": "Server is running!"}


@app.get("/")
def read_root():
    return {"Hello": "from FastAPI"}


@app.get("/db/status")
def database_status():
    """Check database connection status."""
    try:
        conn = db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM recipes")
        recipe_count = cursor.fetchone()['count']
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM shopping_lists")
        list_count = cursor.fetchone()['count']
        
        return {
            "status": "connected",
            "database_path": db.db_path,
            "recipes_count": recipe_count,
            "shopping_lists_count": list_count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
