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

    if any("sid" in h or "enrolment" in h or "enrollment" in h for h in cleaned):
        return "ucaadhar"
    if any("srn" in h for h in cleaned):
        return "aadhar_online"
    if any("pan change" in h or "pan new" in h or "pancard" in h for h in cleaned):
        return "pancard"
    if any("ration" in h or "aayushman" in h or "ayushman" in h for h in cleaned):
        return "aayushman"

    # Check filename
    fname = os.path.basename(file_path).lower()
    if "ucaadhar" in fname or "uc_aadhar" in fname or "sid" in fname or "enrol" in fname:
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
    # Convert df to list of row lists, preserving header row if present
    raw_rows = []
    cols_as_str = [str(c).strip() for c in df.columns]
    if any(not c.isdigit() and str(c).lower() != "nan" and not c.startswith("Unnamed:") for c in cols_as_str):
        raw_rows.append(cols_as_str)
    for _, r in df.iterrows():
        raw_rows.append([str(val).strip() if pd.notna(val) and val is not None and str(val).lower() != "nan" else "" for val in r.values])

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

    first_row_headers = raw_rows[0] if raw_rows else []
    service_type = (
        forced_service
        if forced_service and forced_service != "auto"
        else (inferred_service or detect_service_type_from_content(first_row_headers, file_path))
    )

    records = []
    sheet_date = normalize_date_str(sheet_name)
    current_date = sheet_date if sheet_date else datetime.now().strftime("%Y-%m-%d")

    headers = []
    idx_date = -1
    idx_name = -1
    idx_sid = -1
    idx_srn = -1
    idx_pan = -1
    idx_ration = -1
    idx_mobile = -1
    idx_status = -1
    idx_total = -1
    idx_fee = -1
    idx_remark = -1

    def update_columns(row_cells):
        nonlocal headers, idx_date, idx_name, idx_sid, idx_srn, idx_pan, idx_ration, idx_mobile, idx_status, idx_total, idx_fee, idx_remark
        headers = [clean_header_name(c) for c in row_cells]
        def find_c(*syns, exclude=()):
            for syn in syns:
                for i, h in enumerate(headers):
                    if not h:
                        continue
                    if any(ex in h for ex in exclude):
                        continue
                    if h == syn or (len(syn) >= 3 and syn in h) or (len(h) >= 3 and h in syn) or (h in ["mo", "mo.", "mob"] and syn in ["mo", "mobile"]):
                        return i
            return -1
        idx_date = find_c("date", "dt", exclude=["enrol", "enroll"])
        idx_name = find_c("name", "party", "client")
        idx_sid = find_c("sid", "enrolment", "enrollment")
        idx_srn = find_c("srn")
        idx_pan = find_c("pan")
        idx_ration = find_c("ration", "ayushman", "aayushman")
        idx_mobile = find_c("mobile", "mo", "contact", "phone")
        idx_status = find_c("status")
        idx_total = find_c("total", "amount", "amt")
        idx_fee = find_c("fee")
        idx_remark = find_c("remark", "others", "note")

    for row_vals in raw_rows:
        if not any(row_vals):
            continue

        joined = " ".join(row_vals).upper()

        # Check if header row
        if any(k in joined for k in ["ENROLMENT", "SID NUMBER", "SRN", "RATION CARD", "PAN CHANGE"]) or (
            any(row_vals[i].upper() in ["NO", "SLNO", "SR NO", "SRNO"] for i in range(min(2, len(row_vals))))
            and any(k in joined for k in ["NAME", "STATUS", "TOTAL", "SID", "DATE"])
        ):
            update_columns(row_vals)
            continue

        if not headers:
            update_columns(["SLNO", "ENROLMENT", "STATUS", "TOTAL", "FEE", "OTHERS"])

        # Check date divider
        has_status = any(st in joined for st in ["COMPLETED", "COMPLET", "INPROCESS", "IN PROCESS", "REJECT", "PENDING"])
        date_candidates = [normalize_date_str(v) for v in row_vals if normalize_date_str(v) and len(str(v).strip()) <= 15]

        if date_candidates and not has_status:
            first_cell = row_vals[0].replace(".0", "").strip() if row_vals else ""
            if not first_cell.isdigit() or len(first_cell) > 4:
                current_date = date_candidates[0]
                continue

        # Subtotal row check: no status, no SID regex, and all non-empty are digits
        non_empty = [s for s in row_vals if s]
        if not has_status and not any(re.search(r"\bS\d{10,30}\b", s, re.I) for s in non_empty) and all(s.replace(".", "", 1).isdigit() for s in non_empty):
            continue

        rec_date = current_date
        if idx_date != -1 and idx_date < len(row_vals) and row_vals[idx_date]:
            pd_date = normalize_date_str(row_vals[idx_date])
            if pd_date:
                rec_date = pd_date
                current_date = pd_date

        name = row_vals[idx_name] if idx_name != -1 and idx_name < len(row_vals) else ""
        id_num = ""
        rec_sid = ""

        for s in row_vals:
            m_sid = re.search(r"\b(S\d{10,30})\b", s, re.I)
            if m_sid:
                rec_sid = m_sid.group(1)
                break

        if rec_sid:
            id_num = rec_sid
        elif idx_sid != -1 and idx_sid < len(row_vals) and row_vals[idx_sid]:
            val = row_vals[idx_sid]
            m_sid = re.search(r"\b(S\d{10,30})\b", val, re.I)
            if m_sid:
                id_num = m_sid.group(1)
            elif not val.replace(".", "").isdigit():
                if not name:
                    name = val

        if idx_srn != -1 and idx_srn < len(row_vals) and row_vals[idx_srn]:
            id_num = row_vals[idx_srn]
        if idx_ration != -1 and idx_ration < len(row_vals) and row_vals[idx_ration]:
            id_num = row_vals[idx_ration]

        status = "Completed"
        if idx_status != -1 and idx_status < len(row_vals) and row_vals[idx_status]:
            raw_st = row_vals[idx_status].lower()
            if "inprocess" in raw_st or "process" in raw_st:
                status = "InProcess"
            elif "reject" in raw_st:
                status = "Reject"
            elif "pending" in raw_st:
                status = "Pending"
            elif "complete" in raw_st:
                status = "Completed"
        else:
            for s in row_vals:
                sl = s.lower()
                if "inprocess" in sl or "process" in sl:
                    status = "InProcess"
                    break
                elif "reject" in sl:
                    status = "Reject"
                    break
                elif "pending" in sl:
                    status = "Pending"
                    break

        total_amt = 0.0
        fee_amt = 0.0
        if idx_total != -1 and idx_total < len(row_vals) and row_vals[idx_total]:
            try:
                total_amt = float(row_vals[idx_total])
            except Exception:
                pass
        if idx_fee != -1 and idx_fee < len(row_vals) and row_vals[idx_fee]:
            try:
                fee_amt = float(row_vals[idx_fee])
            except Exception:
                pass
        elif idx_total != -1 and idx_total + 1 < len(row_vals) and row_vals[idx_total + 1]:
            try:
                fee_amt = float(row_vals[idx_total + 1])
            except Exception:
                pass

        remark = row_vals[idx_remark] if idx_remark != -1 and idx_remark < len(row_vals) else ""
        raw_mob = row_vals[idx_mobile] if idx_mobile != -1 and idx_mobile < len(row_vals) else ""
        if not raw_mob:
            m_ph = PHONE_REGEX.search(joined)
            if m_ph:
                raw_mob = m_ph.group(0)

        pan_type = ""
        if idx_pan != -1 and idx_pan < len(row_vals):
            pan_type = row_vals[idx_pan]

        if not name:
            m_nm = re.search(r"NAME[\s\-:]+([A-Za-z\s]+)", joined, re.I)
            if m_nm:
                name = m_nm.group(1).strip()
        if not name and len(row_vals) > 5 and row_vals[5] and not row_vals[5].replace(".", "").isdigit():
            c5_up = row_vals[5].upper()
            if not any(kw in c5_up for kw in ["SPEED", "ADDRESS", "MOBILE", "RIPIT", "CALL"]):
                name = row_vals[5]
        if not name and id_num:
            name = "Aadhaar Client"

        # Determine service for this specific record
        row_svc = service_type
        clean_id = id_num.strip().upper()
        if not forced_service or forced_service == "auto":
            if clean_id.startswith("SID") or (clean_id.startswith("S") and len(clean_id) >= 18):
                row_svc = "ucaadhar"
            elif clean_id.startswith("SRN") or (clean_id.startswith("S") and 10 <= len(clean_id) <= 16):
                row_svc = "aadhar_online"
            elif pan_type or idx_pan != -1:
                row_svc = "pancard"
            elif idx_ration != -1:
                row_svc = "aayushman"
            elif idx_sid != -1:
                row_svc = "ucaadhar"
            elif idx_srn != -1:
                row_svc = "aadhar_online"

        if name or id_num or raw_mob:
            display_mob, norm_mob = clean_phone(raw_mob)
            is_baki = 1 if any(w in remark.lower() for w in ["baki", "not reciv", "not resiv", "no reciv", "payment baki", "name baki"]) else 0
            records.append({
                "file_id": file_id,
                "service_type": row_svc,
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

    if records:
        sheet_recs_svcs = [r["service_type"] for r in records if r.get("service_type") and r["service_type"] != "general"]
        if sheet_recs_svcs:
            service_type = max(set(sheet_recs_svcs), key=sheet_recs_svcs.count)

    return records, service_type, headers


def parse_service_excel_or_csv(file_path: str, file_id: int, forced_service: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses any office spreadsheet (Excel or CSV), reading ALL sheets if multiple exist.
    """
    ext = os.path.splitext(file_path)[1].lower()
    sheets_dict = {}

    if ext in [".xlsx", ".xlsm"]:
        sheets_dict = pd.read_excel(file_path, sheet_name=None, engine="openpyxl", header=None, dtype=str)
    elif ext == ".xls":
        sheets_dict = pd.read_excel(file_path, sheet_name=None, engine="xlrd", header=None, dtype=str)
    elif ext == ".csv":
        parsed_rows = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip()]
                parsed_rows = list(csv.reader(lines))
        except Exception:
            pass
        if not parsed_rows:
            try:
                with open(file_path, "r", encoding="latin1", errors="ignore") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    parsed_rows = list(csv.reader(lines))
            except Exception:
                pass
        if parsed_rows:
            max_cols = max(len(r) for r in parsed_rows)
            padded = [r + [""] * (max_cols - len(r)) for r in parsed_rows]
            df = pd.DataFrame(padded)
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
    elif all_records:
        all_rec_svcs = [r["service_type"] for r in all_records if r.get("service_type") and r["service_type"] != "general"]
        if all_rec_svcs:
            overall_service = max(set(all_rec_svcs), key=all_rec_svcs.count)
        elif detected_services:
            overall_service = max(set(detected_services), key=detected_services.count)
        else:
            overall_service = "general"
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


def format_date_dd_mm_yyyy(val: Any) -> str:
    if pd.isna(val) or val is None or not str(val).strip():
        return ""
    s = str(val).strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(3)):02d}-{int(m.group(2)):02d}-{m.group(1)}"
    m2 = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m2:
        return f"{int(m2.group(1)):02d}-{int(m2.group(2)):02d}-{m2.group(3)}"
    return s


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
        dt_disp = format_date_dd_mm_yyyy(r.get("record_date", ""))
        if service_type == "ucaadhar":
            row_data = [
                idx, dt_disp, r.get("id_number", ""), r.get("name", ""),
                r.get("status", ""), r.get("total_amt", 0.0), r.get("fee_amt", 0.0),
                r.get("mobile", ""), r.get("remark", "")
            ]
        elif service_type == "aadhar_online":
            row_data = [
                idx, dt_disp, r.get("name", ""), r.get("id_number", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        elif service_type == "pancard":
            row_data = [
                idx, dt_disp, r.get("name", ""), r.get("pan_type", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        elif service_type == "aayushman":
            row_data = [
                idx, dt_disp, r.get("id_number", ""), r.get("name", ""),
                r.get("mobile", ""), r.get("status", ""), r.get("remark", "")
            ]
        else:
            row_data = [
                idx, r.get("service_type", "").upper(), dt_disp, r.get("name", ""),
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
