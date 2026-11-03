import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Styles
HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Navy Blue
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
DATA_FONT = Font(name="Calibri", size=10)
NOTE_FONT = Font(name="Calibri", size=9, italic=True, color="64748B")

THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1")
)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

SERVICES_CONFIG = {
    "ucaadhar": {
        "title": "UC_AADHAR",
        "filename": "Template_1_UC_Aadhaar.xlsx",
        "description": "UC Aadhaar Daily Entry Template",
        "headers": ["SR NO", "DATE", "SID NUMBER", "NAME", "MOBILE NUMBER", "STATUS", "TOTAL AMT", "FEE AMT", "REMARK"],
        "sample_rows": [
            [1, "30-10-2026", "S14292100800020261030113824", "RAMESHBHAI PATEL", "9825012345", "Completed", 50, 50, "PHOTO UPDATE"],
            [2, "30-10-2026", "S14292100800020261030120145", "ANITABEN DAVE", "9898023456", "InProcess", 50, 50, "HOF MANDATE"],
            [3, "30-10-2026", "S14292100800020261030141520", "MEHULKUMAR SHAH", "9712334567", "Completed", 100, 50, "MOBILE LINK"]
        ],
        "alignments": [ALIGN_CENTER, ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_CENTER, ALIGN_CENTER, ALIGN_RIGHT, ALIGN_RIGHT, ALIGN_LEFT]
    },
    "aadhar_online": {
        "title": "AADHAR_ONLINE",
        "filename": "Template_2_Aadhaar_Online.xlsx",
        "description": "Aadhaar Online (SRN) Daily Entry Template",
        "headers": ["SR NO", "DATE", "NAME", "SRN NUMBER", "MOBILE NUMBER", "STATUS", "REMARK"],
        "sample_rows": [
            [1, "30-10-2026", "SURESHBHAI CHAUHAN", "S1311143561680", "9712345678", "Completed", "ADDRESS UPDATE"],
            [2, "30-10-2026", "BHAVIKABEN JOSHI", "S1311143561792", "9824056789", "InProcess", "DOC VERIFY"],
            [3, "30-10-2026", "PRAKASHBHAI PARMAR", "S1311143561814", "9913067890", "Completed", "MOBILE UPDATE"]
        ],
        "alignments": [ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_CENTER, ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT]
    },
    "pancard": {
        "title": "PAN_CARD",
        "filename": "Template_3_PAN_Card.xlsx",
        "description": "PAN Card (New / Change) Daily Entry Template",
        "headers": ["SR NO", "DATE", "NAME", "PAN CHANGE/NEW", "MOBILE NUMBER", "STATUS", "REMARK"],
        "sample_rows": [
            [1, "30-10-2026", "KHUSHI RADADIYA", "PAN NEW", "9313417241", "Completed", "CSC"],
            [2, "30-10-2026", "JIGNESH JAGDISH CHAUHAN", "PAN CHANGE", "9712389176", "Completed", ""],
            [3, "30-10-2026", "DAVERA PAYAL", "PAN CHANGE", "9510818024", "Completed", "ADHAR MISMATCH"]
        ],
        "alignments": [ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_CENTER, ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT]
    },
    "aayushman": {
        "title": "AAYUSHMAN_CARD",
        "filename": "Template_4_Ayushman_Card.xlsx",
        "description": "Ayushman / Ration Card Daily Entry Template",
        "headers": ["SR NO", "DATE", "RATION / AYUSHMAN NUMBER", "NAME", "MOBILE NUMBER", "STATUS", "REMARK"],
        "sample_rows": [
            [1, "30-10-2026", "PAJYXBXFU100234", "DINESHBHAI SOLANKI", "9898123456", "Completed", "PMJAY CARD"],
            [2, "30-10-2026", "PAJYXBXFU100582", "GEETABEN PATEL", "9727034567", "Completed", "NEW ENTRY"],
            [3, "30-10-2026", "PAJYXBXFU100914", "RAHULBHAI VAGHELA", "9426045678", "InProcess", "PENDING OTP"]
        ],
        "alignments": [ALIGN_CENTER, ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT, ALIGN_CENTER, ALIGN_CENTER, ALIGN_LEFT]
    }
}


def style_sheet(ws, title, headers, sample_rows, alignments):
    ws.title = title
    ws.row_dimensions[1].height = 28

    # Write headers
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = THIN_BORDER

    # Write sample rows
    for row_idx, row_data in enumerate(sample_rows, start=2):
        ws.row_dimensions[row_idx].height = 22
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = DATA_FONT
            cell.alignment = alignments[col_idx - 1] if col_idx - 1 < len(alignments) else ALIGN_LEFT
            cell.border = THIN_BORDER

    # Auto-adjust column widths
    for col_idx, header in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = max(
            len(str(header)),
            max([len(str(r[col_idx - 1])) for r in sample_rows] + [10])
        )
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


def create_templates():
    # 1. Create individual service template workbooks
    for svc_key, cfg in SERVICES_CONFIG.items():
        wb = openpyxl.Workbook()
        ws = wb.active
        style_sheet(ws, cfg["title"], cfg["headers"], cfg["sample_rows"], cfg["alignments"])
        file_path = os.path.join(TEMPLATE_DIR, cfg["filename"])
        wb.save(file_path)
        print(f"Created template: {file_path}")

    # 2. Create Master All-In-One Workbook with 4 separate sheets
    master_wb = openpyxl.Workbook()
    # remove default sheet
    default_sheet = master_wb.active

    for idx, (svc_key, cfg) in enumerate(SERVICES_CONFIG.items()):
        ws = master_wb.create_sheet(title=cfg["title"])
        style_sheet(ws, cfg["title"], cfg["headers"], cfg["sample_rows"], cfg["alignments"])

    master_wb.remove(default_sheet)
    master_path = os.path.join(TEMPLATE_DIR, "Khodal_Office_Master_Template.xlsx")
    master_wb.save(master_path)
    print(f"Created Master template: {master_path}")


if __name__ == "__main__":
    create_templates()
