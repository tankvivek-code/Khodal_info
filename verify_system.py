"""
Comprehensive System Verification Test Suite for Khodal Office Hub
Verifies Clean Slate, All 4 Service Workflows, Multi-Sheet Excel Handling,
Edge Cases, and Cleans up After Testing.
"""

import os
import shutil
from datetime import datetime
from database import (
    init_db,
    add_uploaded_file,
    get_all_files,
    get_file_by_id,
    delete_uploaded_file,
    clear_all_database_records,
    insert_bulk_records,
    insert_single_record,
    update_single_record,
    delete_single_record,
    update_record_status,
    search_records,
    get_daily_progress_stats,
    get_all_records_for_export,
    get_db_connection
)
from excel_service import (
    parse_service_excel_or_csv,
    export_records_to_excel,
    clean_phone,
    normalize_date_str
)
import openpyxl

def run_all_tests():
    print("=====================================================================")
    print("🚀 RUNNING KHODAL OFFICE VERIFICATION SUITE (CLEAN SLATE & WORKFLOWS)")
    print("=====================================================================\n")

    init_db()
    clear_all_database_records()
    passed = 0
    total = 0

    def test(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ PASS: {name}")
        else:
            print(f"  ❌ FAIL: {name} - {details}")
            raise AssertionError(f"Test failed: {name} - {details}")

    # -------------------------------------------------------------------------
    # SUITE 1: CLEAN SLATE VERIFICATION
    # -------------------------------------------------------------------------
    print("--- [1/6] Verifying Clean Slate (0 Default/Dummy Records) ---")
    initial_stats = get_daily_progress_stats()
    test("Initial total records is 0", initial_stats["total_applications"] == 0, f"got {initial_stats['total_applications']}")
    test("Initial completed count is 0", initial_stats["completed"] == 0)
    test("Initial in-process count is 0", initial_stats["in_process"] == 0)
    test("Initial baki count is 0", initial_stats["baki_pending"] == 0)
    test("Initial total fees is 0.0", initial_stats["total_fee"] == 0.0)
    test("Initial files list is empty", len(get_all_files()) == 0)

    # -------------------------------------------------------------------------
    # SUITE 2: INSERT & VERIFY 4 SERVICE WORKFLOWS
    # -------------------------------------------------------------------------
    print("\n--- [2/6] Populating Sample Records Across All 4 Services ---")
    
    file_id = add_uploaded_file(
        filename="office_batch_1.xlsx",
        service_type="general",
        file_date="2026-10-01",
        stored_path="uploads/office_batch_1.xlsx",
        file_size=15420,
        row_count=0
    )
    test("Uploaded file tracking entry created", file_id > 0)

    sample_records = [
        # UC Aadhaar
        {
            "file_id": file_id,
            "service_type": "ucaadhar",
            "record_date": "2026-10-01",
            "name": "Brajesh Girish Tiwari",
            "mobile": "8128382517",
            "id_number": "S148796318971020261001104627",
            "pan_type": "",
            "status": "Completed",
            "total_amt": 125.0,
            "fee_amt": 200.0,
            "remark": "SPEED",
            "is_baki": 0
        },
        {
            "file_id": file_id,
            "service_type": "ucaadhar",
            "record_date": "2026-10-01",
            "name": "Shiju Philip Khunt",
            "mobile": "9904353878",
            "id_number": "S14879000000000000000000000",
            "pan_type": "",
            "status": "InProcess",
            "total_amt": 75.0,
            "fee_amt": 100.0,
            "remark": "200 BAKI",
            "is_baki": 1
        },
        # Aadhaar Online
        {
            "file_id": file_id,
            "service_type": "aadhar_online",
            "record_date": "2026-10-01",
            "name": "Suresh Patel",
            "mobile": "9825012345",
            "id_number": "S1311143561680",
            "pan_type": "",
            "status": "Completed",
            "total_amt": 0.0,
            "fee_amt": 0.0,
            "remark": "HOF",
            "is_baki": 0
        },
        # PAN Card
        {
            "file_id": file_id,
            "service_type": "pancard",
            "record_date": "2026-10-02",
            "name": "Mahesh Shah",
            "mobile": "9725098765",
            "id_number": "",
            "pan_type": "PAN NEW",
            "status": "Completed",
            "total_amt": 0.0,
            "fee_amt": 150.0,
            "remark": "",
            "is_baki": 0
        },
        # Ayushman Card
        {
            "file_id": file_id,
            "service_type": "aayushman",
            "record_date": "2026-10-02",
            "name": "Dinesh Joshi",
            "mobile": "9625011223",
            "id_number": "PAJYXBXFU109904",
            "pan_type": "",
            "status": "Completed",
            "total_amt": 0.0,
            "fee_amt": 50.0,
            "remark": "OK",
            "is_baki": 0
        }
    ]

    inserted_count = insert_bulk_records(sample_records)
    test("Bulk inserted 5 test records", inserted_count == 5)

    stats = get_daily_progress_stats()
    test("Total records is now 5", stats["total_applications"] == 5)
    test("Completed is 4", stats["completed"] == 4)
    test("InProcess is 1", stats["in_process"] == 1)
    test("Baki pending count is 1", stats["baki_pending"] == 1)
    test("Total fees is 500.0", stats["total_fee"] == 500.0)

    # -------------------------------------------------------------------------
    # SUITE 3: SEARCH POSSIBILITIES & EDGE CASES
    # -------------------------------------------------------------------------
    print("\n--- [3/6] Testing Search Queries & Edge Cases ---")
    
    # Name searches
    r, c = search_records(name="tiwari")
    test("Search lowercase 'tiwari' finds record", c == 1 and r[0]["name"] == "Brajesh Girish Tiwari")

    r, c = search_records(name="TIWARI")
    test("Search uppercase 'TIWARI' finds record", c == 1)

    r, c = search_records(name="Shiju Philip")
    test("Search full name 'Shiju Philip'", c == 1)

    # Mobile searches
    r, c = search_records(mobile="8128382517")
    test("Search 10-digit mobile '8128382517'", c == 1)

    r, c = search_records(mobile="81283")
    test("Search prefix 5-digit mobile '81283'", c == 1)

    r, c = search_records(mobile="82517")
    test("Search suffix 5-digit mobile '82517'", c == 1)

    r, c = search_records(mobile="+91 81283 82517")
    test("Search formatted mobile '+91 81283 82517'", c == 1)

    # ID searches
    r, c = search_records(id_number="S1311143561680")
    test("Search exact SRN 'S1311143561680'", c == 1)

    r, c = search_records(id_number="S131114")
    test("Search partial SRN 'S131114'", c == 1)

    r, c = search_records(id_number="S148796318971020261001104627")
    test("Search exact SID", c == 1)

    r, c = search_records(id_number="PAJYXBXFU")
    test("Search Ration card prefix 'PAJYXBXFU'", c == 1)

    # Service & status filtering
    r, c = search_records(service_type="ucaadhar")
    test("Filter tab 'ucaadhar' returns 2", c == 2)

    r, c = search_records(service_type="aadhar_online")
    test("Filter tab 'aadhar_online' returns 1", c == 1)

    r, c = search_records(service_type="pancard")
    test("Filter tab 'pancard' returns 1", c == 1)

    r, c = search_records(service_type="aayushman")
    test("Filter tab 'aayushman' returns 1", c == 1)

    r, c = search_records(baki_only=True)
    test("Filter 'baki_only' returns 1", c == 1 and r[0]["is_baki"] == 1)

    # -------------------------------------------------------------------------
    # SUITE 4: DATA MUTATION & STATUS TOGGLING
    # -------------------------------------------------------------------------
    print("\n--- [4/6] Testing Mutation, Toggling & Record Deletion ---")
    
    new_id = insert_single_record({
        "service_type": "pancard",
        "record_date": "2026-10-03",
        "name": "Ketan Vaghasiya",
        "mobile": "9898000000",
        "pan_type": "PAN NEW",
        "status": "InProcess",
        "fee_amt": 100.0,
        "remark": ""
    })
    test("Create single record returns valid ID", new_id > 0)

    # Status toggle
    update_record_status(new_id, "Completed")
    r, _ = search_records(mobile="9898000000")
    test("Toggled status to Completed", len(r) == 1 and r[0]["status"] == "Completed")

    # Update record
    update_single_record(new_id, {
        "service_type": "pancard",
        "record_date": "2026-10-03",
        "name": "Ketan Vaghasiya Updated",
        "mobile": "9898000000",
        "fee_amt": 120.0
    })
    r, _ = search_records(mobile="9898000000")
    test("Updated single record details", r[0]["name"] == "Ketan Vaghasiya Updated" and r[0]["fee_amt"] == 120.0)

    # Delete record
    delete_single_record(new_id)
    r, c = search_records(mobile="9898000000")
    test("Deleted single record", c == 0)

    # -------------------------------------------------------------------------
    # SUITE 5: MULTI-SHEET EXCEL PARSING & EXPORTING
    # -------------------------------------------------------------------------
    print("\n--- [5/6] Testing Multi-Sheet Excel Files & Exporter ---")
    
    export_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(export_dir, exist_ok=True)

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "UC_Aadhaar"
    ws1.append(["Date", "Name", "SID Number", "Mobile", "Fee", "Remark"])
    ws1.append(["2026-10-01", "Sheet1 Client", "SID999", "9111111111", 100, "Ok"])

    ws2 = wb.create_sheet("PAN_Card")
    ws2.append(["Date", "Party Name", "PAN TYPE", "Mobile No", "Remark"])
    ws2.append(["2026-10-02", "Sheet2 Client", "PAN NEW", "9222222222", "Done"])

    ws3 = wb.create_sheet("2026-10-03")
    ws3.append(["Name", "SRN Number", "Mobile", "Remarks"])
    ws3.append(["Sheet3 Client", "SRN888", "9333333333", "In Process"])

    multi_path = os.path.join(export_dir, "test_multi_sheet.xlsx")
    wb.save(multi_path)

    parsed_multi, summary = parse_service_excel_or_csv(multi_path, 100)
    test("Multi-sheet Excel parsed across 3 sheets", summary["sheets_count"] == 3)
    test("Parsed 3 records across 3 sheets", len(parsed_multi) == 3)
    test("Sheet 1 detected as ucaadhar", parsed_multi[0]["service_type"] == "ucaadhar")
    test("Sheet 2 detected as pancard", parsed_multi[1]["service_type"] == "pancard")
    test("Sheet 3 inherited date from sheet title", parsed_multi[2]["record_date"] == "2026-10-03")

    if os.path.exists(multi_path):
        os.remove(multi_path)

    # Exporter test
    p_all = export_records_to_excel(sample_records, export_dir, service_type="all")
    test("Exported records to Excel file", os.path.exists(p_all) and os.path.getsize(p_all) > 1000)
    if os.path.exists(p_all):
        os.remove(p_all)

    # -------------------------------------------------------------------------
    # SUITE 6: CLEANUP & LEAVING 0 DUMMY RECORDS
    # -------------------------------------------------------------------------
    print("\n--- [6/6] Verifying Full Cleanup (0 Dummy Records Remaining) ---")
    
    clear_all_database_records()
    final_stats = get_daily_progress_stats()
    test("Database cleared to 0 records", final_stats["total_applications"] == 0)
    test("Database cleared to 0 files", len(get_all_files()) == 0)

    # Clean temporary files in exports
    for f in os.listdir(export_dir):
        if f.endswith(".xlsx") or f.endswith(".csv"):
            try:
                os.remove(os.path.join(export_dir, f))
            except OSError:
                pass

    print("\n=====================================================================")
    print(f"🎉 TEST RESULTS: {passed}/{total} TESTS PASSED (100% SUCCESS)")
    print("=====================================================================")

if __name__ == "__main__":
    run_all_tests()
