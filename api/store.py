import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from api import config


@contextmanager
def connection():
    config.DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.DATA / "tsi.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init():
    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, status TEXT NOT NULL, metadata TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, error TEXT, duration REAL, sha256 TEXT, result TEXT)")


        columns = {row["name"] for row in db.execute("PRAGMA table_info(analyses)")}
        if "owner_id" not in columns:
            db.execute("ALTER TABLE analyses ADD COLUMN owner_id TEXT")
        db.execute("CREATE INDEX IF NOT EXISTS analyses_owner ON analyses(owner_id)")
        db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS auth_limits (key TEXT PRIMARY KEY, started REAL NOT NULL, attempts INTEGER NOT NULL)")


def create(metadata, owner_id):
    now = time.time()
    job_id = str(uuid.uuid4())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] >= config.MAX_JOBS:
            raise RuntimeError("storage_limit")
        if db.execute("SELECT COUNT(*) FROM analyses WHERE owner_id=?", (owner_id,)).fetchone()[0] >= 5:
            raise RuntimeError("account_analysis_limit")
        db.execute("INSERT INTO analyses (id,status,metadata,created,updated,owner_id) VALUES (?,?,?,?,?,?)", (job_id, "awaiting_upload", json.dumps(metadata), now, now, owner_id))
    return job_id


def get(job_id):
    with connection() as db:
        row = db.execute("SELECT * FROM analyses WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["metadata"] = json.loads(item["metadata"])
    item["result"] = json.loads(item["result"]) if item["result"] else None
    return item


def transition(job_id, previous, status, **fields):
    allowed = {"error", "duration", "sha256", "result"}
    if not set(fields) <= allowed:
        raise ValueError("Invalid update")
    if "result" in fields:
        fields["result"] = json.dumps(fields["result"])
    values = {"status": status, "updated": time.time(), **fields}
    with connection() as db:
        sql = ", ".join(f"{key}=?" for key in values)
        return db.execute(f"UPDATE analyses SET {sql} WHERE id=? AND status=?", (*values.values(), job_id, previous)).rowcount == 1


def claim():
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id FROM analyses WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            return None
        db.execute("UPDATE analyses SET status='processing', updated=? WHERE id=?", (time.time(), row["id"]))
        return row["id"]


def maintenance():
    now = time.time()
    with connection() as db:
        db.execute("UPDATE analyses SET status='failed', error='interrupted', updated=? WHERE status IN ('uploading','processing') AND updated<?", (now, now - 1800))
        rows = db.execute("SELECT id FROM analyses WHERE created<? AND status NOT IN ('uploading','processing')", (now - config.RETENTION_SECONDS,)).fetchall()
        for row in rows:
            (config.DATA / f"{row['id']}.mp4").unlink(missing_ok=True)
            db.execute("DELETE FROM analyses WHERE id=?", (row["id"],))
