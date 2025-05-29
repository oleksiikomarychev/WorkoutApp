from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable is not set.")
    exit(1)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# SQL statements to make columns nullable
sql_statements = """
ALTER TABLE llm_progressions 
    ALTER COLUMN intensity DROP NOT NULL,
    ALTER COLUMN effort DROP NOT NULL,
    ALTER COLUMN volume DROP NOT NULL;
"""

try:
    # Execute the SQL statements
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text(sql_statements))
    print("Migration applied successfully!")
except Exception as e:
    print(f"Error applying migration: {e}")
    exit(1)
