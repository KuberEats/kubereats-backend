from .database import engine

def init_db():
    # Database initialization disabled for remote shared DB.
    # Schema management should be handled via migrations (Alembic) or by the DB admin.
    print("Database connection check only. No schema changes will be performed.")
    
    # We can still test the connection if we want
    try:
        with engine.connect() as conn:
            print("Successfully connected to the remote database.")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")

if __name__ == "__main__":
    init_db()
