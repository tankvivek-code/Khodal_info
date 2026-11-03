import json
import os
import sqlite3
from excel_service import parse_service_excel_or_csv
from database import (
    init_db,
    add_uploaded_file,
    insert_bulk_records,
    clear_all_database_records,
    get_daily_progress_stats,
    get_all_files,
    DB_PATH
)

init_db()
clear_all_database_records()

# 1. Master multi-sheet file
master_path = "uploads/Khodal_Office_Master.xlsx"
recs_master, summary_master = parse_service_excel_or_csv(master_path, 1, forced_service="auto")
print(f"Master file parsed: {len(recs_master)} records across {summary_master['sheets_count']} sheets.")

# We will record the 4 distinct daily service files in uploaded_files:
file_definitions = [
    {
        "filename": "UC_Aadhaar_Daily.csv",
        "service": "ucaadhar",
        "date": "2026-10-01",
        "path": "uploads/UC_Aadhaar_Daily.csv",
        "filter": lambda r: r["service_type"] == "ucaadhar"
    },
    {
        "filename": "Aadhaar_Online_Daily.csv",
        "service": "aadhar_online",
        "date": "2026-10-01",
        "path": "uploads/Aadhaar_Online_Daily.csv",
        "filter": lambda r: r["service_type"] == "aadhar_online"
    },
    {
        "filename": "PAN_Card_Daily.csv",
        "service": "pancard",
        "date": "2026-07-01",
        "path": "uploads/PAN_Card_Daily.csv",
        "filter": lambda r: r["service_type"] == "pancard"
    },
    {
        "filename": "Ayushman_Card_Daily.csv",
        "service": "aayushman",
        "date": "2026-07-01",
        "path": "uploads/Ayushman_Card_Daily.csv",
        "filter": lambda r: r["service_type"] == "aayushman"
    },
]

all_final_records = []
all_files_metadata = []

# Insert master file into uploaded_files tracking
master_file_id = add_uploaded_file(
    filename="Khodal_Office_Master.xlsx",
    service_type="general",
    file_date="2026-10-01",
    stored_path=master_path,
    file_size=os.path.getsize(master_path),
    row_count=len(recs_master)
)

all_files_metadata.append({
    "id": master_file_id,
    "filename": "Khodal_Office_Master.xlsx",
    "service_type": "general",
    "row_count": len(recs_master),
    "file_size": os.path.getsize(master_path),
    "uploaded_at": "2026-11-03 12:35:00"
})

for f_def in file_definitions:
    f_path = f_def["path"]
    f_size = os.path.getsize(f_path) if os.path.exists(f_path) else 15000
    sub_recs = [r for r in recs_master if f_def["filter"](r)]
    
    f_id = add_uploaded_file(
        filename=f_def["filename"],
        service_type=f_def["service"],
        file_date=f_def["date"],
        stored_path=f_path,
        file_size=f_size,
        row_count=len(sub_recs)
    )
    
    for r in sub_recs:
        r["file_id"] = f_id
        all_final_records.append(r)
        
    all_files_metadata.append({
        "id": f_id,
        "filename": f_def["filename"],
        "service_type": f_def["service"],
        "row_count": len(sub_recs),
        "file_size": f_size,
        "uploaded_at": "2026-11-03 12:35:00"
    })

# Bulk insert into database
insert_bulk_records(all_final_records)

# Verify DB state
stats = get_daily_progress_stats()
print("Database loaded stats:", stats)

# Fetch all records with DB ids
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM office_records ORDER BY id DESC")
db_rows = [dict(r) for r in c.fetchall()]
conn.close()

print(f"Exporting {len(db_rows)} real office records to data/records.json and data/records.js...")

with open("data/records.json", "w", encoding="utf-8") as f:
    json.dump(db_rows, f, indent=2, ensure_ascii=False)

with open("data/records.js", "w", encoding="utf-8") as f:
    f.write(f"window.KHODAL_RECORDS = {json.dumps(db_rows, ensure_ascii=False)};\n")
    f.write(f"window.KHODAL_INITIAL_FILES = {json.dumps(all_files_metadata, ensure_ascii=False)};\n")

print("Successfully written data/records.json and data/records.js!")
