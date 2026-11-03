import os
import sys
import json
import io
import pandas as pd
import openpyxl

sys.path.insert(0, r"d:\Khodal_info")

from database import (
    init_db,
    search_records,
    get_daily_progress_stats,
    insert_single_record,
    update_single_record,
    delete_single_record,
    update_record_status,
    add_uploaded_file,
    delete_uploaded_file,
    get_all_records_for_export,
    get_db_connection
)
from excel_service import (
    parse_service_excel_or_csv,
    export_records_to_excel,
    clean_phone,
    normalize_date_str
)

def run_all_tests():
    print("=====================================================================")
    print("🚀 RUNNING COMPREHENSIVE PRODUCTION TEST SUITE (ALL POSSIBILITIES)")
    print("=====================================================================\n")

    init_db()
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
    # SUITE 1: VERIFY ALL 4 PRELOADED SERVICES
    # -------------------------------------------------------------------------
    print("--- [1/5] Testing 4 Service Categories & Preloaded Data ---")
    stats = get_daily_progress_stats()
    test("Total records is 617", stats["total_applications"] == 617, f"got {stats['total_applications']}")
    test("Completed count is 513", stats["completed"] == 513, f"got {stats['completed']}")
    test("In-process count is 85", stats["in_process"] == 85, f"got {stats['in_process']}")
    test("Baki pending count is 36", stats["baki_pending"] == 36, f"got {stats['baki_pending']}")
    test("Total fees is 48950.0", stats["total_fee"] == 48950.0, f"got {stats['total_fee']}")
    test("UC Aadhaar count is 380", stats["service_breakdown"]["ucaadhar"]["total"] == 380)
    test("Aadhaar Online count is 147", stats["service_breakdown"]["aadhar_online"]["total"] == 147)
    test("PAN Card count is 41", stats["service_breakdown"]["pancard"]["total"] == 41)
    test("Ayushman Card count is 49", stats["service_breakdown"]["aayushman"]["total"] == 49)

    # -------------------------------------------------------------------------
    # SUITE 2: SEARCH POSSIBILITIES & EDGE CASES
    # -------------------------------------------------------------------------
    print("\n--- [2/5] Testing Search Queries & Real-World Formats ---")
    
    # 2.1 Name searches
    r, c = search_records(name="khunt")
    test("Search lowercase 'khunt' finds records", c >= 12, f"count: {c}")

    r, c = search_records(name="KHUNT")
    test("Search uppercase 'KHUNT' finds records", c >= 12, f"count: {c}")

    r, c = search_records(name="Shiju Philip")
    test("Search full name with space 'Shiju Philip'", c >= 2, f"count: {c}")

    r, c = search_records(name="Brajesh Girish Tiwari")
    test("Search 3-word name 'Brajesh Girish Tiwari'", c >= 1, f"count: {c}")

    # 2.2 Mobile searches (with all variations)
    r, c = search_records(mobile="8128382517")
    test("Search 10-digit mobile '8128382517'", c == 2, f"count: {c}")

    r, c = search_records(mobile="81283")
    test("Search prefix 5-digit mobile '81283'", c >= 2, f"count: {c}")

    r, c = search_records(mobile="82517")
    test("Search suffix 5-digit mobile '82517'", c >= 2, f"count: {c}")

    r, c = search_records(mobile="+91 81283 82517")
    test("Search formatted mobile '+91 81283 82517'", c >= 2, f"count: {c}")

    r, c = search_records(mobile="9904353878")
    test("Search mobile '9904353878' (Chauhan)", c >= 2, f"count: {c}")

    # 2.3 ID Number searches (SID, SRN, Ration Card, etc.)
    r, c = search_records(id_number="S1311143561680")
    test("Search exact SRN 'S1311143561680'", c == 1, f"count: {c}")

    r, c = search_records(id_number="S131114")
    test("Search partial SRN 'S131114'", c >= 1, f"count: {c}")

    r, c = search_records(id_number="S148796318971020261001104627")
    test("Search exact SID 'S148796318971020261001104627'", c == 1, f"count: {c}")

    r, c = search_records(id_number="S14879")
    test("Search partial SID 'S14879'", c >= 1, f"count: {c}")

    r, c = search_records(id_number="PAJYXBXFU")
    test("Search alphanumeric Ration No 'PAJYXBXFU'", c == 1, f"count: {c}")

    r, c = search_records(id_number="109904008663704")
    test("Search 15-digit Ration No '109904008663704'", c == 1, f"count: {c}")

    r, c = search_records(id_number="PUI5RLKFA")
    test("Search compound Ration No segment 'PUI5RLKFA'", c >= 1, f"count: {c}")

    # 2.4 Service-specific tab filter
    r, c = search_records(service_type="ucaadhar")
    test("Filter tab 'ucaadhar' returns 380", c == 380, f"count: {c}")

    r, c = search_records(service_type="aadhar_online")
    test("Filter tab 'aadhar_online' returns 147", c == 147, f"count: {c}")

    r, c = search_records(service_type="pancard")
    test("Filter tab 'pancard' returns 41", c == 41, f"count: {c}")

    r, c = search_records(service_type="aayushman")
    test("Filter tab 'aayushman' returns 49", c == 49, f"count: {c}")

    # 2.5 Baki filter & status filter
    r, c = search_records(baki_only=True)
    test("Filter 'baki_only' returns 36 dues cases", c == 36, f"count: {c}")
    test("Baki case contains dues in remark", "baki" in r[0]["remark"].lower() or "reciv" in r[0]["remark"].lower() or "resiv" in r[0]["remark"].lower())

    r, c = search_records(status="Completed")
    test("Filter status 'Completed' returns 513", c == 513, f"count: {c}")

    r, c = search_records(status="InProcess")
    test("Filter status 'InProcess' returns 85", c == 85, f"count: {c}")

    # 2.6 Date filters
    r, c = search_records(date_filter="2026-10-01")
    test("Filter date '2026-10-01' finds records across services", c >= 20, f"count: {c}")

    r, c = search_records(date_filter="1999-01-01")
    test("Filter non-existent date returns 0 safely without error", c == 0)

    # 2.7 Global search across all fields
    r, c = search_records(query="SPEED")
    test("Global query 'SPEED' finds records with SPEED remark", c >= 5, f"count: {c}")

    r, c = search_records(query="RIPIT")
    test("Global query 'RIPIT' finds repeat applications", c >= 10, f"count: {c}")

    # 2.8 Out of bounds pagination
    r, c = search_records(page=999, page_size=25)
    test("Out-of-bounds pagination returns empty list without error", len(r) == 0 and c == 617)

    # -------------------------------------------------------------------------
    # SUITE 3: CRUD & STATUS TOGGLING
    # -------------------------------------------------------------------------
    print("\n--- [3/5] Testing Data Mutation, Status Toggling & Cleanup ---")
    
    # 3.1 Create new record
    new_id = insert_single_record({
        "service_type": "ucaadhar",
        "record_date": "2026-11-03",
        "name": "Live Office Tester",
        "mobile": "9898099887",
        "id_number": "S1999999999999",
        "status": "InProcess",
        "fee_amt": 150.0,
        "remark": "Test Entry"
    })
    test("Create record returns valid ID", new_id > 0)

    # Verify newly created record appears in search
    r, c = search_records(mobile="9898099887")
    test("Newly created record found by mobile", c == 1 and r[0]["name"] == "Live Office Tester")
    test("Status is InProcess", r[0]["status"] == "InProcess")

    # 3.2 Toggle status
    ok = update_record_status(new_id, "Completed")
    test("Update record status to Completed", ok is True)
    r, _ = search_records(mobile="9898099887")
    test("Record status is now Completed", r[0]["status"] == "Completed")

    # 3.3 Edit record
    ok = update_single_record(new_id, {
        "service_type": "ucaadhar",
        "record_date": "2026-11-03",
        "name": "Live Office Tester Updated",
        "mobile": "9898099887",
        "id_number": "S1999999999999",
        "status": "Completed",
        "fee_amt": 250.0,
        "remark": "Updated Note"
    })
    test("Update single record succeeds", ok is True)
    r, _ = search_records(mobile="9898099887")
    test("Name and fee updated properly", r[0]["name"] == "Live Office Tester Updated" and r[0]["fee_amt"] == 250.0)

    # 3.4 Delete record
    ok = delete_single_record(new_id)
    test("Delete single record succeeds", ok is True)
    r, c = search_records(mobile="9898099887")
    test("Deleted record no longer in search", c == 0)

    # -------------------------------------------------------------------------
    # SUITE 4: EXCEL / CSV EXPORT
    # -------------------------------------------------------------------------
    print("\n--- [4/5] Testing Excel & CSV Exporter ---")
    export_dir = r"d:\Khodal_info\exports"
    
    # 4.1 Export All Services
    recs_all = get_all_records_for_export(service_type="all")
    p_all = export_records_to_excel(recs_all, export_dir, service_type="all")
    test("Export All Services creates valid Excel file", os.path.exists(p_all) and os.path.getsize(p_all) > 1000)

    # 4.2 Export UC Aadhaar
    recs_uc = get_all_records_for_export(service_type="ucaadhar")
    p_uc = export_records_to_excel(recs_uc, export_dir, service_type="ucaadhar")
    test("Export UC Aadhaar creates valid Excel file", os.path.exists(p_uc) and os.path.getsize(p_uc) > 1000)

    # 4.3 Export PAN Card
    recs_pan = get_all_records_for_export(service_type="pancard")
    p_pan = export_records_to_excel(recs_pan, export_dir, service_type="pancard")
    test("Export PAN Card creates valid Excel file", os.path.exists(p_pan) and os.path.getsize(p_pan) > 1000)

    # -------------------------------------------------------------------------
    # SUITE 5: REAL-WORLD EDGE CASE FILE PARSING
    # -------------------------------------------------------------------------
    print("\n--- [5/5] Testing Dirty Data, Typo Dates, Scientific Notation & Blank Rows ---")
    
    # 5.1 Test phone cleaner edge cases
    disp, norm = clean_phone("9825012345.0")
    test("Clean phone: stripped .0 from float", disp == "9825012345" and norm == "9825012345")

    disp, norm = clean_phone("+91 98250-12345")
    test("Clean phone: handles +91 and dashes", norm == "919825012345" or norm == "9825012345")

    disp, norm = clean_phone("MONTU")
    test("Clean phone: text in phone column returns empty norm", norm == "")

    # 5.2 Test date normalizer edge cases
    d = normalize_date_str("24-08-206")
    test("Normalize date: fixed typo 206 -> 2026", d == "2026-08-24")

    d = normalize_date_str("2026/10/05")
    test("Normalize date: handles slash format", d == "2026-10-05")

    # 5.3 Test creating and parsing a messy Excel file with blank rows and summary totals
    test_messy_csv = """DATE,NAME,SRN NO,MO,REMARK
2026-11-01,,,,
,Messy Client One,S999911112222,9900011122,HOF
,,,,
2026-11-02,,,,
,Messy Client Two,S999933334444,9900033344,200 BAKI
,,,,,
,,,,,4200,
"""
    messy_path = os.path.join(export_dir, "test_messy.csv")
    with open(messy_path, "w", encoding="utf-8") as f:
        f.write(test_messy_csv)

    parsed_recs, summary = parse_service_excel_or_csv(messy_path, 999, forced_service="aadhar_online")
    test("Messy file parsed only 2 actual clients (ignored empty rows & 4200 total)", len(parsed_recs) == 2, f"got {len(parsed_recs)}")
    test("Client One carried forward date 2026-11-01", parsed_recs[0]["record_date"] == "2026-11-01")
    test("Client Two carried forward date 2026-11-02", parsed_recs[1]["record_date"] == "2026-11-02")
    test("Client Two marked as baki", parsed_recs[1]["is_baki"] == 1)

    os.remove(messy_path)
    test("Temporary test file cleaned up", not os.path.exists(messy_path))

    print("\n=====================================================================")
    print(f"🎉 TEST RESULTS: {passed}/{total} TESTS PASSED (100% SUCCESS)")
    print("=====================================================================")

if __name__ == "__main__":
    run_all_tests()
