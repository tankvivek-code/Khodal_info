import sqlite3
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "khodal_office.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


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
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM uploaded_files ORDER BY id ASC")
            files = [dict(r) for r in cursor.fetchall()]
            cursor.execute("SELECT * FROM office_records ORDER BY id ASC")
            records = [dict(r) for r in cursor.fetchall()]

        json_path = os.path.join(data_dir, "records.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)

        js_path = os.path.join(data_dir, "records.js")
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(f"window.KHODAL_RECORDS = {json.dumps(records, ensure_ascii=False)};\n")
            f.write(f"window.KHODAL_INITIAL_FILES = {json.dumps(files, ensure_ascii=False)};\n")

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
        cursor.execute("SELECT * FROM uploaded_files ORDER BY id ASC")
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


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Files tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                service_type TEXT DEFAULT 'general',
                file_date TEXT DEFAULT '',
                stored_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                row_count INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed'
            );
        """)
        
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


def add_uploaded_file(filename: str, service_type: str, file_date: str, stored_path: str, file_size: int, row_count: int) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO uploaded_files (filename, service_type, file_date, stored_path, file_size, row_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (filename, service_type, file_date, stored_path, file_size, row_count, datetime.now().isoformat())
        )
        conn.commit()
    sync_db_to_static_files()
    return cursor.lastrowid


def update_file_row_count(file_id: int, row_count: int):
    with get_db_connection() as conn:
        conn.execute("UPDATE uploaded_files SET row_count = ? WHERE id = ?", (row_count, file_id))
        conn.commit()


def get_all_files() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploaded_files ORDER BY id DESC")
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


def insert_bulk_records(records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
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

        rows.append((
            r.get("file_id"),
            r.get("service_type", "general"),
            normalize_date_for_db(r.get("record_date")),
            str(r.get("name") or "").strip(),
            raw_mob,
            norm_mob,
            str(r.get("id_number") or "").strip(),
            str(r.get("pan_type") or "").strip(),
            str(r.get("status") or "").strip(),
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

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO office_records (
                file_id, service_type, record_date, name, mobile,
                normalized_mobile, id_number, pan_type, status, total_amt,
                fee_amt, remark, is_baki, extra_data, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.get("file_id"),
                r.get("service_type", "ucaadhar"),
                normalize_date_for_db(r.get("record_date")),
                str(r.get("name") or "").strip(),
                raw_mob,
                norm_mob,
                str(r.get("id_number") or "").strip(),
                str(r.get("pan_type") or "").strip(),
                str(r.get("status") or "InProcess").strip(),
                total_amt,
                fee_amt,
                remark_str,
                is_baki,
                json.dumps(r.get("extra_data", {}), ensure_ascii=False),
                now,
                now
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
                r.get("service_type", "ucaadhar"),
                normalize_date_for_db(r.get("record_date")),
                str(r.get("name") or "").strip(),
                raw_mob,
                norm_mob,
                str(r.get("id_number") or "").strip(),
                str(r.get("pan_type") or "").strip(),
                str(r.get("status") or "").strip(),
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
        cursor.execute(
            "UPDATE office_records SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, now, record_id)
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
        if st_lower in ["inprocess", "in_process", "pending"]:
            conditions.append("(LOWER(r.status) LIKE '%process%' OR LOWER(r.status) = 'pending')")
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

        cursor.execute(f"SELECT COUNT(*) FROM office_records {where_clause} {'AND' if conditions else 'WHERE'} (LOWER(status) LIKE '%process%' OR LOWER(status) LIKE '%pending%')", params)
        in_process_count = cursor.fetchone()[0]

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
                "baki": r["baki"],
                "fee": r["fees"] or 0.0
            }

        return {
            "selected_date": date_str or "All Dates",
            "total_applications": total_count,
            "completed": completed_count,
            "in_process": in_process_count,
            "baki_pending": baki_count,
            "total_fee": total_fee,
            "completion_rate": round((completed_count / total_count * 100), 1) if total_count > 0 else 0,
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
