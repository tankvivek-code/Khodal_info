import os
import re
import csv
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

DATE_REGEX = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")
PHONE_REGEX = re.compile(r"\b[6-9]\d{9}\b")


def clean_header_name(header: str) -> str:
    s = str(header).lower().strip()
    s = re.sub(r"[_\-\.\(\)\[\]\/\\:]+", " ", s)
    return " ".join(s.split())


def detect_service_type_from_content(headers: List[str], file_path: str) -> str:
    cleaned = [clean_header_name(h) for h in headers]
    joined = " ".join(cleaned)

    if any("sid" in h for h in cleaned):
        return "ucaadhar"
    if any("srn" in h for h in cleaned):
        return "aadhar_online"
    if any("pan change" in h or "pan new" in h or "pancard" in h for h in cleaned):
        return "pancard"
    if any("ration" in h or "aayushman" in h or "ayushman" in h for h in cleaned):
        return "aayushman"

    # Check filename
    fname = os.path.basename(file_path).lower()
    if "ucaadhar" in fname or "uc_aadhar" in fname or "sid" in fname:
        return "ucaadhar"
    if "aadhar_online" in fname or "online_aadhar" in fname or "srn" in fname:
        return "aadhar_online"
    if "pan" in fname:
        return "pancard"
    if "aayushman" in fname or "ayushman" in fname or "ration" in fname:
        return "aayushman"

    return "general"


def normalize_date_str(val: Any) -> str:
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    m = DATE_REGEX.search(s)
    if not m:
        return ""
    raw = m.group(1).replace("/", "-")
    parts = raw.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:
            # YYYY-MM-DD
            return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        else:
            # DD-MM-YYYY or DD-MM-YY
            year = parts[2]
            if len(year) == 2:
                year = f"20{year}"
            elif len(year) == 3: # e.g. 206 -> 2026
                year = "2026"
            return f"{year}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    return s


def clean_phone(val: Any) -> Tuple[str, str]:
    if pd.isna(val) or val is None:
        return "", ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if "e+" in s.lower():
        try:
            s = f"{int(float(s))}"
        except Exception:
            pass
    digits = re.sub(r"\D", "", s)
    return s, digits


def parse_single_sheet_df(
    df: pd.DataFrame,
    file_path: str,
    file_id: int,
    sheet_name: str = "",
    forced_service: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str, List[str]]:
    raw_headers = [str(c).strip() for c in df.columns]
    
    # Check if sheet_name itself suggests a service
    sheet_name_clean = clean_header_name(sheet_name)
    inferred_service = None
    if "srn" in sheet_name_clean or "online" in sheet_name_clean:
        inferred_service = "aadhar_online"
    elif "pan" in sheet_name_clean:
        inferred_service = "pancard"
    elif "ration" in sheet_name_clean or "ayushman" in sheet_name_clean or "aayushman" in sheet_name_clean:
        inferred_service = "aayushman"
    elif "sid" in sheet_name_clean or "uc" in sheet_name_clean:
        inferred_service = "ucaadhar"

    service_type = (
        forced_service
        if forced_service and forced_service != "auto"
        else (inferred_service or detect_service_type_from_content(raw_headers, file_path))
    )

    records = []
    # Check if sheet_name is a date
    sheet_date = normalize_date_str(sheet_name)
    current_date = sheet_date if sheet_date else datetime.now().strftime("%Y-%m-%d")

    col_names = [clean_header_name(c) for c in raw_headers]

    def find_col_idx(*synonyms):
        for syn in synonyms:
            for idx, c in enumerate(col_names):
                if syn in c or c in syn:
                    return idx
        return -1

    idx_date = find_col_idx("date")
    idx_name = find_col_idx("name", "client name", "party")
    idx_sid = find_col_idx("sid number", "sid")
    idx_srn = find_col_idx("srn no", "srn number", "srn")
    idx_ration = find_col_idx("ration card no", "ration", "aayushman", "ayushman")
    idx_pan = find_col_idx("pan change", "pan new", "pan")
    idx_mobile = find_col_idx("mo", "mobile", "mobile number", "contact")
    idx_status = find_col_idx("status")
    idx_total = find_col_idx("total", "total amt", "amount")
    idx_fee = find_col_idx("fee")
    idx_remark = find_col_idx("remark", "remarks", "others", "note")

    for _, row in df.iterrows():
        row_vals = [str(val).strip() if pd.notna(val) and val is not None and str(val).lower() != "nan" else "" for val in row.values]
        
        # Check if empty row
        if not any(row_vals):
            continue

        # Check if this row is a date section header (e.g. '2026-10-01', '', '', '')
        date_candidates = [v for v in row_vals if DATE_REGEX.search(v)]
        non_empty = [v for v in row_vals if v]
        
        if len(non_empty) == 1 and date_candidates:
            current_date = normalize_date_str(date_candidates[0])
            continue
        elif date_candidates and (idx_date == -1 or (idx_name != -1 and not row_vals[idx_name])):
            # Has date but no name -> date divider row
            current_date = normalize_date_str(date_candidates[0])
            continue

        # Extract record fields
        rec_date = ""
        if idx_date != -1 and idx_date < len(row_vals) and row_vals[idx_date]:
            parsed_d = normalize_date_str(row_vals[idx_date])
            if parsed_d:
                rec_date = parsed_d
                current_date = parsed_d
        
        if not rec_date:
            rec_date = current_date

        name = row_vals[idx_name] if idx_name != -1 and idx_name < len(row_vals) else ""
        raw_mob = row_vals[idx_mobile] if idx_mobile != -1 and idx_mobile < len(row_vals) else ""
        remark = row_vals[idx_remark] if idx_remark != -1 and idx_remark < len(row_vals) else ""
        status = row_vals[idx_status] if idx_status != -1 and idx_status < len(row_vals) else ""
        total_amt = 0.0
        fee_amt = 0.0
        id_num = ""
        pan_type = ""

        # Normalize status string
        if status.lower() in ["inprocess", "in process", "in-process"]:
            status = "InProcess"
        elif status.lower() in ["completed", "complete", "done"]:
            status = "Completed"

        # Service-specific mappings
        if service_type == "ucaadhar":
            if idx_sid != -1 and idx_sid < len(row_vals):
                id_num = row_vals[idx_sid]
            
            # If total column exists
            if idx_total != -1 and idx_total < len(row_vals):
                try:
                    total_amt = float(row_vals[idx_total])
                except Exception:
                    if row_vals[idx_total].upper() == "NEW":
                        remark = f"NEW {remark}".strip()

            # Second fee column
            if idx_fee != -1 and idx_fee < len(row_vals):
                try:
                    fee_amt = float(row_vals[idx_fee])
                except Exception:
                    pass
            elif len(row_vals) >= 6 and not fee_amt:
                try:
                    fee_amt = float(row_vals[5])
                except Exception:
                    pass

            if not raw_mob and remark:
                m_match = PHONE_REGEX.search(remark)
                if m_match:
                    raw_mob = m_match.group(0)

            if not status:
                status = "Completed"

        elif service_type == "aadhar_online":
            if idx_srn != -1 and idx_srn < len(row_vals):
                id_num = row_vals[idx_srn]
            if not status:
                if any(w in remark.lower() for w in ["baki", "not resiv", "not reciv", "name baki"]):
                    status = "Pending"
                else:
                    status = "Completed"

        elif service_type == "pancard":
            if idx_pan != -1 and idx_pan < len(row_vals):
                pan_type = row_vals[idx_pan]
            status = "Completed"

        elif service_type == "aayushman":
            if idx_ration != -1 and idx_ration < len(row_vals):
                id_num = row_vals[idx_ration]
            if "ok" in remark.lower():
                status = "Completed"
            elif "renew" in remark.lower():
                status = "Renew"
            elif "new" in remark.lower():
                status = "New"
            else:
                status = "InProcess"

        else:
            if idx_sid != -1: id_num = row_vals[idx_sid]
            elif idx_srn != -1: id_num = row_vals[idx_srn]
            elif idx_ration != -1: id_num = row_vals[idx_ration]

        # Check if record has at least Name or ID number or Mobile
        if name or id_num or raw_mob:
            display_mob, norm_mob = clean_phone(raw_mob)
            is_baki = 1 if any(w in remark.lower() for w in ["baki", "not reciv", "not resiv", "no reciv", "payment baki", "name baki"]) else 0
            
            records.append({
                "file_id": file_id,
                "service_type": service_type,
                "record_date": rec_date,
                "name": name,
                "mobile": display_mob,
                "normalized_mobile": norm_mob,
                "id_number": id_num,
                "pan_type": pan_type,
                "status": status,
                "total_amt": total_amt,
                "fee_amt": fee_amt,
                "remark": remark,
                "is_baki": is_baki,
                "extra_data": {}
            })

    return records, service_type, raw_headers


def parse_service_excel_or_csv(file_path: str, file_id: int, forced_service: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses any office spreadsheet (Excel or CSV), reading ALL sheets if multiple exist.
    """
    ext = os.path.splitext(file_path)[1].lower()
    sheets_dict = {}

    if ext in [".xlsx", ".xlsm"]:
        sheets_dict = pd.read_excel(file_path, sheet_name=None, engine="openpyxl", dtype=str)
    elif ext == ".xls":
        sheets_dict = pd.read_excel(file_path, sheet_name=None, engine="xlrd", dtype=str)
    elif ext == ".csv":
        try:
            df = pd.read_csv(file_path, dtype=str, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            try:
                df = pd.read_csv(file_path, dtype=str, encoding="latin1", on_bad_lines="skip")
            except Exception:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    parsed_rows = list(csv.reader(lines))
                if parsed_rows:
                    max_cols = max(len(r) for r in parsed_rows)
                    header = parsed_rows[0] + [f"Col_{i}" for i in range(len(parsed_rows[0]), max_cols)]
                    padded = [r + [""] * (max_cols - len(r)) for r in parsed_rows[1:]]
                    df = pd.DataFrame(padded, columns=header)
                else:
                    df = pd.DataFrame()
        sheets_dict = {"CSV": df}
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    all_records = []
    detected_services = []
    all_headers = []

    for s_name, df_sheet in sheets_dict.items():
        if df_sheet is None or df_sheet.empty:
            continue
        records, svc, headers = parse_single_sheet_df(
            df=df_sheet,
            file_path=file_path,
            file_id=file_id,
            sheet_name=str(s_name),
            forced_service=forced_service
        )
        if records:
            all_records.extend(records)
            detected_services.append(svc)
            all_headers.extend(headers)

    # Determine predominant service type
    if forced_service and forced_service != "auto":
        overall_service = forced_service
    elif detected_services:
        overall_service = max(set(detected_services), key=detected_services.count)
    else:
        overall_service = "general"

    summary = {
        "service_type": overall_service,
        "total_rows_parsed": len(all_records),
        "sheets_count": len(sheets_dict),
        "sheet_names": list(sheets_dict.keys()),
        "headers": all_headers
    }
    return all_records, summary


def export_records_to_excel(records: List[Dict[str, Any]], export_dir: str, service_type: Optional[str] = None) -> str:
    os.makedirs(export_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    svc_prefix = service_type.upper() if service_type and service_type != "all" else "ALL_SERVICES"
    output_filename = f"Khodal_{svc_prefix}_{timestamp}.xlsx"
    output_path = os.path.join(export_dir, output_filename)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Office Records"

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Deep Blue
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    cell_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    # Pick column headers based on service type
    if service_type == "ucaadhar":
        headers = ["#", "Date", "SID Number", "Name", "Status", "Total Amt", "Fee Amt", "Mobile", "Others / Remarks"]
    elif service_type == "aadhar_online":
        headers = ["#", "Date", "Name", "SRN Number", "Mobile No", "Status", "Remarks"]
    elif service_type == "pancard":
        headers = ["#", "Date", "Name", "PAN Change / New", "Mobile Number", "Status", "Remarks"]
    elif service_type == "aayushman":
        headers = ["#", "Date", "Ration / Ayushman No", "Name", "Mobile No", "Status", "Remarks"]
    else:
        headers = ["#", "Service", "Date", "Name", "ID Number", "Mobile No", "Status / Type", "Fee", "Remarks"]

    ws.append(headers)

    for col_idx, cell in enumerate(ws[1], start=1):
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
        ws.row_dimensions[1].height = 26

    # Write data
    for idx, r in enumerate(records, start=1):
        if service_type == "ucaadhar":
            row_data = [
                idx, r.get("record_date", ""), r.get("id_number", ""), r.get("name", ""),
                r.get("status", ""), r.get("total_amt", 0.0), r.get("fee_amt", 0.0),
                r.get("mobile", ""), r.get("remark", "")
            ]
        elif service_type == "aadhar_online":
            row_data = [
                idx, r.get("record_date", ""), r.get("name", ""), r.get("id_number", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        elif service_type == "pancard":
            row_data = [
                idx, r.get("record_date", ""), r.get("name", ""), r.get("pan_type", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        elif service_type == "aayushman":
            row_data = [
                idx, r.get("record_date", ""), r.get("id_number", ""), r.get("name", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        else:
            row_data = [
                idx, r.get("service_type", "").upper(), r.get("record_date", ""), r.get("name", ""),
                r.get("id_number", ""), r.get("mobile", ""), r.get("status", "") or r.get("pan_type", ""),
                r.get("fee_amt", 0.0), r.get("remark", "")
            ]

        ws.append(row_data)
        row_num = idx + 1
        for col_idx, cell in enumerate(ws[row_num], start=1):
            cell.font = cell_font
            cell.border = thin_border
            if col_idx in [1, 2, 6]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
        ws.row_dimensions[row_num].height = 20

    # Auto size columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 45)

    wb.save(output_path)
    return output_path
