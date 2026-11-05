from sqlalchemy import text

from app.core.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        version = result.scalar()

        print("Successfully connected to PostgreSQL!")
        print(f"Database version: {version}")

except Exception as error:
    print("Database connection failed!")
    print(f"Error: {error}")

finally:
    engine.dispose()