import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("USER_MAX_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("USER_MAX_DATABASE_URL environment variable is not set")

# Normalize SSL params for psycopg2
try:
    parsed = urlparse(DATABASE_URL)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    ssl_val = (q.get("ssl") or "").strip().lower()
    sslmode = (q.get("sslmode") or "").strip().lower()
    changed = False
    if "channel_binding" in q:
        q.pop("channel_binding", None)
        changed = True
    if ssl_val:
        if ssl_val in {"true", "1", "require"} and not sslmode:
            q["sslmode"] = "require"
            changed = True
        q.pop("ssl", None)
        changed = True
    if changed:
        DATABASE_URL = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
except Exception:
    pass

engine_args = {"echo": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Drop and create all tables
#Base.metadata.drop_all(bind=engine)
#Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
