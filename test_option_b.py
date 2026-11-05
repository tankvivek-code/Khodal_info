import requests
import sqlite3
import os

BASE_URL = "http://localhost:8000"

print("1. Checking server health...")
r = requests.get(f"{BASE_URL}/api/info")
assert r.status_code == 200, f"Failed info: {r.text}"
print("Server is healthy:", r.json())

# Clean up any test file IDs
for fid in [58, 59]:
    try:
        requests.delete(f"{BASE_URL}/api/files/{fid}")
    except Exception:
        pass

print("2. Uploading Template_1_UC_Aadhaar.xlsx...")
file_path = "templates/Template_1_UC_Aadhaar.xlsx"
assert os.path.exists(file_path), "Template file not found"

with open(file_path, "rb") as f:
    files = {"file": ("Template_1_UC_Aadhaar.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"service_type": "auto"}
    res = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)

assert res.status_code == 200, f"Upload failed: {res.text}"
upload_res = res.json()
print("Upload result:", upload_res)
file_id = upload_res["file_id"]
imported_rows = upload_res["imported_rows"]
print(f"Imported {imported_rows} rows with file_id {file_id}")

print("3. Querying /api/records...")
r_rec = requests.get(f"{BASE_URL}/api/records")
data_rec = r_rec.json()
print(f"Total records in API: {data_rec['total_count']}")
assert data_rec["total_count"] >= imported_rows

print("4. Directly querying SQLite database data/khodal_office.db table 'office_records'...")
conn = sqlite3.connect("data/khodal_office.db")
cursor = conn.cursor()
cursor.execute("SELECT count(*) FROM office_records WHERE file_id = ?", (file_id,))
count_in_db = cursor.fetchone()[0]
print(f"Records directly verified inside data/khodal_office.db (office_records): {count_in_db}")
assert count_in_db == imported_rows

print("5. Cleaning up test upload (strictly zero mock data policy)...")
del_res = requests.delete(f"{BASE_URL}/api/files/{file_id}")
print("Delete result:", del_res.json())

cursor.execute("SELECT count(*) FROM office_records WHERE file_id = ?", (file_id,))
remaining = cursor.fetchone()[0]
print(f"Remaining records in DB: {remaining}")
assert remaining == 0
conn.close()

print(">>> ALL VERIFICATIONS PASSED! Option B saves 100% directly to hard drive SQLite database data/khodal_office.db! <<<")
