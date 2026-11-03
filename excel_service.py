import os
import re
import csv
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

DATE_REGEX = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")
PHONE_REGEX = re.compile(r"\b([6-9]\d{9})\b")
SID_REGEX = re.compile(r"\b(S\d{15,30})\b", re.I)
SID_DATE_REGEX = re.compile(r"S\d{10,14}(202[0-9])(0[1-9]|1[0-2])([0-3][0-9])")

STATUS_MAP = {
    "COMPLETED": "Completed",
    "COMPLETE": "Completed",
    "INPROCESS": "InProcess",
    "IN PROCESS": "InProcess",
    "PROCESS": "InProcess",
    "REJECT": "Reject",
    "REJECTED": "Reject",
    "PENDING": "Pending",
}

NON_NAME_WORDS = {
    "NAME", "ADDRESS", "MOBILE", "MO", "MOB", "PHONE", "SPEED", "NEW", "RIPIT", "REPEAT",
    "OK", "NOT RECIV", "NOT RICIV", "NO RECIV", "CALL NOT PICKUP", "CALL NOT RECEIVRD",
    "MANISH ID", "BRIJAL ID", "TOTAL", "STATUS", "SLNO", "ENROLMENT_NO_DATE", "SID NUMBER",
    "OTHERS", "REMARK", "FEE", "ADD CHANGE THAY GAYU CHHE", "NAME CHANGE", "NAME CHANJ",
    "CHIRAG JARIYA", "DHARMESH JARIYA", "DHARSH JARIYA", "MO NO BAKI", "PAYMENT BAKI"
}


def clean_header_name(header: Any) -> str:
    s = str(header).lower().strip()
    s = re.sub(r"[_\-\.\(\)\[\]\/\\:]+", " ", s)
    return " ".join(s.split())


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
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    m = PHONE_REGEX.search(digits)
    norm = m.group(1) if m else (digits if len(digits) == 10 else "")
    return s, norm


from datetime import datetime, timedelta

def normalize_date_str(val: Any) -> str:
    if pd.isna(val) or val is None:
        return ""
    if isinstance(val, (int, float)):
        try:
            if 30000 <= val <= 65000:
                base = datetime(1899, 12, 30)
                dt = base + timedelta(days=float(val))
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")

    s = str(val).strip()
    try:
        fval = float(s)
        if 30000 <= fval <= 65000:
            base = datetime(1899, 12, 30)
            dt = base + timedelta(days=fval)
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    m = DATE_REGEX.search(s)
    if not m:
        return ""
    raw = m.group(1).replace("/", "-")
    parts = raw.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:
            # YYYY-MM-DD or YYYY-DD-MM (Excel US-locale export flip)
            y = parts[0]
            p1 = int(parts[1])
            p2 = int(parts[2])
            # If p2 == 10 and p1 <= 31 (like in Gujarat office PAN registers), it's Oct DD
            if 1 <= p1 <= 31 and p2 == 10:
                return f"{y}-10-{p1:02d}"
            return f"{y}-{p1:02d}-{p2:02d}"
        else:
            # DD-MM-YYYY or DD-MM-YY
            year = parts[2]
            if len(year) == 2:
                year = f"20{year}"
            elif len(year) == 3:
                year = "2026"
            return f"{year}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    return s


def extract_date_from_sid(sid: str) -> str:
    """
    Aadhaar SID enrolment numbers contain the exact timestamp:
    S<operator_id><YYYYMMDDHHMMSS>.
    Extract YYYY-MM-DD directly from the SID timestamp.
    """
    if not sid:
        return ""
    m = SID_DATE_REGEX.search(sid)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def detect_service_type_from_content(headers: List[str], file_path: str) -> str:
    cleaned = [clean_header_name(h) for h in headers]
    if any("sid" in h or "enrolment" in h or "enrollment" in h for h in cleaned):
        return "ucaadhar"
    if any("srn" in h for h in cleaned):
        return "aadhar_online"
    if any("pan change" in h or "pan new" in h or "pancard" in h for h in cleaned):
        return "pancard"
    if any("ration" in h or "aayushman" in h or "ayushman" in h for h in cleaned):
        return "aayushman"

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


def parse_single_sheet_df(
    df: pd.DataFrame,
    file_path: str,
    file_id: int,
    sheet_name: str = "",
    forced_service: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str, List[str]]:
    raw_rows = []
    cols_as_str = [str(c).strip() for c in df.columns]
    if any(not c.isdigit() and str(c).lower() != "nan" and not c.startswith("Unnamed:") for c in cols_as_str):
        raw_rows.append(cols_as_str)
    for _, r in df.iterrows():
        raw_rows.append([str(val).strip() if pd.notna(val) and val is not None and str(val).lower() != "nan" else "" for val in r.values])

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
    current_date = sheet_date if sheet_date else ""
    if not current_date:
        for r_vals in raw_rows[:60]:
            for c in r_vals:
                if not c:
                    continue
                sid_d = extract_date_from_sid(c)
                if sid_d:
                    current_date = sid_d
                    break
                nd = normalize_date_str(c)
                if nd and len(c) <= 15:
                    current_date = nd
                    break
            if current_date:
                break
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

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
        idx_pan = find_c("pan change", "pan new", "pan type", "pan")
        idx_ration = find_c("ration", "ayushman", "aayushman")
        idx_mobile = find_c("mobile", "mo", "contact", "phone")
        idx_status = find_c("status")
        idx_total = find_c("total", "amount", "amt")
        idx_fee = find_c("fee")
        idx_remark = find_c("remark", "others", "note")

    for row_vals in raw_rows:
        cells = [str(c).strip() if c is not None and str(c).strip() and str(c).lower() != "nan" else "" for c in row_vals]
        if not any(cells):
            continue

        joined = " ".join(cells).upper()

        # Determine if row has data markers (SID, phone number, or integer index)
        first_cell = cells[0].replace(".0", "").strip() if cells else ""
        has_int_index = first_cell.isdigit() and len(first_cell) <= 6
        has_phone = any(PHONE_REGEX.search(c.replace(".0", "")) for c in cells)
        has_sid = any(re.search(r"\bS\d{15,}", c, re.I) for c in cells)

        # Check if table header row (only if not an actual data row with index/phone/SID)
        if not has_sid and not has_phone and not has_int_index:
            header_keywords = [
                r"\bNAME\b", r"\bPARTY\b", r"\bDATE\b", r"\bMOBILE\b", r"\bMO\b", r"\bPHONE\b",
                r"\bSRN\b", r"\bSID\b", r"\bPAN\b", r"\bSTATUS\b", r"\bREMARK\b", r"\bTOTAL\b",
                r"\bFEE\b", r"\bRATION\b", r"\bAYUSHMAN\b", r"\bSLNO\b", r"\bSR NO\b", r"\bENROLMENT\b"
            ]
            kw_matches = sum(1 for kw in header_keywords if re.search(kw, joined))
            if kw_matches >= 2 and any(re.search(kw, joined) for kw in [r"\bNAME\b", r"\bPARTY\b", r"\bSRN\b", r"\bSID\b", r"\bPAN\b", r"\bRATION\b", r"\bENROLMENT\b", r"\bSLNO\b", r"\bSTATUS\b"]):
                update_columns(cells)
                continue

        # Check pure date divider row
        non_empty = [c for c in cells if c]
        if len(non_empty) <= 2:
            d_cand = [normalize_date_str(c) for c in non_empty if normalize_date_str(c) and len(c) <= 15]
            if d_cand:
                current_date = d_cand[0]
                continue

        # Check pure subtotal / divider row (e.g. 1350.0, 1400.0, brijal id, MANISH ID, 4300, 65670)
        has_sid = any(re.search(r"\bS\d{15,}", c) for c in non_empty)
        if not has_sid:
            if all(c.replace(".", "", 1).isdigit() for c in non_empty):
                continue
            if any(kw in joined for kw in ["BRIJAL ID", "MANISH ID", "TOTAL", "DIVIDER"]):
                continue

        # 1. Extract Date
        rec_date = current_date
        if idx_date != -1 and idx_date < len(cells) and cells[idx_date]:
            d = normalize_date_str(cells[idx_date])
            if d:
                rec_date = d
                current_date = d

        # 2. Extract SID / SRN / ID Number & Name
        name = ""
        id_num = ""
        sid = ""
        srn = ""
        ration_no = ""
        pan_type = ""

        # Check for Aadhaar SID
        for c in cells:
            m_s = re.search(r"\b(S\d{20,30})", c, re.I)
            if m_s:
                sid = m_s.group(1).upper()
                break

        if sid:
            id_num = sid
            # Aadhaar SID timestamp is always 100% authoritative for date
            sid_d = extract_date_from_sid(sid)
            if sid_d:
                rec_date = sid_d
        elif idx_sid != -1 and idx_sid < len(cells) and cells[idx_sid]:
            val = cells[idx_sid]
            # SID / SRN must contain digits (e.g. S13..., SID999)
            if any(ch.isdigit() for ch in val):
                id_num = val
                if id_num.upper().startswith("S") and len(id_num) >= 18:
                    sid = id_num
                else:
                    srn = id_num
            elif not name and not val.upper().startswith("COMPLET") and not val.upper().startswith("INPROCESS") and not val.upper().startswith("REJECT"):
                if val.upper() not in NON_NAME_WORDS:
                    name = val
        elif idx_srn != -1 and idx_srn < len(cells) and cells[idx_srn]:
            id_num = cells[idx_srn]
            srn = id_num
        elif idx_ration != -1 and idx_ration < len(cells) and cells[idx_ration]:
            id_num = cells[idx_ration]
            ration_no = id_num

        if idx_pan != -1 and idx_pan < len(cells):
            pan_type = cells[idx_pan]

        # 3. Status
        status = "Completed"
        if "REJECT" in joined:
            status = "Reject"
        elif "INPROCESS" in joined or "IN PROCESS" in joined:
            status = "InProcess"
        elif "PENDING" in joined:
            status = "Pending"
        elif idx_status != -1 and idx_status < len(cells) and cells[idx_status]:
            raw_st = cells[idx_status].lower()
            if "process" in raw_st:
                status = "InProcess"
            elif "reject" in raw_st:
                status = "Reject"
            elif "pending" in raw_st:
                status = "Pending"
            elif "complete" in raw_st:
                status = "Completed"

        # 4. Total and Fee
        total_amt = 0.0
        fee_amt = 0.0

        if idx_total != -1 and idx_total < len(cells) and cells[idx_total]:
            try:
                total_amt = float(cells[idx_total])
            except Exception:
                pass
            if idx_fee != -1 and idx_fee < len(cells) and cells[idx_fee]:
                try:
                    fee_amt = float(cells[idx_fee])
                except Exception:
                    pass
            elif idx_total + 1 < len(cells) and cells[idx_total + 1]:
                try:
                    fee_amt = float(cells[idx_total + 1])
                except Exception:
                    pass
        else:
            nums = []
            for i, c in enumerate(cells):
                if i == 0 and c.replace(".0", "").isdigit() and float(c) < 1000:
                    continue
                if re.match(r"^\d+(\.\d+)?$", c) and not PHONE_REGEX.match(c):
                    val = float(c)
                    if val <= 1000:
                        nums.append((i, val))
            if len(nums) >= 2:
                total_amt = nums[0][1]
                fee_amt = nums[1][1]
            elif len(nums) == 1:
                total_amt = nums[0][1]

        # 5. Mobile
        raw_mob = ""
        if idx_mobile != -1 and idx_mobile < len(cells) and cells[idx_mobile]:
            raw_mob = cells[idx_mobile]
        if not raw_mob:
            m_ph = PHONE_REGEX.search(joined.replace(".0", ""))
            if m_ph:
                raw_mob = m_ph.group(1)
            for i, c in enumerate(cells):
                if c.upper() in ["MOBILE", "MO", "MOB"] and i + 1 < len(cells):
                    m_next = PHONE_REGEX.search(cells[i+1].replace(".0", ""))
                    if m_next:
                        raw_mob = m_next.group(1)

        disp_mob, norm_mob = clean_phone(raw_mob)

        # 6. Name
        if not name and idx_name != -1 and idx_name < len(cells) and cells[idx_name]:
            c_name = cells[idx_name]
            if not c_name.startswith("S1") and not re.search(r"\bS\d{15,}", c_name) and not c_name.replace(".", "").isdigit() and not normalize_date_str(c_name):
                name = c_name

        # Case A: Format 1 (Col 1 is SID, Col 2 is Name)
        if not name and len(cells) > 2 and sid and (cells[1].upper().startswith("S1") or cells[0].upper().startswith("S1")):
            sid_col = 1 if cells[1].upper().startswith("S1") else 0
            cand_col = sid_col + 1
            if cand_col < len(cells):
                cand = cells[cand_col]
                cand_u = cand.upper()
                if cand and not cand_u.startswith("COMPLET") and not cand_u.startswith("INPROCESS") and not cand_u.startswith("REJECT") and not cand.replace(".", "").isdigit() and not normalize_date_str(cand):
                    name = cand

        # Case B: Col 1 is Customer Name directly (must NOT be a date!)
        if not name and len(cells) > 1:
            cand = cells[1]
            cand_u = cand.upper()
            if cand and not cand.startswith("S1") and not cand_u.startswith("COMPLET") and not cand_u.startswith("INPROCESS") and not cand_u.startswith("REJECT") and not cand.replace(".", "").isdigit() and not normalize_date_str(cand):
                if cand_u not in NON_NAME_WORDS and not any(kw in cand_u for kw in ["ID", "TOTAL"]):
                    name = cand

        # Case C: Name labeled in later columns (e.g. col 5: 'NAME', col 6: 'MADHVI DHOKIYA')
        if not name:
            for i, c in enumerate(cells):
                if c.upper() in ["NAME", "NAME:"] and i + 1 < len(cells):
                    next_c = cells[i + 1]
                    if next_c and next_c.upper() not in NON_NAME_WORDS and not next_c.replace(".", "").isdigit() and not normalize_date_str(next_c):
                        name = next_c
                        break

        # Case D: Name in remarks column or update column
        if not name:
            for i in range(3, len(cells)):
                c = cells[i]
                c_u = c.upper()
                if not c or c.replace(".", "").isdigit() or PHONE_REGEX.search(c) or normalize_date_str(c):
                    continue
                if "/" in c:
                    part0 = c.split("/")[0].strip()
                    if len(part0.split()) >= 2 and part0.upper() not in NON_NAME_WORDS and not normalize_date_str(part0):
                        name = part0
                        break
                elif "-" in c and "NAME" in c_u:
                    clean_nm = re.sub(r"\bNAME\b", "", c, flags=re.I).replace("-", "").strip()
                    if clean_nm and not normalize_date_str(clean_nm):
                        name = clean_nm
                        break
                elif len(c.split()) >= 2 and c_u not in NON_NAME_WORDS and not normalize_date_str(c):
                    name = c
                    break

        # If still no name, but valid SID
        if not name and sid:
            name = "—"

        # 7. Remarks
        remarks_list = []
        if idx_remark != -1 and idx_remark < len(cells) and cells[idx_remark]:
            remarks_list.append(cells[idx_remark])

        for idx_c, c in enumerate(cells):
            if not c:
                continue
            if c == name or c == id_num or c == disp_mob or c.replace(".0", "") == norm_mob:
                continue
            if idx_c == idx_date or normalize_date_str(c):
                continue
            if idx_c == idx_pan or c == pan_type:
                continue
            if c.upper() in ["COMPLETED", "INPROCESS", "IN PROCESS", "REJECT", "REJECTED", "PENDING"]:
                continue
            if c.replace(".", "", 1).isdigit() and float(c) < 1000:
                continue
            if c.upper() in ["NO", "SLNO", "SR NO", "SID NUMBER", "TOTAL", "STATUS", "NAME", "MOBILE"]:
                continue
            if c not in remarks_list:
                remarks_list.append(c)

        final_remark = " | ".join(dict.fromkeys(remarks_list))
        is_baki = 1 if any(w in final_remark.lower() for w in ["baki", "not reciv", "not resiv", "no reciv"]) else 0

        # Determine row-level service type
        row_svc = service_type
        clean_id = (id_num or "").strip().upper()
        if not forced_service or forced_service == "auto":
            if clean_id.startswith("SID") or (clean_id.startswith("S") and len(clean_id) >= 18):
                row_svc = "ucaadhar"
            elif clean_id.startswith("SRN") or (clean_id.startswith("S") and 10 <= len(clean_id) <= 16):
                row_svc = "aadhar_online"
            elif pan_type or idx_pan != -1:
                row_svc = "pancard"
            elif idx_ration != -1:
                row_svc = "aayushman"

        if name or id_num or disp_mob:
            records.append({
                "file_id": file_id,
                "service_type": row_svc,
                "record_date": rec_date,
                "name": name,
                "mobile": disp_mob,
                "normalized_mobile": norm_mob,
                "id_number": id_num,
                "pan_type": pan_type,
                "status": status,
                "total_amt": total_amt,
                "fee_amt": fee_amt,
                "remark": final_remark,
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

    # Determine predominant service type across all extracted records
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

    if service_type == "ucaadhar":
        columns = ["No", "Date", "SID Number", "Customer Name", "Status", "Govt Total (Rs)", "Fee (Rs)", "Mobile Number", "Remarks"]
    elif service_type == "aadhar_online":
        columns = ["No", "Date", "Customer Name", "SRN Number", "Mobile Number", "Status", "Remarks"]
    elif service_type == "pancard":
        columns = ["No", "Date", "Customer Name", "PAN Type", "Mobile Number", "Status", "Remarks"]
    elif service_type == "aayushman":
        columns = ["No", "Date", "Ration / Ayushman No", "Customer Name", "Mobile Number", "Status", "Remarks"]
    else:
        columns = ["No", "Service", "Date", "Customer Name", "ID / SID / SRN / Card No", "Mobile Number", "Status", "Fee (Rs)", "Remarks"]

    ws.append(columns)
    for col_idx in range(1, len(columns) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[1].height = 26

    for idx, r in enumerate(records, start=1):
        formatted_date = format_date_dd_mm_yyyy(r.get("record_date"))
        if service_type == "ucaadhar":
            row_data = [
                idx,
                formatted_date,
                r.get("id_number", ""),
                r.get("name", ""),
                r.get("status", "Completed"),
                r.get("total_amt", 0.0),
                r.get("fee_amt", 0.0),
                r.get("mobile", ""),
                r.get("remark", "")
            ]
        elif service_type == "aadhar_online":
            row_data = [
                idx,
                formatted_date,
                r.get("name", ""),
                r.get("id_number", ""),
                r.get("mobile", ""),
                r.get("status", "Completed"),
                r.get("remark", "")
            ]
        elif service_type == "pancard":
            row_data = [
                idx,
                formatted_date,
                r.get("name", ""),
                r.get("pan_type", ""),
                r.get("mobile", ""),
                r.get("status", "Completed"),
                r.get("remark", "")
            ]
        elif service_type == "aayushman":
            row_data = [
                idx,
                formatted_date,
                r.get("id_number", ""),
                r.get("name", ""),
                r.get("mobile", ""),
                r.get("status", "Completed"),
                r.get("remark", "")
            ]
        else:
            row_data = [
                idx,
                r.get("service_type", "").upper(),
                formatted_date,
                r.get("name", ""),
                r.get("id_number", ""),
                r.get("mobile", ""),
                r.get("status", "Completed"),
                r.get("fee_amt", 0.0),
                r.get("remark", "")
            ]
        ws.append(row_data)
        row_num = ws.max_row
        ws.row_dimensions[row_num].height = 20
        for col_idx in range(1, len(row_data) + 1):
            c = ws.cell(row=row_num, column=col_idx)
            c.font = cell_font
            c.border = thin_border
            if col_idx in [1, 2]:
                c.alignment = center_align
            else:
                c.alignment = left_align

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    wb.save(output_path)
    return output_path
