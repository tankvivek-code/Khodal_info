import sqlite3

import hashlib

import json

import os

import re

import secrets

from datetime import datetime, timedelta

from typing import List, Dict, Any, Optional, Tuple

from contextlib import contextmanager



DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

DB_PATH = os.environ.get("DB_PATH") or os.path.join(DATA_DIR, "khodal_office.db")





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

    # Match DD-MM-YYYY or DD/MM/YYYY

    m1 = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)

    if m1:

        return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"

    # Match YYYY-MM-DD or YYYY-DD-MM (Excel US-locale flip for Oct/Nov)

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





def sync_db_to_static_files():

    """

    Synchronizes all records and files from the SQLite database to:

    1. data/records.json

    2. data/records.js (window.KHODAL_RECORDS and window.KHODAL_INITIAL_FILES)

    3. data/backups/khodal_backup_latest.json

    This ensures that even if a client clears browser cache or history,

    records are permanently preserved on disk and automatically recovered.

    """

    try:

        data_dir = DATA_DIR

        os.makedirs(data_dir, exist_ok=True)

        backup_dir = os.path.join(data_dir, "backups")

        os.makedirs(backup_dir, exist_ok=True)



        with get_db_connection() as conn:

            cursor = conn.cursor()

            cursor.execute("SELECT id, filename, service_type, file_date, stored_path, file_size, row_count, sheet_names, uploaded_at, status FROM uploaded_files ORDER BY id ASC")

            files = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM office_records ORDER BY id ASC")

            records = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT id, username, full_name, role, is_active, created_at, last_login FROM users WHERE is_active = 1 ORDER BY id ASC")

            active_users = [dict(r) for r in cursor.fetchall()]



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



        # Rolling latest backup

        latest_backup = os.path.join(backup_dir, "khodal_backup_latest.json")

        backup_payload = {

            "version": "1.0",

            "synced_at": datetime.now().isoformat(),

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

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT id, filename, service_type, file_date, stored_path, file_size, row_count, sheet_names, uploaded_at, status FROM uploaded_files ORDER BY id ASC")

        files = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM office_records ORDER BY id ASC")

        records = [dict(r) for r in cursor.fetchall()]

    return {

        "version": "1.0",

        "exported_at": datetime.now().isoformat(),

        "total_files": len(files),

        "total_records": len(records),

        "files": files,

        "records": records

    }





def restore_database_json(data: Dict[str, Any]) -> Dict[str, int]:

    records = data.get("records") or []

    files = data.get("files") or []

    if not records and not files and isinstance(data, list):

        records = data

        files = []



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("DELETE FROM office_records;")

        cursor.execute("DELETE FROM uploaded_files;")



        for f in files:

            cursor.execute(

                """

                INSERT OR REPLACE INTO uploaded_files (id, filename, service_type, file_date, stored_path, file_size, row_count, uploaded_at, status)

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    f.get("id"),

                    f.get("filename", "restored_file.xlsx"),

                    f.get("service_type", "general"),

                    f.get("file_date", ""),

                    f.get("stored_path", ""),

                    f.get("file_size", 0),

                    f.get("row_count", 0),

                    f.get("uploaded_at", datetime.now().isoformat()),

                    f.get("status", "completed")

                )

            )



        for r in records:

            raw_mob = str(r.get("mobile") or "").strip()

            norm_mob = "".join(filter(str.isdigit, raw_mob))

            rec_d = normalize_date_for_db(r.get("record_date"))

            cursor.execute(

                """

                INSERT OR REPLACE INTO office_records (

                    id, file_id, service_type, record_date, name, mobile,

                    normalized_mobile, id_number, pan_type, status, total_amt,

                    fee_amt, remark, is_baki, extra_data, created_at, updated_at

                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    r.get("id"),

                    r.get("file_id"),

                    r.get("service_type", "ucaadhar"),

                    rec_d,

                    str(r.get("name") or "").strip(),

                    raw_mob,

                    norm_mob,

                    str(r.get("id_number") or "").strip(),

                    str(r.get("pan_type") or "").strip(),

                    str(r.get("status") or "Completed").strip(),

                    float(r.get("total_amt", 0.0) or 0.0),

                    float(r.get("fee_amt", 0.0) or 0.0),

                    str(r.get("remark") or "").strip(),

                    int(r.get("is_baki", 0) or 0),

                    json.dumps(r.get("extra_data", {})) if isinstance(r.get("extra_data"), dict) else str(r.get("extra_data") or "{}"),

                    r.get("created_at", datetime.now().isoformat()),

                    datetime.now().isoformat()

                )

            )

        conn.commit()



    sync_db_to_static_files()

    return {"files_restored": len(files), "records_restored": len(records)}







def hash_password(password: str) -> str:

    """Secure deterministic hash for master user password."""

    salt = "khodal_master_salt_7575"

    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()





def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:

    """

    Authenticate user against the SQLite database.

    Supports all active master users stored in the database.

    """

    if not username or not password:

        return None

    

    clean_user = username.strip().lower()

    clean_pass = password.strip()

    

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? AND is_active = 1", (clean_user,))

        row = cursor.fetchone()

        if not row:

            # Fallback direct checks for initial default accounts

            if clean_user == "manish" and clean_pass == "manish@7575":

                return {

                    "id": 1,

                    "username": "manish",

                    "full_name": "Manish",

                    "role": "master"

                }

            if clean_user == "admin" and clean_pass == "admin@7575":

                return {

                    "id": 2,

                    "username": "admin",

                    "full_name": "Master Admin",

                    "role": "master"

                }

            return None

        

        user_dict = dict(row)

        expected_hash = user_dict["password_hash"]

        given_hash = hash_password(clean_pass)

        

        # Support hashed check or direct match for initial default accounts

        is_valid = (expected_hash == given_hash)

        if not is_valid:

            if clean_user == "manish" and clean_pass == "manish@7575":

                is_valid = True

            elif clean_user == "admin" and clean_pass == "admin@7575":

                is_valid = True

        

        if is_valid:

            now = datetime.now().isoformat()

            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_dict["id"]))

            conn.commit()

            return {

                "id": user_dict["id"],

                "username": user_dict["username"],

                "full_name": user_dict.get("full_name") or user_dict["username"].capitalize(),

                "role": user_dict.get("role", "master")

            }

    return None





def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT id, username, full_name, role, is_active, created_at, last_login FROM users WHERE LOWER(username) = ?", (username.strip().lower(),))

        row = cursor.fetchone()

        return dict(row) if row else None





def create_master_user(username: str, password: str, full_name: str, role: str = "master") -> Dict[str, Any]:

    """Create a new master user and store permanently on the SQLite database."""

    clean_user = username.strip().lower()

    clean_pass = password.strip()

    clean_name = full_name.strip() or clean_user.capitalize()



    if not clean_user or len(clean_user) < 3:

        raise ValueError("Username must be at least 3 characters long.")

    if not clean_pass or len(clean_pass) < 4:

        raise ValueError("Password must be at least 4 characters long.")



    p_hash = hash_password(clean_pass)

    now = datetime.now().isoformat()



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (clean_user,))

        if cursor.fetchone():

            raise ValueError(f"Master user '{clean_user}' already exists in database.")



        cursor.execute("""

            INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)

            VALUES (?, ?, ?, ?, 1, ?)

        """, (clean_user, p_hash, clean_name, role, now))

        new_id = cursor.lastrowid

        conn.commit()



    sync_db_to_static_files()

    return {

        "id": new_id,

        "username": clean_user,

        "full_name": clean_name,

        "role": role,

        "is_active": 1,

        "created_at": now,

        "last_login": None

    }





def get_all_master_users() -> List[Dict[str, Any]]:

    """Retrieve all active master users from the SQLite database."""

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""

            SELECT id, username, full_name, role, is_active, created_at, last_login 

            FROM users 

            WHERE is_active = 1 

            ORDER BY id ASC

        """)

        return [dict(r) for r in cursor.fetchall()]





def delete_master_user(user_id: int) -> Tuple[bool, str]:

    """Delete a master user from the SQLite database (ensuring at least one master remains)."""

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")

        total_active = cursor.fetchone()[0]

        if total_active <= 1:

            return False, "Cannot delete the last remaining master user."



        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))

        row = cursor.fetchone()

        if not row:

            return False, "Master user not found."



        # Delete user's active database sessions

        cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

        conn.commit()



    sync_db_to_static_files()

    return True, f"Master user '{row['username']}' deleted successfully from database."





def create_user_session(user_id: int, duration_days: int = 30) -> str:

    """Create a persistent user session stored directly on SQLite database (not in browser storage)."""

    token = secrets.token_hex(32)

    created_at = datetime.now()

    expires_at = created_at + timedelta(days=duration_days)



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""

            INSERT INTO user_sessions (token, user_id, created_at, expires_at, last_active, is_active)

            VALUES (?, ?, ?, ?, ?, 1)

        """, (token, user_id, created_at.isoformat(), expires_at.isoformat(), created_at.isoformat()))

        conn.commit()

    return token





def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:

    """Validate session token against SQLite database and return authenticated user."""

    if not token:

        return None

    now = datetime.now().isoformat()

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""

            SELECT u.id, u.username, u.full_name, u.role, u.is_active, u.created_at, u.last_login,

                   s.expires_at, s.id as session_id

            FROM user_sessions s

            JOIN users u ON s.user_id = u.id

            WHERE s.token = ? AND s.is_active = 1 AND u.is_active = 1

        """, (token,))

        row = cursor.fetchone()

        if not row:

            return None



        row_dict = dict(row)

        if row_dict["expires_at"] < now:

            cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE id = ?", (row_dict["session_id"],))

            conn.commit()

            return None



        cursor.execute("UPDATE user_sessions SET last_active = ? WHERE id = ?", (now, row_dict["session_id"]))

        conn.commit()



        return {

            "id": row_dict["id"],

            "username": row_dict["username"],

            "full_name": row_dict["full_name"],

            "role": row_dict["role"],

            "created_at": row_dict["created_at"],

            "last_login": row_dict["last_login"]

        }





def delete_user_session(token: str) -> bool:

    """Delete a user session from the database on logout."""

    if not token:

        return False

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))

        conn.commit()

        return cursor.rowcount > 0





def init_db():

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db_connection() as conn:

        cursor = conn.cursor()

        

        # 1. Master users table

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT UNIQUE NOT NULL,

                password_hash TEXT NOT NULL,

                full_name TEXT DEFAULT 'Master Admin',

                role TEXT DEFAULT 'master',

                is_active INTEGER DEFAULT 1,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                last_login TIMESTAMP

            );

        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

        

        # Ensure master user 1 'manish' with pass 'manish@7575' exists

        cursor.execute("SELECT id FROM users WHERE LOWER(username) = 'manish'")

        master_row = cursor.fetchone()

        manish_hash = hash_password("manish@7575")

        if not master_row:

            cursor.execute("""

                INSERT INTO users (username, password_hash, full_name, role, is_active)

                VALUES ('manish', ?, 'Manish', 'master', 1)

            """, (manish_hash,))

            conn.commit()

        else:

            cursor.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE id = ?", (manish_hash, master_row[0]))

            conn.commit()



        # Ensure master user 2 'admin' with pass 'admin@7575' exists

        cursor.execute("SELECT id FROM users WHERE LOWER(username) = 'admin'")

        admin_row = cursor.fetchone()

        admin_hash = hash_password("admin@7575")

        if not admin_row:

            cursor.execute("""

                INSERT INTO users (username, password_hash, full_name, role, is_active)

                VALUES ('admin', ?, 'Master Admin', 'master', 1)

            """, (admin_hash,))

            conn.commit()

        else:

            cursor.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE id = ?", (admin_hash, admin_row[0]))

            conn.commit()



        # User sessions table - stores sessions in database instead of browser storage

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS user_sessions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                token TEXT UNIQUE NOT NULL,

                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                expires_at TIMESTAMP NOT NULL,

                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                is_active INTEGER DEFAULT 1

            );

        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);")



        # 2. Files tracking table with file_blob for storing Excel files in SQLite

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS uploaded_files (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                filename TEXT NOT NULL,

                service_type TEXT DEFAULT 'general',

                file_date TEXT DEFAULT '',

                stored_path TEXT NOT NULL,

                file_size INTEGER DEFAULT 0,

                row_count INTEGER DEFAULT 0,

                file_blob BLOB,

                sheet_names TEXT DEFAULT '[]',

                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                status TEXT DEFAULT 'completed'

            );

        """)

        

        # Column migration for existing uploaded_files table

        cursor.execute("PRAGMA table_info(uploaded_files);")

        cols = [r["name"] for r in cursor.fetchall()]

        if "file_blob" not in cols:

            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN file_blob BLOB;")

        if "sheet_names" not in cols:

            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN sheet_names TEXT DEFAULT '[]';")

        if "uploaded_by" not in cols:

            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN uploaded_by TEXT DEFAULT 'manish';")

        if "user_id" not in cols:

            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN user_id INTEGER REFERENCES users(id);")

        conn.commit()

        

        # Core office records table supporting all 4 service categories

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS office_records (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                file_id INTEGER REFERENCES uploaded_files(id) ON DELETE CASCADE,

                service_type TEXT NOT NULL, -- 'ucaadhar', 'aadhar_online', 'pancard', 'aayushman'

                record_date TEXT NOT NULL,  -- YYYY-MM-DD

                name TEXT DEFAULT '',

                mobile TEXT DEFAULT '',

                normalized_mobile TEXT DEFAULT '',

                id_number TEXT DEFAULT '',   -- SID (UC Aadhaar), SRN (Aadhaar Online), Ration/Ayushman No

                pan_type TEXT DEFAULT '',    -- 'NEW PAN', 'PAN UPDATE'

                status TEXT DEFAULT '',      -- 'Completed', 'InProcess', 'New', 'Renew', etc.

                total_amt REAL DEFAULT 0.0,  -- Total Amount (UC Aadhaar)

                fee_amt REAL DEFAULT 0.0,    -- Fee Collected

                remark TEXT DEFAULT '',      -- HOF, RIPIT, SPEED, NOT RECIV, 200 BAKI, etc.

                is_baki INTEGER DEFAULT 0,   -- 1 if remark indicates pending payment/docs

                extra_data TEXT DEFAULT '{}',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            );

        """)

        

        # Column migrations for existing office_records table

        cursor.execute("PRAGMA table_info(office_records);")

        rec_cols = [r["name"] for r in cursor.fetchall()]

        if "created_by" not in rec_cols:

            cursor.execute("ALTER TABLE office_records ADD COLUMN created_by TEXT DEFAULT 'manish';")

        if "user_id" not in rec_cols:

            cursor.execute("ALTER TABLE office_records ADD COLUMN user_id INTEGER REFERENCES users(id);")

        conn.commit()

        

        # Performance indexes for instant search & filtering

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_service ON office_records(service_type);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON office_records(record_date);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_name ON office_records(name);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_mobile ON office_records(mobile);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_norm_mob ON office_records(normalized_mobile);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_id_num ON office_records(id_number);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_status ON office_records(status);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_is_baki ON office_records(is_baki);")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_file_id ON office_records(file_id);")

        conn.commit()



        # Database normalization:

        # 1. Aadhaar cards (ucaadhar, aadhar_online) have exactly three statuses: Completed, InProgress, Rejected

        cursor.execute("""

            UPDATE office_records 

            SET status = 'Rejected' 

            WHERE service_type IN ('ucaadhar', 'aadhar_online') 

              AND (LOWER(status) IN ('reject', 'rejected', 'cancel', 'cancelled', 'failed'));

        """)

        cursor.execute("""

            UPDATE office_records 

            SET status = 'InProgress' 

            WHERE service_type IN ('ucaadhar', 'aadhar_online') 

              AND (LOWER(status) IN ('inprogress', 'in progress', 'inprocess', 'in process', 'pending', 'process', 'processing'));

        """)

        cursor.execute("""

            UPDATE office_records 

            SET status = 'Completed' 

            WHERE service_type IN ('ucaadhar', 'aadhar_online') 

              AND (status IS NULL OR status = '' OR LOWER(status) IN ('completed', 'complete', 'done', 'success', 'ok'));

        """)



        # 2. PAN Card and Ayushman Card do NOT need status - clear status column

        cursor.execute("""

            UPDATE office_records 

            SET status = '' 

            WHERE service_type IN ('pancard', 'aayushman');

        """)

        conn.commit()





def add_uploaded_file(

    filename: str,

    service_type: str,

    file_date: str,

    stored_path: str,

    file_size: int,

    row_count: int,

    file_blob: Optional[bytes] = None,

    sheet_names: Optional[List[str]] = None,

    uploaded_by: str = "manish",

    user_id: Optional[int] = None

) -> int:

    """Store Excel file metadata and raw binary blob permanently inside SQLite."""

    sheets_json = json.dumps(sheet_names or [], ensure_ascii=False)

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(

            """

            INSERT INTO uploaded_files (filename, service_type, file_date, stored_path, file_size, row_count, file_blob, sheet_names, uploaded_at, uploaded_by, user_id)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (filename, service_type, file_date, stored_path, file_size, row_count, file_blob, sheets_json, datetime.now().isoformat(), uploaded_by, user_id)

        )

        conn.commit()

    sync_db_to_static_files()

    return cursor.lastrowid





def get_file_blob(file_id: int) -> Tuple[Optional[bytes], str]:

    """Retrieve raw binary Excel file blob directly from SQLite database."""

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT file_blob, filename, stored_path FROM uploaded_files WHERE id = ?", (file_id,))

        row = cursor.fetchone()

        if not row:

            return None, ""

        if row["file_blob"]:

            return row["file_blob"], row["filename"]

        if row["stored_path"] and os.path.exists(row["stored_path"]):

            try:

                with open(row["stored_path"], "rb") as f:

                    return f.read(), row["filename"]

            except OSError:

                pass

        return None, row["filename"]





def update_file_row_count(file_id: int, row_count: int):

    with get_db_connection() as conn:

        conn.execute("UPDATE uploaded_files SET row_count = ? WHERE id = ?", (row_count, file_id))

        conn.commit()





def get_all_files() -> List[Dict[str, Any]]:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT id, filename, service_type, file_date, stored_path, file_size, row_count, sheet_names, uploaded_at, status, (file_blob IS NOT NULL) as has_blob FROM uploaded_files ORDER BY id DESC")

        rows = cursor.fetchall()

        return [dict(row) for row in rows]





def get_file_by_id(file_id: int) -> Optional[Dict[str, Any]]:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))

        row = cursor.fetchone()

        return dict(row) if row else None





def delete_uploaded_file(file_id: int) -> bool:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT stored_path FROM uploaded_files WHERE id = ?", (file_id,))

        row = cursor.fetchone()

        if row and os.path.exists(row["stored_path"]):

            try:

                os.remove(row["stored_path"])

            except OSError:

                pass

        

        cursor.execute("DELETE FROM office_records WHERE file_id = ?", (file_id,))

        cursor.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))

        conn.commit()

    sync_db_to_static_files()

    return True





def clear_all_database_records() -> bool:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("DELETE FROM office_records;")

        cursor.execute("DELETE FROM uploaded_files;")

        conn.commit()

        cursor.execute("VACUUM;")

        conn.commit()

    sync_db_to_static_files()

    return True





def normalize_record_status(service_type: str, raw_status: Any) -> str:

    """

    Enforce status rules:

    - pancard and aayushman do NOT need status (always returns "").

    - ucaadhar and aadhar_online have three statuses: 'Completed', 'InProgress', 'Rejected'.

    """

    st_svc = (service_type or "").strip().lower()

    if st_svc in ["pancard", "aayushman"]:

        return ""

    

    st_raw = str(raw_status or "").strip().lower()

    if not st_raw:

        return "InProgress"

    if any(k in st_raw for k in ["reject", "cancel", "failed"]):

        return "Rejected"

    if any(k in st_raw for k in ["process", "pending", "progress"]):

        return "InProgress"

    if any(k in st_raw for k in ["complet", "done", "ok", "success"]):

        return "Completed"

    return "InProgress"





def insert_bulk_records(records: List[Dict[str, Any]]) -> int:

    now = datetime.now().isoformat()

    rows = []

    for r in records:

        raw_mob = str(r.get("mobile") or "").strip()

        norm_mob = "".join(filter(str.isdigit, raw_mob))

        

        remark_str = str(r.get("remark") or "").strip()

        is_baki = 1 if any(w in remark_str.lower() for w in ["baki", "not reciv", "not resiv", "no reciv", "payment baki", "name baki"]) else 0

        

        try:

            total_amt = float(r.get("total_amt", 0.0) or 0.0)

        except (ValueError, TypeError):

            total_amt = 0.0

            

        try:

            fee_amt = float(r.get("fee_amt", 0.0) or 0.0)

        except (ValueError, TypeError):

            fee_amt = 0.0



        svc = r.get("service_type", "general")

        clean_status = normalize_record_status(svc, r.get("status"))



        rows.append((

            r.get("file_id"),

            svc,

            normalize_date_for_db(r.get("record_date")),

            str(r.get("name") or "").strip(),

            raw_mob,

            norm_mob,

            str(r.get("id_number") or "").strip(),

            str(r.get("pan_type") or "").strip(),

            clean_status,

            total_amt,

            fee_amt,

            remark_str,

            is_baki,

            json.dumps(r.get("extra_data", {}), ensure_ascii=False),

            now,

            now

        ))



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.executemany(

            """

            INSERT INTO office_records (

                file_id, service_type, record_date, name, mobile,

                normalized_mobile, id_number, pan_type, status, total_amt,

                fee_amt, remark, is_baki, extra_data, created_at, updated_at

            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            rows

        )

        conn.commit()

    sync_db_to_static_files()

    return len(rows)





def insert_single_record(r: Dict[str, Any]) -> int:

    now = datetime.now().isoformat()

    raw_mob = str(r.get("mobile") or "").strip()

    norm_mob = "".join(filter(str.isdigit, raw_mob))

    

    remark_str = str(r.get("remark") or "").strip()

    is_baki = 1 if any(w in remark_str.lower() for w in ["baki", "not reciv", "not resiv", "no reciv", "payment baki", "name baki"]) else 0



    try:

        total_amt = float(r.get("total_amt", 0.0) or 0.0)

    except Exception:

        total_amt = 0.0

    try:

        fee_amt = float(r.get("fee_amt", 0.0) or 0.0)

    except Exception:

        fee_amt = 0.0



    svc = r.get("service_type", "ucaadhar")

    clean_status = normalize_record_status(svc, r.get("status"))



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(

            """

            INSERT INTO office_records (

                file_id, service_type, record_date, name, mobile,

                normalized_mobile, id_number, pan_type, status, total_amt,

                fee_amt, remark, is_baki, extra_data, created_at, updated_at,

                created_by, user_id

            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (

                r.get("file_id"),

                svc,

                normalize_date_for_db(r.get("record_date")),

                str(r.get("name") or "").strip(),

                raw_mob,

                norm_mob,

                str(r.get("id_number") or "").strip(),

                str(r.get("pan_type") or "").strip(),

                clean_status,

                total_amt,

                fee_amt,

                remark_str,

                is_baki,

                json.dumps(r.get("extra_data", {}), ensure_ascii=False),

                now,

                now,

                str(r.get("created_by") or "manish"),

                r.get("user_id")

            )

        )

        conn.commit()

    sync_db_to_static_files()

    return cursor.lastrowid





def update_single_record(record_id: int, r: Dict[str, Any]) -> bool:

    now = datetime.now().isoformat()

    raw_mob = str(r.get("mobile") or "").strip()

    norm_mob = "".join(filter(str.isdigit, raw_mob))

    

    remark_str = str(r.get("remark") or "").strip()

    is_baki = 1 if any(w in remark_str.lower() for w in ["baki", "not reciv", "not resiv", "no reciv", "payment baki", "name baki"]) else 0



    try:

        total_amt = float(r.get("total_amt", 0.0) or 0.0)

    except Exception:

        total_amt = 0.0

    try:

        fee_amt = float(r.get("fee_amt", 0.0) or 0.0)

    except Exception:

        fee_amt = 0.0



    svc = r.get("service_type", "ucaadhar")

    clean_status = normalize_record_status(svc, r.get("status"))



    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(

            """

            UPDATE office_records

            SET service_type = ?, record_date = ?, name = ?, mobile = ?,

                normalized_mobile = ?, id_number = ?, pan_type = ?, status = ?,

                total_amt = ?, fee_amt = ?, remark = ?, is_baki = ?, updated_at = ?

            WHERE id = ?

            """,

            (

                svc,

                normalize_date_for_db(r.get("record_date")),

                str(r.get("name") or "").strip(),

                raw_mob,

                norm_mob,

                str(r.get("id_number") or "").strip(),

                str(r.get("pan_type") or "").strip(),

                clean_status,

                total_amt,

                fee_amt,

                remark_str,

                is_baki,

                now,

                record_id

            )

        )

        conn.commit()

    sync_db_to_static_files()

    return cursor.rowcount > 0





def delete_single_record(record_id: int) -> bool:

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("DELETE FROM office_records WHERE id = ?", (record_id,))

        conn.commit()

    sync_db_to_static_files()

    return cursor.rowcount > 0





def update_record_status(record_id: int, new_status: str) -> bool:

    now = datetime.now().isoformat()

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("SELECT service_type FROM office_records WHERE id = ?", (record_id,))

        row = cursor.fetchone()

        if not row:

            return False

        clean_status = normalize_record_status(row["service_type"], new_status)

        cursor.execute(

            "UPDATE office_records SET status = ?, updated_at = ? WHERE id = ?",

            (clean_status, now, record_id)

        )

        conn.commit()

    sync_db_to_static_files()

    return cursor.rowcount > 0





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

    """

    High-performance flexible search supporting:

    - Service category (ucaadhar, aadhar_online, pancard, aayushman, or None for all)

    - Name (case-insensitive substring)

    - Mobile (partial digits match)

    - ID Number (SID, SRN, Ration/Ayushman Card No)

    - General query (across all columns)

    - Specific Date or Date Range (start_date to end_date)

    - Status ('Completed', 'InProcess', etc.)

    - Baki / Pending only flag

    - Pagination

    """

    conditions = []

    params = []



    # Sanitize string parameters

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

    page = page if isinstance(page, int) and page >= 1 else 1

    page_size = page_size if isinstance(page_size, int) and page_size >= 1 else 25

    baki_only = bool(baki_only) if isinstance(baki_only, (bool, int)) else False

    

    if service_type and service_type.strip() and service_type.strip().lower() != "all":

        conditions.append("r.service_type = ?")

        params.append(service_type.strip().lower())

        

    if name and name.strip():

        conditions.append("LOWER(r.name) LIKE ?")

        params.append(f"%{name.strip().lower()}%")

        

    if mobile and mobile.strip():

        raw_m = mobile.strip()

        digits_only = "".join(filter(str.isdigit, raw_m))

        

        # If user typed +91XXXXXXXXXX (12 digits) or 0XXXXXXXXXX (11 digits), extract standard 10-digit

        if digits_only.startswith("91") and len(digits_only) == 12:

            base_10 = digits_only[2:]

        elif digits_only.startswith("0") and len(digits_only) == 11:

            base_10 = digits_only[1:]

        else:

            base_10 = digits_only



        if digits_only:

            conditions.append("""

                (

                    r.normalized_mobile LIKE ? OR

                    r.normalized_mobile LIKE ? OR

                    r.mobile LIKE ? OR

                    r.mobile LIKE ?

                )

            """)

            params.extend([f"%{base_10}%", f"%{digits_only}%", f"%{base_10}%", f"%{raw_m}%"])

        else:

            conditions.append("r.mobile LIKE ?")

            params.append(f"%{raw_m}%")

            

    if id_number and id_number.strip():

        conditions.append("LOWER(r.id_number) LIKE ?")

        params.append(f"%{id_number.strip().lower()}%")



    if date_filter and date_filter.strip():

        df = date_filter.strip()

        m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", df)

        if m:

            df = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

        conditions.append("r.record_date = ?")

        params.append(df)

    elif start_date and end_date:

        conditions.append("r.record_date BETWEEN ? AND ?")

        params.extend([start_date.strip(), end_date.strip()])

        

    if status and status.strip() and status.strip().lower() != "all":

        st_lower = status.strip().lower()

        if st_lower in ["inprogress", "in_process", "inprocess", "pending", "process"]:

            conditions.append("(LOWER(r.status) LIKE '%progress%' OR LOWER(r.status) LIKE '%process%' OR LOWER(r.status) = 'pending')")

        elif st_lower in ["reject", "rejected", "failed", "cancelled"]:

            conditions.append("LOWER(r.status) LIKE '%reject%'")

        elif st_lower in ["complete", "completed", "done"]:

            conditions.append("LOWER(r.status) LIKE '%complete%'")

        else:

            conditions.append("LOWER(r.status) = ?")

            params.append(st_lower)

        

    if baki_only:

        conditions.append("r.is_baki = 1")

        

    if file_id is not None and file_id > 0:

        conditions.append("r.file_id = ?")

        params.append(file_id)



    if query and query.strip():

        q_term = query.strip()

        q_lower = f"%{q_term.lower()}%"

        digits_q = "".join(filter(str.isdigit, q_term))

        

        if digits_q:

            base_q = digits_q

            if digits_q.startswith("91") and len(digits_q) == 12:

                base_q = digits_q[2:]

            elif digits_q.startswith("0") and len(digits_q) == 11:

                base_q = digits_q[1:]



            conditions.append("""

                (

                    LOWER(r.name) LIKE ? OR

                    r.normalized_mobile LIKE ? OR

                    r.normalized_mobile LIKE ? OR

                    r.mobile LIKE ? OR

                    LOWER(r.id_number) LIKE ? OR

                    LOWER(r.remark) LIKE ? OR

                    LOWER(r.pan_type) LIKE ? OR

                    LOWER(r.status) LIKE ?

                )

            """)

            params.extend([q_lower, f"%{base_q}%", f"%{digits_q}%", f"%{q_term}%", q_lower, q_lower, q_lower, q_lower])

        else:

            conditions.append("""

                (

                    LOWER(r.name) LIKE ? OR

                    LOWER(r.id_number) LIKE ? OR

                    LOWER(r.remark) LIKE ? OR

                    LOWER(r.pan_type) LIKE ? OR

                    LOWER(r.status) LIKE ? OR

                    LOWER(r.record_date) LIKE ?

                )

            """)

            params.extend([q_lower, q_lower, q_lower, q_lower, q_lower, q_lower])



    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    

    with get_db_connection() as conn:

        cursor = conn.cursor()

        

        count_sql = f"SELECT COUNT(*) FROM office_records r {where_clause}"

        cursor.execute(count_sql, params)

        total_count = cursor.fetchone()[0]

        

        data_sql = f"""

            SELECT r.*, f.filename as source_file

            FROM office_records r

            LEFT JOIN uploaded_files f ON r.file_id = f.id

            {where_clause}

            ORDER BY r.record_date DESC, r.id DESC

            LIMIT ? OFFSET ?

        """

        offset = (page - 1) * page_size

        paged_params = list(params) + [page_size, offset]

        

        cursor.execute(data_sql, paged_params)

        rows = cursor.fetchall()

        

        results = []

        for r in rows:

            d = dict(r)

            try:

                d["extra_data"] = json.loads(d.get("extra_data") or "{}")

            except Exception:

                d["extra_data"] = {}

            results.append(d)

            

        return results, total_count





def get_daily_progress_stats(date_str: Optional[str] = None, service_type: Optional[str] = None) -> Dict[str, Any]:

    """

    Returns progress statistics:

    - total applications

    - completed count & %

    - in_process count & %

    - baki / pending count

    - total fee / revenue collected

    - service-wise breakdown

    """

    conditions = []

    params = []



    date_str = date_str if isinstance(date_str, str) else ""

    service_type = service_type if isinstance(service_type, str) else ""

    

    if date_str and date_str.strip():

        ds = date_str.strip()

        m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", ds)

        if m:

            ds = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

        conditions.append("record_date = ?")

        params.append(ds)

        

    if service_type and service_type.strip() and service_type.strip().lower() != "all":

        conditions.append("service_type = ?")

        params.append(service_type.strip().lower())



    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""



    with get_db_connection() as conn:

        cursor = conn.cursor()

        

        # Overall counts

        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause}", params)

        total_count = cursor.fetchone()[0]



        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause} {'AND' if conditions else 'WHERE'} LOWER(status) LIKE '%complete%'", params)

        completed_count = cursor.fetchone()[0]



        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause} {'AND' if conditions else 'WHERE'} (LOWER(status) LIKE '%progress%' OR LOWER(status) LIKE '%process%' OR LOWER(status) LIKE '%pending%')", params)

        in_process_count = cursor.fetchone()[0]



        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause} {'AND' if conditions else 'WHERE'} LOWER(status) LIKE '%reject%'", params)

        rejected_count = cursor.fetchone()[0]



        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause} {'AND' if conditions else 'WHERE'} is_baki = 1", params)

        baki_count = cursor.fetchone()[0]



        cursor.execute(f"SELECT SUM(fee_amt) FROM office_records {where_clause}", params)

        fee_sum_row = cursor.fetchone()

        total_fee = fee_sum_row[0] if fee_sum_row and fee_sum_row[0] else 0.0



        # Available dates list (for date picker / filter quick selection)

        cursor.execute("SELECT DISTINCT record_date FROM office_records WHERE record_date != '' ORDER BY record_date DESC")

        available_dates = [r[0] for r in cursor.fetchall()]



        # Service-wise distribution

        cursor.execute(f"""

            SELECT service_type, COUNT(*) as cnt,

                   SUM(CASE WHEN LOWER(status) LIKE '%complete%' THEN 1 ELSE 0 END) as comp,

                   SUM(CASE WHEN LOWER(status) LIKE '%progress%' OR LOWER(status) LIKE '%process%' OR LOWER(status) LIKE '%pending%' THEN 1 ELSE 0 END) as in_prog,

                   SUM(CASE WHEN LOWER(status) LIKE '%reject%' THEN 1 ELSE 0 END) as rej,

                   SUM(CASE WHEN is_baki = 1 THEN 1 ELSE 0 END) as baki,

                   SUM(fee_amt) as fees

            FROM office_records

            {where_clause}

            GROUP BY service_type

        """, params)

        service_breakdown = {}

        for r in cursor.fetchall():

            service_breakdown[r["service_type"]] = {

                "total": r["cnt"],

                "completed": r["comp"],

                "in_process": r["in_prog"],

                "rejected": r["rej"],

                "baki": r["baki"],

                "fee": r["fees"] or 0.0

            }



        return {

            "selected_date": date_str or "All Dates",

            "total_applications": total_count,

            "completed": completed_count,

            "in_process": in_process_count,

            "rejected": rejected_count,

            "baki_pending": baki_count,

            "total_fee": total_fee,

            "completion_rate": round((completed_count / total_count * 100), 1) if total_count > 0 else 0,

            "rejection_rate": round((rejected_count / total_count * 100), 1) if total_count > 0 else 0,

            "available_dates": available_dates,

            "service_breakdown": service_breakdown

        }





def get_all_records_for_export(

    service_type: Optional[str] = None,

    name: Optional[str] = None,

    mobile: Optional[str] = None,

    id_number: Optional[str] = None,

    date_filter: Optional[str] = None

) -> List[Dict[str, Any]]:

    records, _ = search_records(

        service_type=service_type,

        name=name,

        mobile=mobile,

        id_number=id_number,

        date_filter=date_filter,

        page=1,

        page_size=100000

    )

    return records

