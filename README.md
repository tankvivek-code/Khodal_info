# 🏢 Khodal Office Data Hub — Daily Work Progress & Search

A complete, high-performance office management system specially built to store and track daily work data across **4 Divided Field Categories**:

1. 🪪 **Demo 1: UC Aadhaar** (`Date`, `SID Number`, `Name`, `Status`, `Total Amt`, `Fee`, `Mobile/Others`, `Remarks`)
2. 🌐 **Demo 2: Aadhaar Online** (`Date`, `Name`, `SRN Number`, `Mobile No`, `Remarks`, `Status`)
3. 💳 **Demo 3: PAN Card** (`Date`, `Name`, `PAN Change / New`, `Mobile Number`, `Remarks`, `Status`)
4. 🏥 **Demo 4: Ayushman / Ration Card** (`Date`, `Ration / Ayushman No`, `Name`, `Mobile No`, `Remarks`, `Status`)

---

## 🌟 Key Features

### 1. 🗂️ Field-Divided Service Tabs
- **Instant Tab Switching**: Switch seamlessly between **All Services**, **UC Aadhaar**, **Aadhaar Online**, **PAN Card**, and **Ayushman Card**.
- **Dynamic Columns**: Each tab shows only the columns relevant to that specific service (e.g. *SID Number & Fee* for UC Aadhaar, *SRN Number* for Aadhaar Online, *PAN Change/New* for PAN Card, *Ration Card No* for Ayushman).
- **Service Count Badges**: Shows live counts for each service at a glance.

### 2. 📅 Daily Progress Tracker
- **Date Selector**: Check progress for **Today**, **Yesterday**, or choose any specific day (e.g., `2026-10-30`, `2026-10-28`).
- **Live Progress Metric Cards**:
  - 📋 **Total Applications** (daily & all-time)
  - 🟢 **Completed Work** (with % completion rate)
  - 🟡 **In-Process / Active Applications**
  - 🔴 **Baki / Action Required** (tracks dues like `200 BAKI`, `HOF THI BAKI`, `NOT RECIV`)
  - 💰 **Total Revenue / Fee Collected** (e.g. `₹48,950`)
- **1-Click Status Toggling**: Click any status pill (e.g. `InProcess`) to immediately toggle it to `Completed`!

### 3. 🔍 Multi-Field Live Search
- 👤 **Search by Name**: Live matching as you type (e.g. `Khunt`, `Patel`, `Jadwani`, `Sharma`).
- 📱 **Search by Mobile No**: Instant digit matching (e.g. `81283`, `9328318876`, `9099588811`).
- 🔢 **Search by ID Number**: Fast search across **SID Numbers**, **SRN Numbers**, and **Ration / Ayushman Card Numbers** (e.g. `S131114`, `PAJYXBXFU`).
- 🏷️ **Quick Filters**: One-click filter for **Completed Only**, **In-Process Only**, or **Baki Cases Only**.
- 💬 **Direct WhatsApp Web**: Instant green chat button next to every customer phone number (`https://wa.me/91<number>`).

### 4. 📤 Daily File Uploads (Excel / CSV)
- **Automatic Service Detection**: Automatically identifies which service the file belongs to based on column headers.
- **Handles Date Divider Rows**: Automatically carries forward dates from section headers (e.g. `2026-10-01,,,,,,`).
- **Preserves Original Files**: Saves uploaded files in `uploads/` for permanent backup.

### 5. 📥 One-Click Export
- **Export to Excel (`.xlsx`)**: Downloads a formatted spreadsheet organized according to the selected service.
- **Export to CSV**: Quick lightweight text export.

### 6. 🌐 Office Network Sharing
- Connect from any computer, tablet, or phone on the same office Wi-Fi at `http://<your-lan-ip>:8000`.

---

## 🚀 How to Run

### Method 1: Double-Click (Recommended)
Double-click **`run.bat`** in `D:\Khodal_info`. It will launch the server and open your browser automatically.

### Method 2: Command Line
```powershell
python app.py
```
Open your browser to:
- **Local:** [http://localhost:8000](http://localhost:8000)
- **Office LAN:** `http://192.168.1.7:8000`

---

## 📁 Pre-Loaded Real Office Data

All 4 demo files provided have already been loaded into your database:
- `demo1_ucaadhar.csv` &mdash; **380 UC Aadhaar Records**
- `demo2_aadhar_online.csv` &mdash; **147 Aadhaar Online Records**
- `demo3_pancard.csv` &mdash; **41 PAN Card Records**
- `demo4_aayushman.csv` &mdash; **49 Ayushman Card Records**

Total: **617 pre-loaded real records** ready to search and track!
