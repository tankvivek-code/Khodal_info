import hashlib
import json
import os
import re
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pymongo
from pymongo import MongoClient, ReturnDocument
import bson
from bson.binary import Binary

# ---------------------------------------------------------------------------
# Environment & Configuration (MongoDB Atlas Cloud Database)
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

DEFAULT_MONGO_URI_TEMPLATE = "mongodb+srv://tankvivek65_db_user:<db_password>@cluster0.nl4cir6.mongodb.net/?compressors=zlib"
MONGODB_URI = os.environ.get("MONGODB_URI", DEFAULT_MONGO_URI_TEMPLATE).strip()
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "khodal_office").strip()

mongo_client: Optional[MongoClient] = None
mongo_db = None
USE_MONGODB = False
MONGO_CONNECT_ERROR = ""

def get_effective_mongo_uri(uri: Optional[str] = None) -> str:
    target = (uri or os.environ.get("MONGODB_URI") or DEFAULT_MONGO_URI_TEMPLATE).strip()
    pwd = (os.environ.get("MONGODB_PASSWORD") or os.environ.get("DB_PASSWORD") or "").strip()
    if pwd and "<db_password>" in target:
        target = target.replace("<db_password>", urllib.parse.quote_plus(pwd))
    return target

def init_mongo_connection(uri: Optional[str] = None) -> bool:
    global mongo_client, mongo_db, USE_MONGODB, MONGODB_URI, MONGO_CONNECT_ERROR
    target_uri = get_effective_mongo_uri(uri)
    if not target_uri or "<db_password>" in target_uri:
        USE_MONGODB = False
        MONGO_CONNECT_ERROR = "Awaiting database password for user tankvivek65_db_user"
        return False
    try:
        client = MongoClient(target_uri, serverSelectionTimeoutMS=4000)
        client.admin.command('ping')
        mongo_client = client
        mongo_db = client.get_database(MONGODB_DB_NAME)
        USE_MONGODB = True
        MONGODB_URI = target_uri
        MONGO_CONNECT_ERROR = ""
        ensure_indexes()
        ensure_default_master_users()
        print(f"🟢 Connected to MongoDB Atlas Cloud Database ({MONGODB_DB_NAME}) successfully!")
        return True
    except Exception as e:
        USE_MONGODB = False
        MONGO_CONNECT_ERROR = str(e)
        print(f"⚠️ Could not connect to MongoDB Atlas ({e})")
        return False

def configure_mongodb_password(password: str) -> Tuple[bool, str]:
    global MONGODB_URI
    if not password or not password.strip():
        return False, "Password cannot be empty."
    encoded_pw = urllib.parse.quote_plus(password.strip())
    new_uri = f"mongodb+srv://tankvivek65_db_user:{encoded_pw}@cluster0.nl4cir6.mongodb.net/?compressors=zlib"
    success = init_mongo_connection(new_uri)
    if success:
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write("# MongoDB Atlas Cloud Database Configuration\n")
                f.write(f"MONGODB_URI={new_uri}\n")
                f.write(f"MONGODB_DB_NAME={MONGODB_DB_NAME}\n")
        except Exception:
            pass
        return True, "Successfully connected to MongoDB Atlas Cloud Database (Cluster0)!"
    else:
        return False, f"Could not authenticate with MongoDB Atlas: {MONGO_CONNECT_ERROR}"

def get_database_status() -> Dict[str, Any]:
    waiting_pw = "<db_password>" in MONGODB_URI or not MONGODB_URI or not USE_MONGODB
    count = 0
    if mongo_db is not None:
        try:
            count = mongo_db["office_records"].count_documents({})
        except Exception:
            pass
    return {
        "engine": "mongodb",
        "mongodb_connected": USE_MONGODB,
        "mongodb_cluster": "Cluster0 (cluster0.nl4cir6.mongodb.net)",
        "waiting_for_password": waiting_pw,
        "db_name": MONGODB_DB_NAME,
        "records_count": count,
        "error": MONGO_CONNECT_ERROR if not USE_MONGODB else ""
    }

def get_next_sequence(name: str = "records") -> int:
    if mongo_db is None:
        return 1
    doc = mongo_db["counters"].find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return int(doc["seq"])

def ensure_indexes():
    if mongo_db is None:
        return
    try:
        mongo_db["office_records"].create_index([("id", pymongo.ASCENDING)], unique=True)
        mongo_db["office_records"].create_index([("service_type", pymongo.ASCENDING)])
        mongo_db["office_records"].create_index([("record_date", pymongo.DESCENDING)])
        mongo_db["office_records"].create_index([("normalized_mobile", pymongo.ASCENDING)])
        mongo_db["office_records"].create_index([("id_number", pymongo.ASCENDING)])
        mongo_db["office_records"].create_index([("file_id", pymongo.ASCENDING)])
        mongo_db["office_records"].create_index([("status", pymongo.ASCENDING)])
        mongo_db["office_records"].create_index([("is_baki", pymongo.ASCENDING)])
        
        mongo_db["uploaded_files"].create_index([("id", pymongo.ASCENDING)], unique=True)
        mongo_db["uploaded_files"].create_index([("uploaded_at", pymongo.DESCENDING)])
        
        mongo_db["users"].create_index([("id", pymongo.ASCENDING)], unique=True)
        mongo_db["users"].create_index([("username", pymongo.ASCENDING)], unique=True)
        
        mongo_db["user_sessions"].create_index([("session_token", pymongo.ASCENDING)], unique=True)
        mongo_db["user_sessions"].create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0)
        mongo_db["counters"].create_index([("_id", pymongo.ASCENDING)], unique=True)
    except Exception as e:
        print(f"Warning configuring MongoDB indexes: {e}")

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"

def ensure_default_master_users():
    if mongo_db is None:
        return
    try:
        if mongo_db["users"].count_documents({}) == 0:
            create_master_user("manish", "manish@7575", "Manish (Master Admin)", "master")
            create_master_user("admin", "admin@123", "Office Administrator", "master")
    except Exception as e:
        print(f"Warning ensuring default master users: {e}")

def init_db():
    init_mongo_connection()

# ---------------------------------------------------------------------------
# User Authentication & Sessions (MongoDB Atlas)
# ---------------------------------------------------------------------------
def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    clean_user = username.strip().lower()
    if mongo_db is None:
        return None
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
    return None

def create_master_user(username: str, password: str, full_name: Optional[str] = None, role: str = "master") -> Dict[str, Any]:
    clean_user = username.strip().lower()
    pw_hash = hash_password(password)
    display_name = full_name.strip() if full_name and full_name.strip() else f"{clean_user.capitalize()} (Master)"
    now = datetime.now().isoformat()
    if mongo_db is None:
        return {"id": 1, "username": clean_user, "full_name": display_name, "role": role}
    existing = mongo_db["users"].find_one({"username": clean_user})
    if existing:
        mongo_db["users"].update_one(
            {"username": clean_user},
            {"$set": {"password_hash": pw_hash, "full_name": display_name, "role": role, "is_active": 1, "last_login": now}}
        )
        u = mongo_db["users"].find_one({"username": clean_user}, {"_id": 0, "password_hash": 0})
        return dict(u)
    new_id = get_next_sequence("users")
    doc = {
        "id": new_id,
        "username": clean_user,
        "password_hash": pw_hash,
        "full_name": display_name,
        "role": role,
        "is_active": 1,
        "created_at": now,
        "last_login": None
    }
    mongo_db["users"].insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc

def get_all_master_users() -> List[Dict[str, Any]]:
    if mongo_db is None:
        return []
    try:
        cursor = mongo_db["users"].find({}, {"_id": 0, "password_hash": 0}).sort("id", pymongo.ASCENDING)
        return list(cursor)
    except Exception:
        return []

def delete_master_user(user_id: int) -> bool:
    if mongo_db is None:
        return False
    try:
        res = mongo_db["users"].delete_one({"id": user_id})
        return res.deleted_count > 0
    except Exception:
        return False

def create_user_session(user_id: int, duration_days: int = 30) -> str:
    token = secrets.token_hex(32)
    now = datetime.now()
    expires_at = (now + timedelta(days=duration_days)).isoformat()
    if mongo_db is not None:
        try:
            mongo_db["user_sessions"].insert_one({
                "session_token": token,
                "user_id": user_id,
                "created_at": now.isoformat(),
                "expires_at": expires_at
            })
        except Exception as e:
            print("MongoDB session creation error:", e)
    return token

def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or mongo_db is None:
        return None
    try:
        sess = mongo_db["user_sessions"].find_one({"session_token": token})
        if sess:
            if sess.get("expires_at"):
                exp = datetime.fromisoformat(sess["expires_at"])
                if exp < datetime.now():
                    mongo_db["user_sessions"].delete_one({"session_token": token})
                    return None
            user = mongo_db["users"].find_one({"id": sess["user_id"], "is_active": 1}, {"_id": 0, "password_hash": 0})
            if user:
                return dict(user)
    except Exception:
        pass
    return None

def delete_user_session(token: str) -> bool:
    if not token or mongo_db is None:
        return False
    try:
        res = mongo_db["user_sessions"].delete_one({"session_token": token})
        return res.deleted_count > 0
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Uploaded Files Management (MongoDB Atlas)
# ---------------------------------------------------------------------------
def add_uploaded_file(filename: str, original_filename: str, file_path: str,
                      file_type: str, file_size: int, row_count: int,
                      service_type: str, file_blob: Optional[bytes] = None) -> int:
    clean_svc = (service_type or "all").lower().strip()
    now = datetime.now().isoformat()
    if mongo_db is None:
        return 1
    new_id = get_next_sequence("files")
    doc = {
        "id": new_id,
        "filename": filename,
        "original_filename": original_filename,
        "file_path": file_path,
        "file_type": file_type,
        "file_size": file_size,
        "row_count": row_count,
        "service_type": clean_svc,
        "uploaded_at": now,
        "file_blob": Binary(file_blob) if file_blob else None
    }
    mongo_db["uploaded_files"].insert_one(doc)
    return new_id

def get_file_blob(file_id: int) -> Optional[bytes]:
    if mongo_db is None:
        return None
    try:
        f = mongo_db["uploaded_files"].find_one({"id": file_id})
        if f and f.get("file_blob"):
            return bytes(f["file_blob"])
    except Exception:
        pass
    return None

def get_all_files() -> List[Dict[str, Any]]:
    if mongo_db is None:
        return []
    try:
        cursor = mongo_db["uploaded_files"].find({}, {"_id": 0, "file_blob": 0}).sort("uploaded_at", pymongo.DESCENDING)
        files = list(cursor)
        for f in files:
            f["actual_record_count"] = mongo_db["office_records"].count_documents({"file_id": f["id"]})
        return files
    except Exception:
        return []

def get_file_by_id(file_id: int) -> Optional[Dict[str, Any]]:
    if mongo_db is None:
        return None
    try:
        f = mongo_db["uploaded_files"].find_one({"id": file_id}, {"_id": 0, "file_blob": 0})
        return dict(f) if f else None
    except Exception:
        return None

def update_file_row_count(file_id: int, new_count: int):
    if mongo_db is not None:
        try:
            mongo_db["uploaded_files"].update_one({"id": file_id}, {"$set": {"row_count": new_count}})
        except Exception:
            pass

def delete_uploaded_file(file_id: int) -> bool:
    if mongo_db is None:
        return False
    try:
        mongo_db["office_records"].delete_many({"file_id": file_id})
        res = mongo_db["uploaded_files"].delete_one({"id": file_id})
        return res.deleted_count > 0
    except Exception:
        return False

def clear_all_database_records() -> Tuple[int, int]:
    if mongo_db is None:
        return (0, 0)
    try:
        res_r = mongo_db["office_records"].delete_many({})
        res_f = mongo_db["uploaded_files"].delete_many({})
        return (res_r.deleted_count, res_f.deleted_count)
    except Exception:
        return (0, 0)

# ---------------------------------------------------------------------------
# Office Records Management (MongoDB Atlas)
# ---------------------------------------------------------------------------
def normalize_date(val: Any) -> Optional[str]:
    if not val:
        return None
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def insert_bulk_records(records: List[Dict[str, Any]]) -> int:
    if not records or mongo_db is None:
        return 0
    now = datetime.now().isoformat()
    docs = []
    for r in records:
        rec_id = r.get("id") or get_next_sequence("records")
        mob = str(r.get("mobile", "") or "")
        norm_mob = "".join(filter(str.isdigit, mob))
        doc = {
            "id": rec_id,
            "file_id": r.get("file_id"),
            "service_type": (r.get("service_type") or "ucaadhar").lower().strip(),
            "name": str(r.get("name", "") or "").strip(),
            "mobile": mob,
            "normalized_mobile": norm_mob,
            "id_number": str(r.get("id_number", "") or "").strip(),
            "record_date": normalize_date(r.get("record_date")) or now[:10],
            "status": str(r.get("status", "") or "Completed").strip(),
            "amount": float(r.get("amount", 0.0) or 0.0),
            "remarks": str(r.get("remarks", "") or "").strip(),
            "dynamic_fields": r.get("dynamic_fields") or {},
            "created_at": r.get("created_at") or now,
            "updated_at": now,
            "is_baki": 1 if r.get("is_baki") else 0
        }
        docs.append(doc)
    try:
        res = mongo_db["office_records"].insert_many(docs, ordered=False)
        return len(res.inserted_ids)
    except Exception as e:
        print("MongoDB insert_bulk_records error:", e)
        return len(docs)

def insert_single_record(record: Dict[str, Any]) -> int:
    if mongo_db is None:
        return 0
    now = datetime.now().isoformat()
    rec_id = record.get("id") or get_next_sequence("records")
    mob = str(record.get("mobile", "") or "")
    doc = {
        "id": rec_id,
        "file_id": record.get("file_id"),
        "service_type": (record.get("service_type") or "ucaadhar").lower().strip(),
        "name": str(record.get("name", "") or "").strip(),
        "mobile": mob,
        "normalized_mobile": "".join(filter(str.isdigit, mob)),
        "id_number": str(record.get("id_number", "") or "").strip(),
        "record_date": normalize_date(record.get("record_date")) or now[:10],
        "status": str(record.get("status", "") or "Completed").strip(),
        "amount": float(record.get("amount", 0.0) or 0.0),
        "remarks": str(record.get("remarks", "") or "").strip(),
        "dynamic_fields": record.get("dynamic_fields") or {},
        "created_at": now,
        "updated_at": now,
        "is_baki": 1 if record.get("is_baki") else 0
    }
    try:
        mongo_db["office_records"].insert_one(doc)
        return rec_id
    except Exception as e:
        print("MongoDB insert_single_record error:", e)
        return 0

def update_single_record(record_id: int, updates: Dict[str, Any]) -> bool:
    if mongo_db is None:
        return False
    now = datetime.now().isoformat()
    set_fields = {"updated_at": now}
    for k, v in updates.items():
        if k in ("name", "status", "remarks", "service_type", "id_number"):
            set_fields[k] = str(v).strip()
        elif k == "mobile":
            set_fields["mobile"] = str(v)
            set_fields["normalized_mobile"] = "".join(filter(str.isdigit, str(v)))
        elif k == "record_date":
            set_fields["record_date"] = normalize_date(v) or str(v)[:10]
        elif k == "amount":
            try:
                set_fields["amount"] = float(v)
            except (ValueError, TypeError):
                pass
        elif k == "is_baki":
            set_fields["is_baki"] = 1 if v else 0
        elif k == "dynamic_fields":
            set_fields["dynamic_fields"] = v
    try:
        res = mongo_db["office_records"].update_one({"id": record_id}, {"$set": set_fields})
        return res.modified_count > 0 or res.matched_count > 0
    except Exception:
        return False

def delete_single_record(record_id: int) -> bool:
    if mongo_db is None:
        return False
    try:
        res = mongo_db["office_records"].delete_one({"id": record_id})
        return res.deleted_count > 0
    except Exception:
        return False

def update_record_status(record_id: int, new_status: str, remarks: Optional[str] = None) -> bool:
    if mongo_db is None:
        return False
    now = datetime.now().isoformat()
    fields = {"status": new_status.strip(), "updated_at": now}
    if remarks is not None:
        fields["remarks"] = remarks.strip()
    try:
        res = mongo_db["office_records"].update_one({"id": record_id}, {"$set": fields})
        return res.modified_count > 0 or res.matched_count > 0
    except Exception:
        return False

def search_records(
    service_type: Optional[str] = None,
    name: Optional[str] = None,
    mobile: Optional[str] = None,
    id_number: Optional[str] = None,
    query: Optional[str] = None,
    date_filter: Optional[str] = None,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = None,
    status: Optional[str] = None,
    file_id: Optional[int] = None,
    is_baki: Optional[bool] = None,
    baki_only: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "id",
    sort_order: str = "desc"
) -> Tuple[List[Dict[str, Any]], int]:
    if mongo_db is None:
        return [], 0
    try:
        q: Dict[str, Any] = {}
        if service_type and service_type.lower() != "all":
            q["service_type"] = service_type.lower().strip()
        if name and name.strip():
            q["name"] = {"$regex": re.escape(name.strip()), "$options": "i"}
        if mobile and mobile.strip():
            digs = "".join(filter(str.isdigit, mobile.strip()))
            if digs:
                q["$or"] = [{"mobile": {"$regex": digs}}, {"normalized_mobile": {"$regex": digs}}]
        if id_number and id_number.strip():
            q["id_number"] = {"$regex": re.escape(id_number.strip()), "$options": "i"}
        if query and query.strip():
            q_str = query.strip()
            digs = "".join(filter(str.isdigit, q_str))
            or_clauses: List[Dict[str, Any]] = [
                {"name": {"$regex": re.escape(q_str), "$options": "i"}},
                {"id_number": {"$regex": re.escape(q_str), "$options": "i"}},
                {"remarks": {"$regex": re.escape(q_str), "$options": "i"}}
            ]
            if digs:
                or_clauses.append({"mobile": {"$regex": digs}})
                or_clauses.append({"normalized_mobile": {"$regex": digs}})
            q["$or"] = or_clauses

        eff_date = date_filter or date
        if eff_date and eff_date.strip():
            q["record_date"] = eff_date.strip()
        elif start_date and end_date:
            q["record_date"] = {"$gte": start_date.strip(), "$lte": end_date.strip()}
        elif start_date:
            q["record_date"] = {"$gte": start_date.strip()}
        elif end_date:
            q["record_date"] = {"$lte": end_date.strip()}

        eff_status = status_filter or status
        if eff_status and eff_status.lower() != "all":
            q["status"] = {"$regex": f"^{re.escape(eff_status.strip())}$", "$options": "i"}

        if file_id is not None:
            q["file_id"] = file_id

        eff_baki = is_baki if is_baki is not None else baki_only
        if eff_baki is not None and eff_baki:
            q["is_baki"] = 1

        total = mongo_db["office_records"].count_documents(q)
        sort_dir = pymongo.DESCENDING if sort_order.lower() == "desc" else pymongo.ASCENDING
        sort_field = "record_date" if sort_by == "date" else sort_by
        
        cursor = mongo_db["office_records"].find(q, {"_id": 0})\
            .sort([(sort_field, sort_dir), ("id", sort_dir)])\
            .skip((max(1, page) - 1) * page_size)\
            .limit(page_size)
        return list(cursor), total
    except Exception as e:
        print("MongoDB search_records error:", e)
        return [], 0

def get_daily_progress_stats(date_filter: Optional[str] = None, service_type: Optional[str] = None) -> Dict[str, Any]:
    target_date = date_filter or datetime.now().strftime("%Y-%m-%d")
    clean_svc = (service_type or "all").lower().strip()
    if mongo_db is None:
        return {
            "date": target_date, "service_type": clean_svc,
            "daily_total": 0, "all_total": 0,
            "completed": 0, "in_process": 0, "rejected": 0, "baki": 0,
            "services": {}
        }
    try:
        match_all = {}
        match_daily = {"record_date": target_date}
        if clean_svc != "all":
            match_all["service_type"] = clean_svc
            match_daily["service_type"] = clean_svc

        daily_total = mongo_db["office_records"].count_documents(match_daily)
        all_total = mongo_db["office_records"].count_documents(match_all)

        completed = mongo_db["office_records"].count_documents(dict(match_daily, status={"$regex": "^completed$", "$options": "i"}))
        in_process = mongo_db["office_records"].count_documents(dict(match_daily, status={"$regex": "^(inprogress|pending|processing)$", "$options": "i"}))
        rejected = mongo_db["office_records"].count_documents(dict(match_daily, status={"$regex": "^rejected$", "$options": "i"}))
        baki = mongo_db["office_records"].count_documents(dict(match_daily, is_baki=1))

        # Aggregation by service
        pipe = [
            {"$match": {"record_date": target_date}},
            {"$group": {"_id": "$service_type", "count": {"$sum": 1}}}
        ]
        services_map = {}
        for doc in mongo_db["office_records"].aggregate(pipe):
            if doc["_id"]:
                services_map[doc["_id"]] = doc["count"]

        return {
            "date": target_date,
            "service_type": clean_svc,
            "daily_total": daily_total,
            "all_total": all_total,
            "completed": completed,
            "in_process": in_process,
            "rejected": rejected,
            "baki": baki,
            "services": services_map
        }
    except Exception as e:
        print("MongoDB progress stats error:", e)
        return {
            "date": target_date, "service_type": clean_svc,
            "daily_total": 0, "all_total": 0,
            "completed": 0, "in_process": 0, "rejected": 0, "baki": 0,
            "services": {}
        }

def get_all_records_for_export(
    service_type: Optional[str] = None,
    name: Optional[str] = None,
    mobile: Optional[str] = None,
    id_number: Optional[str] = None,
    date_filter: Optional[str] = None,
    file_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    records, _ = search_records(
        service_type=service_type,
        name=name,
        mobile=mobile,
        id_number=id_number,
        date_filter=date_filter,
        file_id=file_id,
        page=1,
        page_size=100000
    )
    return records

def backup_database_json() -> Dict[str, Any]:
    files = get_all_files()
    records, _ = search_records(page=1, page_size=100000)
    users = get_all_master_users()
    return {
        "app_name": "Khodal Office Data Hub",
        "exported_at": datetime.now().isoformat(),
        "database_engine": "mongodb",
        "cluster": "cluster0.nl4cir6.mongodb.net",
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
    for u in users:
        if u.get("username"):
            create_master_user(u["username"], "manish@7575", u.get("full_name"), u.get("role", "master"))
    old_to_new_file_ids = {}
    for f in files:
        new_fid = add_uploaded_file(
            filename=f.get("filename", "restored_file.xlsx"),
            original_filename=f.get("original_filename", "restored_file.xlsx"),
            file_path=f.get("file_path", ""),
            file_type=f.get("file_type", "excel"),
            file_size=f.get("file_size", 0),
            row_count=f.get("row_count", 0),
            service_type=f.get("service_type", "all")
        )
        if f.get("id"):
            old_to_new_file_ids[f["id"]] = new_fid
    restored_records = []
    for r in records:
        rec_copy = dict(r)
        if rec_copy.get("file_id") and rec_copy["file_id"] in old_to_new_file_ids:
            rec_copy["file_id"] = old_to_new_file_ids[rec_copy["file_id"]]
        rec_copy.pop("id", None)
        restored_records.append(rec_copy)
    count = insert_bulk_records(restored_records)
    return {
        "restored_records": count,
        "restored_files": len(files),
        "restored_users": len(users)
    }
