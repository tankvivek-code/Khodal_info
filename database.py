import sqlite3
import hashlib
import json
import os
import re
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

try:
    import pymongo
    import bson
    from bson.binary import Binary
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

# ---------------------------------------------------------------------------
# Environment & Configuration
# ---------------------------------------------------------------------------
def load_env_vars():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and not os.environ.get(k):
                            os.environ[k] = v
        except Exception:
            pass

load_env_vars()

DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.environ.get("DB_PATH") or os.path.join(DATA_DIR, "khodal_office.db")

MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "khodal_office").strip()

mongo_client = None
mongo_db = None
USE_MONGODB = False

def init_mongo_connection(uri: Optional[str] = None) -> bool:
    global mongo_client, mongo_db, USE_MONGODB, MONGODB_URI
    target_uri = (uri or MONGODB_URI or "").strip()
    if not target_uri or "<db_password>" in target_uri or not PYMONGO_AVAILABLE:
        USE_MONGODB = False
        return False
    try:
        client = pymongo.MongoClient(target_uri, serverSelectionTimeoutMS=3500)
        client.admin.command('ping')
        mongo_client = client
        mongo_db = client.get_database(MONGODB_DB_NAME)
        USE_MONGODB = True
        MONGODB_URI = target_uri
        print(f"🟢 Connected to MongoDB Atlas Cloud Database ({MONGODB_DB_NAME})!")
        return True
    except Exception as e:
        print(f"⚠️ Could not connect to MongoDB Atlas ({e}). Using local SQLite.")
        USE_MONGODB = False
        return False

def get_database_status() -> Dict[str, Any]:
    global USE_MONGODB, MONGODB_URI
    cluster = "Cluster0 (cluster0.nl4cir6.mongodb.net)"
    waiting_pw = "<db_password>" in MONGODB_URI or not MONGODB_URI
    return {
        "engine": "mongodb" if USE_MONGODB else "sqlite",
        "mongodb_connected": USE_MONGODB,
        "mongodb_cluster": cluster,
        "waiting_for_password": waiting_pw,
        "db_name": MONGODB_DB_NAME if USE_MONGODB else "khodal_office.db",
        "local_db_path": DB_PATH
    }

def configure_mongodb_password(password: str) -> Tuple[bool, str]:
    global MONGODB_URI
    if not password or not password.strip():
        return False, "Password cannot be empty."
    encoded_pw = urllib.parse.quote_plus(password.strip())
    new_uri = f"mongodb+srv://tankvivek65_db_user:{encoded_pw}@cluster0.nl4cir6.mongodb.net/?compressors=zlib"
    success = init_mongo_connection(new_uri)
    if success:
        # Save to .env
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"# MongoDB Atlas Cloud Database Connection URI\n")
                f.write(f"MONGODB_URI={new_uri}\n")
                f.write(f"MONGODB_DB_NAME={MONGODB_DB_NAME}\n")
        except Exception:
            pass
        # Ensure collections & indexes
        init_db()
        return True, "Successfully connected to MongoDB Atlas!"
    else:
        return False, "Failed to connect to MongoDB Atlas with that password. Please verify credentials."

# ---------------------------------------------------------------------------
# SQLite Connection Helper
# ---------------------------------------------------------------------------
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

def normalize_date_for_db(val: Any) -> str:
    if not val:
        return datetime.now().strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s or s == "-" or s.lower() == "nan":
        return ""
    m1 = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m1:
        return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m2:
        y = m2.group(1)
        p1 = int(m2.group(2))
        p2 = int(m2.group(3))
        if p2 == 10 and 1 <= p1 <= 12:
            return f"{y}-10-{p1:02d}"
        if p2 == 11 and 1 <= p1 <= 12:
            return f"{y}-11-{p1:02d}"
        return f"{y}-{p1:02d}-{p2:02d}"
    return s[:10]

# ---------------------------------------------------------------------------
# MongoDB Sequence Counter
# ---------------------------------------------------------------------------
def get_next_sequence_mongo(counter_name: str) -> int:
    if not USE_MONGODB or mongo_db is None:
        return 1
    doc = mongo_db["counters"].find_one_and_update(
        {"_id": counter_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return int(doc["seq"])

# ---------------------------------------------------------------------------
# Password Hashing & Users
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"

def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    clean_user = username.strip().lower()
    
    # 1. MongoDB check if active
    if USE_MONGODB and mongo_db is not None:
        try:
            user = mongo_db["users"].find_one({"username": clean_user, "is_active": 1})
            if user:
                parts = user["password_hash"].split(":")
                if len(parts) == 2:
                    salt, stored_hash = parts
                    check_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
                    if check_hash == stored_hash:
                        now = datetime.now().isoformat()
                        mongo_db["users"].update_one({"id": user["id"]}, {"$set": {"last_login": now}})
                        res = dict(user)
                        res.pop("_id", None)
                        res.pop("password_hash", None)
                        return res
        except Exception as e:
            print("MongoDB auth error:", e)
            
    # 2. SQLite fallback
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (clean_user,))
        user = cursor.fetchone()
        if not user:
            return None
        parts = user["password_hash"].split(":")
        if len(parts) != 2:
            return None
        salt, stored_hash = parts
        check_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        if check_hash == stored_hash:
            now = datetime.now().isoformat()
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user["id"]))
            conn.commit()
            return {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "created_at": user["created_at"],
                "last_login": now
            }
    return None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean_user = username.strip().lower()
    if USE_MONGODB and mongo_db is not None:
        try:
            u = mongo_db["users"].find_one({"username": clean_user, "is_active": 1}, {"_id": 0, "password_hash": 0})
            if u:
                return dict(u)
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, is_active, created_at, last_login FROM users WHERE username = ?", (clean_user,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_master_user(username: str, password: str, full_name: Optional[str] = None, role: str = "master") -> Dict[str, Any]:
    clean_user = username.strip().lower()
    pw_hash = hash_password(password)
    display_name = full_name.strip() if full_name and full_name.strip() else f"{clean_user.capitalize()} (Master)"
    now = datetime.now().isoformat()
    
    if USE_MONGODB and mongo_db is not None:
        existing = mongo_db["users"].find_one({"username": clean_user})
        if existing:
            mongo_db["users"].update_one(
                {"username": clean_user},
                {"$set": {"password_hash": pw_hash, "full_name": display_name, "role": role, "is_active": 1, "last_login": now}}
            )
            u = mongo_db["users"].find_one({"username": clean_user}, {"_id": 0, "password_hash": 0})
            return dict(u)
        new_id = get_next_sequence_mongo("user_id")
        user_doc = {
            "id": new_id,
            "username": clean_user,
            "password_hash": pw_hash,
            "full_name": display_name,
            "role": role,
            "is_active": 1,
            "created_at": now,
            "last_login": None
        }
        mongo_db["users"].insert_one(user_doc)
        res = dict(user_doc)
        res.pop("_id", None)
        res.pop("password_hash", None)
        return res
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                full_name = excluded.full_name,
                role = excluded.role,
                is_active = 1
        """, (clean_user, pw_hash, display_name, role, now))
        conn.commit()
        cursor.execute("SELECT id, username, full_name, role, is_active, created_at, last_login FROM users WHERE username = ?", (clean_user,))
        return dict(cursor.fetchone())

def get_all_master_users() -> List[Dict[str, Any]]:
    if USE_MONGODB and mongo_db is not None:
        try:
            users = list(mongo_db["users"].find({"is_active": 1}, {"_id": 0, "password_hash": 0}).sort("id", 1))
            if users:
                return users
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, is_active, created_at, last_login FROM users WHERE is_active = 1 ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

def delete_master_user(user_id: int) -> bool:
    if USE_MONGODB and mongo_db is not None:
        try:
            total_active = mongo_db["users"].count_documents({"is_active": 1})
            if total_active <= 1:
                return False
            res = mongo_db["users"].update_one({"id": user_id}, {"$set": {"is_active": 0}})
            return res.modified_count > 0
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        if cursor.fetchone()[0] <= 1:
            return False
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def create_user_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    now = datetime.now()
    expires_at = (now + timedelta(days=30)).isoformat()
    if USE_MONGODB and mongo_db is not None:
        try:
            session_id = get_next_sequence_mongo("session_id")
            mongo_db["user_sessions"].insert_one({
                "id": session_id,
                "user_id": user_id,
                "session_token": token,
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "is_active": 1
            })
            return token
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_sessions (user_id, session_token, created_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (user_id, token, now.isoformat(), expires_at))
        conn.commit()
    return token

def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    now = datetime.now().isoformat()
    if USE_MONGODB and mongo_db is not None:
        try:
            sess = mongo_db["user_sessions"].find_one({"session_token": token, "is_active": 1, "expires_at": {"$gt": now}})
            if sess:
                u = mongo_db["users"].find_one({"id": sess["user_id"], "is_active": 1}, {"_id": 0, "password_hash": 0})
                if u:
                    return dict(u)
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.role, u.is_active, u.created_at, u.last_login
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.is_active = 1 AND s.expires_at > ? AND u.is_active = 1
        """, (token, now))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_user_session(token: str) -> bool:
    if not token:
        return False
    if USE_MONGODB and mongo_db is not None:
        try:
            res = mongo_db["user_sessions"].update_one({"session_token": token}, {"$set": {"is_active": 0}})
            return res.modified_count > 0
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE session_token = ?", (token,))
        conn.commit()
        return cursor.rowcount > 0

# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------
def init_db():
    # 1. Try connecting to MongoDB Atlas
    init_mongo_connection()
    
    if USE_MONGODB and mongo_db is not None:
        try:
            # Ensure MongoDB indexes
            mongo_db["office_records"].create_index([("id", 1)], unique=True)
            mongo_db["office_records"].create_index([("service_type", 1)])
            mongo_db["office_records"].create_index([("record_date", -1)])
            mongo_db["office_records"].create_index([("normalized_mobile", 1)])
            mongo_db["office_records"].create_index([("id_number", 1)])
            mongo_db["office_records"].create_index([("file_id", 1)])
            
            mongo_db["uploaded_files"].create_index([("id", 1)], unique=True)
            mongo_db["uploaded_files"].create_index([("uploaded_at", -1)])
            
            mongo_db["users"].create_index([("id", 1)], unique=True)
            mongo_db["users"].create_index([("username", 1)], unique=True)
            
            mongo_db["user_sessions"].create_index([("session_token", 1)], unique=True)
            mongo_db["counters"].create_index([("_id", 1)], unique=True)
            
            # Default users
            if mongo_db["users"].count_documents({}) == 0:
                create_master_user("manish", "manish@7575", "Manish (Master Admin)", "master")
                create_master_user("admin", "admin@7575", "Admin User", "admin")
            print("✓ MongoDB Atlas collections and indexes initialized!")
        except Exception as e:
            print("MongoDB Atlas index initialization error:", e)

    # 2. Always initialize SQLite schema as robust fallback
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'master',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                service_type TEXT NOT NULL,
                file_date TEXT,
                stored_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                row_count INTEGER DEFAULT 0,
                sheet_names TEXT,
                file_blob BLOB,
                uploaded_at TEXT NOT NULL,
                status TEXT DEFAULT 'processed',
                uploaded_by TEXT DEFAULT 'manish',
                user_id INTEGER
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS office_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                service_type TEXT NOT NULL,
                record_date TEXT NOT NULL,
                name TEXT NOT NULL,
                mobile TEXT,
                normalized_mobile TEXT,
                id_number TEXT,
                pan_type TEXT,
                status TEXT DEFAULT 'Completed',
                total_amt REAL DEFAULT 0.0,
                fee_amt REAL DEFAULT 0.0,
                remark TEXT,
                is_baki INTEGER DEFAULT 0,
                extra_data TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT DEFAULT 'manish',
                user_id INTEGER,
                source_file TEXT,
                FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_service_date ON office_records(service_type, record_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_mobile ON office_records(normalized_mobile);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_id_number ON office_records(id_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_name ON office_records(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_file ON office_records(file_id);")
        
        # Default SQLite users
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute("INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) VALUES (?, ?, ?, 'master', 1, ?)",
                           ("manish", hash_password("manish@7575"), "Manish (Master Admin)", now))
            cursor.execute("INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) VALUES (?, ?, ?, 'admin', 1, ?)",
                           ("admin", hash_password("admin@7575"), "Admin User", now))
        conn.commit()

# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------
def add_uploaded_file(filename: str, service_type: str, file_date: str, stored_path: str,
                      file_size: int, row_count: int, sheet_names: Optional[List[str]] = None,
                      file_blob: Optional[bytes] = None, uploaded_by: str = "manish", user_id: Optional[int] = None) -> int:
    now = datetime.now().isoformat()
    sheets_json = json.dumps(sheet_names or [], ensure_ascii=False)
    
    if USE_MONGODB and mongo_db is not None:
        try:
            file_id = get_next_sequence_mongo("file_id")
            doc = {
                "id": file_id,
                "filename": filename,
                "service_type": service_type,
                "file_date": file_date,
                "stored_path": stored_path,
                "file_size": file_size,
                "row_count": row_count,
                "sheet_names": sheets_json,
                "file_blob": Binary(file_blob) if file_blob else None,
                "uploaded_at": now,
                "status": "processed",
                "uploaded_by": uploaded_by,
                "user_id": user_id
            }
            mongo_db["uploaded_files"].insert_one(doc)
            return file_id
        except Exception as e:
            print("MongoDB add_uploaded_file error:", e)
            
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO uploaded_files (
                filename, service_type, file_date, stored_path, file_size,
                row_count, sheet_names, file_blob, uploaded_at, status, uploaded_by, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', ?, ?)
        """, (filename, service_type, file_date, stored_path, file_size, row_count, sheets_json, file_blob, now, uploaded_by, user_id))
        conn.commit()
        return cursor.lastrowid

def get_file_blob(file_id: int) -> Optional[Tuple[bytes, str]]:
    if USE_MONGODB and mongo_db is not None:
        try:
            doc = mongo_db["uploaded_files"].find_one({"id": file_id})
            if doc and doc.get("file_blob"):
                return bytes(doc["file_blob"]), doc.get("filename", f"file_{file_id}.xlsx")
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_blob, filename FROM uploaded_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row and row["file_blob"]:
            return row["file_blob"], row["filename"]
    return None

def update_file_row_count(file_id: int, count: int):
    if USE_MONGODB and mongo_db is not None:
        try:
            mongo_db["uploaded_files"].update_one({"id": file_id}, {"$set": {"row_count": count}})
            return
        except Exception:
            pass
    with get_db_connection() as conn:
        conn.execute("UPDATE uploaded_files SET row_count = ? WHERE id = ?", (count, file_id))
        conn.commit()

def get_all_files() -> List[Dict[str, Any]]:
    if USE_MONGODB and mongo_db is not None:
        try:
            files = list(mongo_db["uploaded_files"].find({}, {"_id": 0, "file_blob": 0}).sort("id", -1))
            return files
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, service_type, file_date, stored_path, file_size, row_count, sheet_names, uploaded_at, status, uploaded_by, user_id FROM uploaded_files ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]

def get_file_by_id(file_id: int) -> Optional[Dict[str, Any]]:
    if USE_MONGODB and mongo_db is not None:
        try:
            f = mongo_db["uploaded_files"].find_one({"id": file_id}, {"_id": 0, "file_blob": 0})
            if f:
                return dict(f)
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, service_type, file_date, stored_path, file_size, row_count, sheet_names, uploaded_at, status, uploaded_by, user_id FROM uploaded_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_uploaded_file(file_id: int) -> bool:
    if USE_MONGODB and mongo_db is not None:
        try:
            mongo_db["office_records"].delete_many({"file_id": file_id})
            res = mongo_db["uploaded_files"].delete_one({"id": file_id})
            sync_db_to_static_files()
            return res.deleted_count > 0
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM office_records WHERE file_id = ?", (file_id,))
        cursor.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))
        conn.commit()
        sync_db_to_static_files()
        return cursor.rowcount > 0

def clear_all_database_records() -> bool:
    if USE_MONGODB and mongo_db is not None:
        try:
            mongo_db["office_records"].delete_many({})
            mongo_db["uploaded_files"].delete_many({})
            mongo_db["counters"].update_many({}, {"$set": {"seq": 0}})
            sync_db_to_static_files()
            return True
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM office_records;")
        cursor.execute("DELETE FROM uploaded_files;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('office_records', 'uploaded_files');")
        conn.commit()
    sync_db_to_static_files()
    return True

# ---------------------------------------------------------------------------
# Record Normalization & Status
# ---------------------------------------------------------------------------
def normalize_record_status(status: Any, remark: Any = "") -> Tuple[str, int]:
    raw_status = str(status or "").strip()
    raw_remark = str(remark or "").strip().upper()
    baki_triggers = ["BAKI", "NOT RECIV", "HOF THI BAKI", "PENDING", "HOLD"]
    is_baki = 1 if any(t in raw_remark for t in baki_triggers) or "baki" in raw_status.lower() else 0
    clean_s = raw_status.lower()
    if "complete" in clean_s or "done" in clean_s or "success" in clean_s:
        return "Completed", is_baki
    if "reject" in clean_s or "failed" in clean_s or "cancel" in clean_s:
        return "Rejected", is_baki
    if "process" in clean_s or "pending" in clean_s or "hold" in clean_s or "active" in clean_s:
        return "InProgress", is_baki
    return ("Completed" if not is_baki else "InProgress"), is_baki

# ---------------------------------------------------------------------------
# Record Insertions & Updates
# ---------------------------------------------------------------------------
def insert_bulk_records(records: List[Dict[str, Any]]) -> int:
    now = datetime.now().isoformat()
    if not records:
        return 0
        
    if USE_MONGODB and mongo_db is not None:
        docs = []
        for r in records:
            raw_mob = str(r.get("mobile") or "").strip()
            norm_mob = "".join(filter(str.isdigit, raw_mob))
            norm_date = normalize_date_for_db(r.get("record_date"))
            status, is_baki = normalize_record_status(r.get("status"), r.get("remark"))
            rec_id = get_next_sequence_mongo("record_id")
            docs.append({
                "id": rec_id,
                "file_id": r.get("file_id"),
                "service_type": (r.get("service_type") or "ucaadhar").strip().lower(),
                "record_date": norm_date,
                "name": str(r.get("name") or "").strip().upper(),
                "mobile": raw_mob,
                "normalized_mobile": norm_mob,
                "id_number": str(r.get("id_number") or "").strip().upper(),
                "pan_type": str(r.get("pan_type") or "").strip().upper(),
                "status": status,
                "total_amt": float(r.get("total_amt") or 0.0),
                "fee_amt": float(r.get("fee_amt") or 0.0),
                "remark": str(r.get("remark") or "").strip(),
                "is_baki": is_baki,
                "extra_data": r.get("extra_data") or {},
                "created_at": now,
                "updated_at": now,
                "created_by": r.get("created_by") or "manish",
                "user_id": r.get("user_id"),
                "source_file": r.get("source_file") or ""
            })
        if docs:
            mongo_db["office_records"].insert_many(docs)
        sync_db_to_static_files()
        return len(docs)
        
    rows = []
    for r in records:
        raw_mob = str(r.get("mobile") or "").strip()
        norm_mob = "".join(filter(str.isdigit, raw_mob))
        norm_date = normalize_date_for_db(r.get("record_date"))
        status, is_baki = normalize_record_status(r.get("status"), r.get("remark"))
        extra_json = json.dumps(r.get("extra_data") or {}, ensure_ascii=False)
        rows.append((
            r.get("file_id"),
            (r.get("service_type") or "ucaadhar").strip().lower(),
            norm_date,
            str(r.get("name") or "").strip().upper(),
            raw_mob,
            norm_mob,
            str(r.get("id_number") or "").strip().upper(),
            str(r.get("pan_type") or "").strip().upper(),
            status,
            float(r.get("total_amt") or 0.0),
            float(r.get("fee_amt") or 0.0),
            str(r.get("remark") or "").strip(),
            is_baki,
            extra_json,
            now,
            now,
            r.get("created_by") or "manish",
            r.get("user_id"),
            r.get("source_file") or ""
        ))
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO office_records (
                file_id, service_type, record_date, name, mobile,
                normalized_mobile, id_number, pan_type, status, total_amt,
                fee_amt, remark, is_baki, extra_data, created_at, updated_at,
                created_by, user_id, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        inserted = cursor.rowcount
    sync_db_to_static_files()
    return inserted

def insert_single_record(record: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    raw_mob = str(record.get("mobile") or "").strip()
    norm_mob = "".join(filter(str.isdigit, raw_mob))
    norm_date = normalize_date_for_db(record.get("record_date"))
    status, is_baki = normalize_record_status(record.get("status"), record.get("remark"))
    svc = (record.get("service_type") or "ucaadhar").strip().lower()
    name = str(record.get("name") or "").strip().upper()
    id_num = str(record.get("id_number") or "").strip().upper()
    pan_type = str(record.get("pan_type") or "").strip().upper()
    total_amt = float(record.get("total_amt") or 0.0)
    fee_amt = float(record.get("fee_amt") or 0.0)
    remark = str(record.get("remark") or "").strip()
    creator = record.get("created_by") or "manish"
    uid = record.get("user_id")
    
    if USE_MONGODB and mongo_db is not None:
        rec_id = get_next_sequence_mongo("record_id")
        doc = {
            "id": rec_id,
            "file_id": record.get("file_id"),
            "service_type": svc,
            "record_date": norm_date,
            "name": name,
            "mobile": raw_mob,
            "normalized_mobile": norm_mob,
            "id_number": id_num,
            "pan_type": pan_type,
            "status": status,
            "total_amt": total_amt,
            "fee_amt": fee_amt,
            "remark": remark,
            "is_baki": is_baki,
            "extra_data": record.get("extra_data") or {},
            "created_at": now,
            "updated_at": now,
            "created_by": creator,
            "user_id": uid,
            "source_file": record.get("source_file") or "Manual Entry"
        }
        mongo_db["office_records"].insert_one(doc)
        sync_db_to_static_files()
        res = dict(doc)
        res.pop("_id", None)
        return res
        
    extra_json = json.dumps(record.get("extra_data") or {}, ensure_ascii=False)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO office_records (
                file_id, service_type, record_date, name, mobile,
                normalized_mobile, id_number, pan_type, status, total_amt,
                fee_amt, remark, is_baki, extra_data, created_at, updated_at,
                created_by, user_id, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("file_id"), svc, norm_date, name, raw_mob,
            norm_mob, id_num, pan_type, status, total_amt,
            fee_amt, remark, is_baki, extra_json, now, now,
            creator, uid, record.get("source_file") or "Manual Entry"
        ))
        conn.commit()
        record_id = cursor.lastrowid
        cursor.execute("SELECT * FROM office_records WHERE id = ?", (record_id,))
        result = dict(cursor.fetchone())
    sync_db_to_static_files()
    return result

def update_single_record(record_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    now = datetime.now().isoformat()
    if USE_MONGODB and mongo_db is not None:
        try:
            update_fields = {"updated_at": now}
            if "name" in data: update_fields["name"] = str(data["name"]).strip().upper()
            if "mobile" in data:
                raw_mob = str(data["mobile"]).strip()
                update_fields["mobile"] = raw_mob
                update_fields["normalized_mobile"] = "".join(filter(str.isdigit, raw_mob))
            if "record_date" in data: update_fields["record_date"] = normalize_date_for_db(data["record_date"])
            if "id_number" in data: update_fields["id_number"] = str(data["id_number"]).strip().upper()
            if "pan_type" in data: update_fields["pan_type"] = str(data["pan_type"]).strip().upper()
            if "status" in data:
                status, is_baki = normalize_record_status(data["status"], data.get("remark", ""))
                update_fields["status"] = status
                update_fields["is_baki"] = is_baki
            if "total_amt" in data: update_fields["total_amt"] = float(data["total_amt"] or 0.0)
            if "fee_amt" in data: update_fields["fee_amt"] = float(data["fee_amt"] or 0.0)
            if "remark" in data: update_fields["remark"] = str(data["remark"]).strip()
            
            mongo_db["office_records"].update_one({"id": record_id}, {"$set": update_fields})
            updated = mongo_db["office_records"].find_one({"id": record_id}, {"_id": 0})
            sync_db_to_static_files()
            return dict(updated) if updated else None
        except Exception:
            pass
            
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fields = []
        params = []
        if "name" in data:
            fields.append("name = ?")
            params.append(str(data["name"]).strip().upper())
        if "mobile" in data:
            raw_mob = str(data["mobile"]).strip()
            norm_mob = "".join(filter(str.isdigit, raw_mob))
            fields.append("mobile = ?")
            fields.append("normalized_mobile = ?")
            params.extend([raw_mob, norm_mob])
        if "record_date" in data:
            fields.append("record_date = ?")
            params.append(normalize_date_for_db(data["record_date"]))
        if "id_number" in data:
            fields.append("id_number = ?")
            params.append(str(data["id_number"]).strip().upper())
        if "pan_type" in data:
            fields.append("pan_type = ?")
            params.append(str(data["pan_type"]).strip().upper())
        if "status" in data:
            status, is_baki = normalize_record_status(data["status"], data.get("remark", ""))
            fields.append("status = ?")
            fields.append("is_baki = ?")
            params.extend([status, is_baki])
        if "total_amt" in data:
            fields.append("total_amt = ?")
            params.append(float(data["total_amt"] or 0.0))
        if "fee_amt" in data:
            fields.append("fee_amt = ?")
            params.append(float(data["fee_amt"] or 0.0))
        if "remark" in data:
            fields.append("remark = ?")
            params.append(str(data["remark"]).strip())
        if not fields:
            return None
        fields.append("updated_at = ?")
        params.append(now)
        params.append(record_id)
        sql = f"UPDATE office_records SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(sql, params)
        conn.commit()
        cursor.execute("SELECT * FROM office_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        res = dict(row) if row else None
    sync_db_to_static_files()
    return res

def delete_single_record(record_id: int) -> bool:
    if USE_MONGODB and mongo_db is not None:
        try:
            res = mongo_db["office_records"].delete_one({"id": record_id})
            sync_db_to_static_files()
            return res.deleted_count > 0
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM office_records WHERE id = ?", (record_id,))
        conn.commit()
        success = cursor.rowcount > 0
    sync_db_to_static_files()
    return success

def update_record_status(record_id: int, status: str) -> Optional[Dict[str, Any]]:
    now = datetime.now().isoformat()
    if USE_MONGODB and mongo_db is not None:
        try:
            rec = mongo_db["office_records"].find_one({"id": record_id})
            if not rec:
                return None
            norm_status, is_baki = normalize_record_status(status, rec.get("remark", ""))
            mongo_db["office_records"].update_one(
                {"id": record_id},
                {"$set": {"status": norm_status, "is_baki": is_baki, "updated_at": now}}
            )
            updated = mongo_db["office_records"].find_one({"id": record_id}, {"_id": 0})
            sync_db_to_static_files()
            return dict(updated) if updated else None
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT remark FROM office_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            return None
        norm_status, is_baki = normalize_record_status(status, row["remark"])
        cursor.execute("""
            UPDATE office_records
            SET status = ?, is_baki = ?, updated_at = ?
            WHERE id = ?
        """, (norm_status, is_baki, now, record_id))
        conn.commit()
        cursor.execute("SELECT * FROM office_records WHERE id = ?", (record_id,))
        res = dict(cursor.fetchone())
    sync_db_to_static_files()
    return res

# ---------------------------------------------------------------------------
# Search & Query Records
# ---------------------------------------------------------------------------
def search_records(
    service_type: Optional[str] = None,
    name: Optional[str] = None,
    mobile: Optional[str] = None,
    id_number: Optional[str] = None,
    query: Optional[str] = None,
    date_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    baki_only: bool = False,
    file_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    # Sanitize
    page = page if isinstance(page, int) and page >= 1 else 1
    page_size = page_size if isinstance(page_size, int) and page_size >= 1 else 25
    
    if USE_MONGODB and mongo_db is not None:
        try:
            q = {}
            if service_type and service_type.strip() and service_type.strip().lower() != "all":
                q["service_type"] = service_type.strip().lower()
            if name and name.strip():
                q["name"] = {"$regex": re.escape(name.strip()), "$options": "i"}
            if mobile and mobile.strip():
                digs = "".join(filter(str.isdigit, mobile.strip()))
                if digs:
                    q["$or"] = [{"mobile": {"$regex": digs}}, {"normalized_mobile": {"$regex": digs}}]
            if id_number and id_number.strip():
                q["id_number"] = {"$regex": re.escape(id_number.strip()), "$options": "i"}
            if date_filter and date_filter.strip():
                q["record_date"] = date_filter.strip()
            elif start_date and end_date:
                q["record_date"] = {"$gte": start_date.strip(), "$lte": end_date.strip()}
            elif start_date:
                q["record_date"] = {"$gte": start_date.strip()}
            elif end_date:
                q["record_date"] = {"$lte": end_date.strip()}
            if status and status.strip():
                q["status"] = {"$regex": f"^{re.escape(status.strip())}$", "$options": "i"}
            if baki_only:
                q["is_baki"] = 1
            if file_id:
                q["file_id"] = int(file_id)
            if query and query.strip():
                clean_q = query.strip()
                q["$or"] = [
                    {"name": {"$regex": re.escape(clean_q), "$options": "i"}},
                    {"mobile": {"$regex": "".join(filter(str.isdigit, clean_q)) or clean_q}},
                    {"id_number": {"$regex": re.escape(clean_q), "$options": "i"}},
                    {"remark": {"$regex": re.escape(clean_q), "$options": "i"}}
                ]
            
            total_count = mongo_db["office_records"].count_documents(q)
            skip = (page - 1) * page_size
            cursor = mongo_db["office_records"].find(q, {"_id": 0}).sort([("record_date", -1), ("id", -1)]).skip(skip).limit(page_size)
            items = list(cursor)
            return items, total_count
        except Exception as e:
            print("MongoDB search_records error:", e)

    # SQLite
    conditions = []
    params = []
    service_type = service_type if isinstance(service_type, str) else ""
    name = name if isinstance(name, str) else ""
    mobile = mobile if isinstance(mobile, str) else ""
    id_number = id_number if isinstance(id_number, str) else ""
    query = query if isinstance(query, str) else ""
    date_filter = date_filter if isinstance(date_filter, str) else ""
    status = status if isinstance(status, str) else ""
    start_date = start_date if isinstance(start_date, str) else ""
    end_date = end_date if isinstance(end_date, str) else ""
    file_id = file_id if isinstance(file_id, int) and file_id > 0 else None
    baki_only = bool(baki_only) if isinstance(baki_only, (bool, int)) else False
    
    if service_type and service_type.strip() and service_type.strip().lower() != "all":
        conditions.append("r.service_type = ?")
        params.append(service_type.strip().lower())
    if name and name.strip():
        conditions.append("LOWER(r.name) LIKE ?")
        params.append(f"%{name.strip().lower()}%")
    if mobile and mobile.strip():
        digits_only = "".join(filter(str.isdigit, mobile.strip()))
        if digits_only.startswith("91") and len(digits_only) == 12:
            base_10 = digits_only[2:]
        elif digits_only.startswith("0") and len(digits_only) == 11:
            base_10 = digits_only[1:]
        else:
            base_10 = digits_only
        conditions.append("(r.normalized_mobile LIKE ? OR r.mobile LIKE ?)")
        params.extend([f"%{base_10}%", f"%{mobile.strip()}%"])
    if id_number and id_number.strip():
        conditions.append("LOWER(r.id_number) LIKE ?")
        params.append(f"%{id_number.strip().lower()}%")
    if query and query.strip():
        clean_q = query.strip().lower()
        digits = "".join(filter(str.isdigit, clean_q))
        if digits:
            conditions.append("(LOWER(r.name) LIKE ? OR r.normalized_mobile LIKE ? OR LOWER(r.id_number) LIKE ? OR LOWER(r.remark) LIKE ?)")
            params.extend([f"%{clean_q}%", f"%{digits}%", f"%{clean_q}%", f"%{clean_q}%"])
        else:
            conditions.append("(LOWER(r.name) LIKE ? OR LOWER(r.id_number) LIKE ? OR LOWER(r.remark) LIKE ?)")
            params.extend([f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%"])
    if date_filter and date_filter.strip():
        conditions.append("r.record_date = ?")
        params.append(date_filter.strip())
    elif start_date and end_date:
        conditions.append("r.record_date BETWEEN ? AND ?")
        params.extend([start_date.strip(), end_date.strip()])
    elif start_date:
        conditions.append("r.record_date >= ?")
        params.append(start_date.strip())
    elif end_date:
        conditions.append("r.record_date <= ?")
        params.append(end_date.strip())
    if status and status.strip():
        conditions.append("LOWER(r.status) = ?")
        params.append(status.strip().lower())
    if baki_only:
        conditions.append("r.is_baki = 1")
    if file_id:
        conditions.append("r.file_id = ?")
        params.append(file_id)
        
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    count_sql = f"SELECT COUNT(*) FROM office_records r {where_clause}"
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT r.*, f.filename as source_file
        FROM office_records r
        LEFT JOIN uploaded_files f ON r.file_id = f.id
        {where_clause}
        ORDER BY r.record_date DESC, r.id DESC
        LIMIT ? OFFSET ?
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        data_params = params + [page_size, offset]
        cursor.execute(data_sql, data_params)
        rows = [dict(r) for r in cursor.fetchall()]
    return rows, total_count

def get_daily_progress_stats(date_filter: Optional[str] = None, service_type: Optional[str] = None) -> Dict[str, Any]:
    target_date = date_filter.strip() if date_filter and date_filter.strip() else datetime.now().strftime("%Y-%m-%d")
    clean_svc = (service_type or "all").strip().lower()
    
    if USE_MONGODB and mongo_db is not None:
        try:
            match_all = {}
            match_daily = {"record_date": target_date}
            if clean_svc != "all":
                match_all["service_type"] = clean_svc
                match_daily["service_type"] = clean_svc
            
            daily_total = mongo_db["office_records"].count_documents(match_daily)
            all_total = mongo_db["office_records"].count_documents(match_all)
            
            q_comp = dict(match_daily, status={"$regex": "^completed$", "$options": "i"})
            completed = mongo_db["office_records"].count_documents(q_comp)
            
            q_proc = dict(match_daily, status={"$regex": "^inprogress$", "$options": "i"})
            in_process = mongo_db["office_records"].count_documents(q_proc)
            
            q_rej = dict(match_daily, status={"$regex": "^rejected$", "$options": "i"})
            rejected = mongo_db["office_records"].count_documents(q_rej)
            
            q_baki = dict(match_daily, is_baki=1)
            baki_count = mongo_db["office_records"].count_documents(q_baki)
            
            # Revenue calculation
            pipeline = [{"$match": match_daily}, {"$group": {"_id": None, "total_revenue": {"$sum": "$fee_amt"}}}]
            rev_res = list(mongo_db["office_records"].aggregate(pipeline))
            total_rev = float(rev_res[0]["total_revenue"]) if rev_res else 0.0
            
            # Available dates
            distinct_dates = mongo_db["office_records"].distinct("record_date")
            dates_list = sorted([d for d in distinct_dates if d], reverse=True)[:30]
            
            completion_rate = round((completed / daily_total * 100), 1) if daily_total > 0 else 0.0
            return {
                "date": target_date,
                "service_type": clean_svc,
                "total_records": daily_total,
                "all_time_total": all_total,
                "completed": completed,
                "in_process": in_process,
                "rejected": rejected,
                "baki_count": baki_count,
                "total_revenue": total_rev,
                "completion_rate": completion_rate,
                "available_dates": dates_list
            }
        except Exception as e:
            print("MongoDB progress stats error:", e)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        svc_filter_all = "WHERE service_type = ?" if clean_svc != "all" else ""
        svc_params_all = [clean_svc] if clean_svc != "all" else []
        cursor.execute(f"SELECT COUNT(*) FROM office_records {svc_filter_all}", svc_params_all)
        all_time_total = cursor.fetchone()[0]
        
        conditions = ["record_date = ?"]
        params = [target_date]
        if clean_svc != "all":
            conditions.append("service_type = ?")
            params.append(clean_svc)
        where_sql = f"WHERE {' AND '.join(conditions)}"
        sql = f"""
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN LOWER(status) = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN LOWER(status) = 'inprogress' THEN 1 ELSE 0 END) as in_process_count,
                SUM(CASE WHEN LOWER(status) = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
                SUM(CASE WHEN is_baki = 1 THEN 1 ELSE 0 END) as baki_count,
                SUM(COALESCE(fee_amt, 0.0)) as total_revenue
            FROM office_records
            {where_sql}
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        daily_total = row["total_count"] or 0
        completed = row["completed_count"] or 0
        in_process = row["in_process_count"] or 0
        rejected = row["rejected_count"] or 0
        baki_count = row["baki_count"] or 0
        total_rev = float(row["total_revenue"] or 0.0)
        completion_rate = round((completed / daily_total * 100), 1) if daily_total > 0 else 0.0
        
        cursor.execute("SELECT DISTINCT record_date FROM office_records WHERE record_date != '' ORDER BY record_date DESC LIMIT 30")
        dates = [r[0] for r in cursor.fetchall() if r[0]]
        return {
            "date": target_date,
            "service_type": clean_svc,
            "total_records": daily_total,
            "all_time_total": all_time_total,
            "completed": completed,
            "in_process": in_process,
            "rejected": rejected,
            "baki_count": baki_count,
            "total_revenue": total_rev,
            "completion_rate": completion_rate,
            "available_dates": dates
        }

def get_all_records_for_export(service_type: Optional[str] = None, name: Optional[str] = None,
                               mobile: Optional[str] = None, id_number: Optional[str] = None,
                               date_filter: Optional[str] = None, file_id: Optional[int] = None) -> List[Dict[str, Any]]:
    records, _ = search_records(
        service_type=service_type, name=name, mobile=mobile,
        id_number=id_number, date_filter=date_filter, file_id=file_id,
        page=1, page_size=100000
    )
    return records

# ---------------------------------------------------------------------------
# Backup & Restore
# ---------------------------------------------------------------------------
def sync_db_to_static_files() -> bool:
    try:
        data_dir = DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        files = get_all_files()
        records, _ = search_records(page=1, page_size=50000)
        active_users = get_all_master_users()
        
        json_path = os.path.join(data_dir, "records.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
            
        primary_user = active_users[0] if active_users else {"username": "manish", "role": "master", "full_name": "Manish (Master Admin)"}
        js_path = os.path.join(data_dir, "records.js")
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(f"window.KHODAL_RECORDS = {json.dumps(records, ensure_ascii=False)};\n")
            f.write(f"window.KHODAL_INITIAL_FILES = {json.dumps(files, ensure_ascii=False)};\n")
            f.write(f"window.KHODAL_MASTER_USERS = {json.dumps(active_users, ensure_ascii=False)};\n")
            f.write(f"window.KHODAL_MASTER_USER = {json.dumps(primary_user, ensure_ascii=False)};\n")
            
        latest_backup = os.path.join(backup_dir, "khodal_backup_latest.json")
        backup_payload = {
            "version": "1.0",
            "synced_at": datetime.now().isoformat(),
            "database_engine": "mongodb" if USE_MONGODB else "sqlite",
            "total_files": len(files),
            "total_records": len(records),
            "files": files,
            "records": records
        }
        with open(latest_backup, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error in sync_db_to_static_files: {e}")
        return False

def backup_database_json() -> Dict[str, Any]:
    files = get_all_files()
    records, _ = search_records(page=1, page_size=100000)
    users = get_all_master_users()
    return {
        "app_name": "Khodal Office Data Hub",
        "exported_at": datetime.now().isoformat(),
        "database_engine": "mongodb" if USE_MONGODB else "sqlite",
        "file_count": len(files),
        "record_count": len(records),
        "files": files,
        "records": records,
        "users": users
    }

def restore_database_json(data: Dict[str, Any]) -> Dict[str, int]:
    records = data.get("records") or []
    files = data.get("files") or []
    users = data.get("users") or []
    
    # Restore users
    for u in users:
        if u.get("username"):
            create_master_user(u["username"], "manish@7575", u.get("full_name"), u.get("role", "master"))
            
    # Restore files
    old_to_new_file_ids = {}
    for f in files:
        new_fid = add_uploaded_file(
            filename=f.get("filename", "restored_file.xlsx"),
            service_type=f.get("service_type", "general"),
            file_date=f.get("file_date", ""),
            stored_path=f.get("stored_path", ""),
            file_size=f.get("file_size", 0),
            row_count=f.get("row_count", 0),
            sheet_names=f.get("sheet_names", []),
            uploaded_by=f.get("uploaded_by", "manish")
        )
        old_to_new_file_ids[f.get("id")] = new_fid
        
    # Remap file_id for records
    mapped_records = []
    for r in records:
        rec_copy = dict(r)
        if rec_copy.get("file_id") in old_to_new_file_ids:
            rec_copy["file_id"] = old_to_new_file_ids[rec_copy["file_id"]]
        mapped_records.append(rec_copy)
        
    inserted_count = insert_bulk_records(mapped_records)
    sync_db_to_static_files()
    return {"files_restored": len(files), "records_restored": inserted_count}
