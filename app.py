import os
import shutil
import socket
import webbrowser
import threading
import time
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import io
import hashlib
import csv

from database import (
    init_db,
    backup_database_json,
    restore_database_json,
    verify_user,
    get_file_blob,
    add_uploaded_file,
    get_all_files,
    get_file_by_id,
    delete_uploaded_file,
    clear_all_database_records,
    update_file_row_count,
    insert_bulk_records,
    insert_single_record,
    update_single_record,
    delete_single_record,
    update_record_status,
    search_records,
    get_daily_progress_stats,
    get_all_records_for_export
)
from excel_service import (
    parse_service_excel_or_csv,
    export_records_to_excel
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)


def get_local_ip() -> str:
    """Detect LAN IP address so office coworkers can connect."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Khodal Office Data Hub", lifespan=lifespan)

# Allow CORS for network sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/api/auth/login")
async def login(credentials: Dict[str, str]):
    """Authenticate master user (manish / manish@7575)."""
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    user = verify_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid User ID or Password. Please check your credentials.")
    
    token = hashlib.sha256(f"{user['username']}:{time.time()}:khodal_office_secret".encode()).hexdigest()
    return {
        "status": "success",
        "message": f"Welcome, {user['full_name']}!",
        "token": token,
        "user": user
    }


@app.get("/api/auth/me")
async def get_current_user():
    """Return default master user profile."""
    return {
        "status": "success",
        "user": {
            "username": "manish",
            "full_name": "Manish",
            "role": "master"
        }
    }


@app.post("/api/auth/logout")
async def logout():
    return {"status": "success", "message": "Logged out successfully"}


@app.get("/api/info")
async def get_system_info():
    lan_ip = get_local_ip()
    return {
        "app_name": "Khodal Office Data Hub",
        "lan_ip": lan_ip,
        "local_url": "http://localhost:8000",
        "office_share_url": f"http://{lan_ip}:8000"
    }


@app.get("/api/progress")
async def get_progress(
    date: Optional[str] = Query(None, description="Date filter YYYY-MM-DD"),
    service_type: Optional[str] = Query(None, description="Service category")
):
    stats = get_daily_progress_stats(date_str=date, service_type=service_type)
    return stats


@app.get("/api/records")
async def list_records(
    service_type: Optional[str] = Query("all", description="ucaadhar, aadhar_online, pancard, aayushman, or all"),
    name: Optional[str] = Query(None, description="Search by person / client name"),
    mobile: Optional[str] = Query(None, description="Search by mobile number"),
    id_number: Optional[str] = Query(None, description="Search by SID, SRN, Ration or Card Number"),
    query: Optional[str] = Query(None, description="Global search across all columns"),
    date: Optional[str] = Query(None, description="Filter by exact date YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="Filter by status (Completed, InProcess, etc.)"),
    baki_only: bool = Query(False, description="Filter only records with baki / pending action"),
    file_id: Optional[int] = Query(None, description="Filter by uploaded file ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=200)
):
    items, total_count = search_records(
        service_type=service_type,
        name=name,
        mobile=mobile,
        id_number=id_number,
        query=query,
        date_filter=date,
        status=status,
        baki_only=baki_only,
        file_id=file_id,
        page=page,
        page_size=page_size
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return {
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "service_type": service_type
    }


@app.post("/api/records")
async def create_record(data: Dict[str, Any]):
    if not data.get("name") and not data.get("id_number") and not data.get("mobile"):
        raise HTTPException(status_code=400, detail="Please provide at least a Name, ID Number, or Mobile Number.")
    record_id = insert_single_record(data)
    return {"status": "success", "id": record_id, "message": "Record added successfully"}


@app.put("/api/records/{record_id}")
async def edit_record(record_id: int, data: Dict[str, Any]):
    updated = update_single_record(record_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success", "message": "Record updated successfully"}


@app.patch("/api/records/{record_id}/status")
async def toggle_status(record_id: int, data: Dict[str, Any]):
    new_status = data.get("status", "Completed")
    updated = update_record_status(record_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success", "message": f"Status updated to {new_status}"}


@app.delete("/api/records/{record_id}")
async def remove_record(record_id: int):
    deleted = delete_single_record(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success", "message": "Record deleted"}


@app.post("/api/upload")
async def upload_daily_file(
    file: UploadFile = File(...),
    service_type: Optional[str] = Form("auto"),
    file_date: Optional[str] = Form("")
):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in [".xlsx", ".xls", ".csv", ".xlsm"]:
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls) and CSV (.csv) files are supported.")
        
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{filename}"
    saved_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        file_bytes = await file.read()
        with open(saved_path, "wb") as buffer:
            buffer.write(file_bytes)
            
        file_size = len(file_bytes)
        
        # 1. Parse data according to service rules
        records, summary = parse_service_excel_or_csv(saved_path, 0, forced_service=service_type)
        actual_svc = summary.get("service_type", service_type)
        sheets_count = summary.get("sheets_count", 1)
        sheet_names = summary.get("sheet_names", [])
        
        # 2. Add file record in DB with raw binary BLOB stored inside SQLite
        file_id = add_uploaded_file(
            filename=filename,
            service_type=actual_svc,
            file_date=file_date or (records[0]["record_date"] if records else ""),
            stored_path=saved_path,
            file_size=file_size,
            row_count=0,
            file_blob=file_bytes,
            sheet_names=sheet_names
        )
        
        # Assign file_id to records
        for r in records:
            r["file_id"] = file_id
            
        # 3. Bulk insert parsed records
        row_count = insert_bulk_records(records)
        update_file_row_count(file_id, row_count)
        
        sheets_count = summary.get("sheets_count", 1)
        sheet_names = summary.get("sheet_names", [])
        sheet_info = f" across {sheets_count} sheets ({', '.join(sheet_names[:3])}{'...' if len(sheet_names) > 3 else ''})" if sheets_count > 1 else ""

        return {
            "status": "success",
            "file_id": file_id,
            "filename": filename,
            "service_type": actual_svc,
            "imported_rows": row_count,
            "sheets_count": sheets_count,
            "sheet_names": sheet_names,
            "message": f"Successfully uploaded and imported {row_count} records{sheet_info} for {actual_svc.upper()}!"
        }
    except Exception as e:
        if os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.get("/api/files")
async def list_files():
    return get_all_files()


@app.get("/api/files/{file_id}/download")
async def download_original_file(file_id: int):
    file_blob, filename = get_file_blob(file_id)
    if file_blob:
        return StreamingResponse(
            io.BytesIO(file_blob),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    file_info = get_file_by_id(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found in database")
    stored_path = file_info.get("stored_path")
    if stored_path and os.path.exists(stored_path):
        return FileResponse(
            path=stored_path,
            filename=file_info.get("filename", "download.xlsx"),
            media_type="application/octet-stream"
        )
    raise HTTPException(status_code=404, detail="Physical file missing and no database blob available")


@app.delete("/api/files/{file_id}")
async def remove_file(file_id: int):
    deleted = delete_uploaded_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File could not be deleted")
    return {"status": "success", "message": "File and associated records deleted"}


@app.delete("/api/files")
async def clear_all_files_endpoint():
    clear_all_database_records()
    return {"status": "success", "message": "All files and records cleared successfully"}


@app.get("/api/export")
async def export_excel(
    service_type: Optional[str] = Query("all"),
    name: Optional[str] = Query(None),
    mobile: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None),
    date: Optional[str] = Query(None)
):
    records = get_all_records_for_export(
        service_type=service_type,
        name=name,
        mobile=mobile,
        id_number=id_number,
        date_filter=date
    )
    if not records:
        raise HTTPException(status_code=404, detail="No matching records found to export.")
        
    export_path = export_records_to_excel(records, EXPORT_DIR, service_type=service_type)
    filename = os.path.basename(export_path)
    
    return FileResponse(
        path=export_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/api/templates/{template_name}")
async def download_excel_template(template_name: str):
    allowed_templates = {
        "master": "Khodal_Office_Master_Template.xlsx",
        "ucaadhar": "Template_1_UC_Aadhaar.xlsx",
        "aadhar_online": "Template_2_Aadhaar_Online.xlsx",
        "pancard": "Template_3_PAN_Card.xlsx",
        "aayushman": "Template_4_Ayushman_Card.xlsx",
    }
    filename = allowed_templates.get(template_name.lower())
    if not filename:
        raise HTTPException(status_code=404, detail="Template not found. Available: master, ucaadhar, aadhar_online, pancard, aayushman")

    file_path = os.path.join(TEMPLATE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Template file '{filename}' not found on server")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/api/export/csv")
async def export_csv(
    service_type: Optional[str] = Query("all"),
    name: Optional[str] = Query(None),
    mobile: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None),
    date: Optional[str] = Query(None)
):
    records = get_all_records_for_export(
        service_type=service_type,
        name=name,
        mobile=mobile,
        id_number=id_number,
        date_filter=date
    )
    if not records:
        raise HTTPException(status_code=404, detail="No matching records found to export.")

    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ["Sr No", "Service", "Date", "Name", "ID Number", "Mobile No", "Status", "Amount", "Remarks"]
    writer.writerow(headers)
    
    for idx, r in enumerate(records, start=1):
        writer.writerow([
            idx,
            r.get("service_type", "").upper(),
            r.get("record_date", ""),
            r.get("name", ""),
            r.get("id_number", ""),
            r.get("mobile", ""),
            r.get("status", "") or r.get("pan_type", ""),
            r.get("fee_amt", 0.0),
            r.get("remark", "")
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="Khodal_{service_type}_Export.csv"'}
    )



@app.get("/api/database/backup")
async def download_database_backup():
    """Download complete database backup with all files and records."""
    data = backup_database_json()
    timestamp = datetime.now().strftime("%d-%m-%Y_%H%M")
    filename = f"Khodal_Office_DB_Backup_{timestamp}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/database/restore")
async def restore_database_backup(file: UploadFile = File(...)):
    """Restore database from uploaded JSON backup file."""
    try:
        content = await file.read()
        payload = json.loads(content.decode("utf-8"))
        res = restore_database_json(payload)
        return {
            "status": "success",
            "message": f"Successfully restored {res.get('records_restored', 0)} records and {res.get('files_restored', 0)} files!",
            **res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to restore backup: {str(e)}")


# Serve single page UI and data assets
DATA_DIR = os.path.join(BASE_DIR, "data")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.exists(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
async def serve_index():
    root_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(root_index):
        return FileResponse(root_index)
    static_index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse("<h1>Khodal Office Hub: index.html not found</h1>")


def open_browser(port: int = 8000):
    time.sleep(1.2)
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 65)
    lan_ip = get_local_ip()
    print("🚀 KHODAL OFFICE DATA HUB - FIELD-DIVIDED DAILY WORK TRACKER")
    print(f"📍 Local Access:        http://localhost:{port}")
    print(f"🌐 Office LAN Share:    http://{lan_ip}:{port}")
    print("=" * 65)
    
    if os.environ.get("ENVIRONMENT") != "production" and not os.environ.get("PORT"):
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
