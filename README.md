# 🏢 Khodal Office Data Hub — Local Office PC & Multi-Device Hub

A complete, high-performance office management system specially built to store, track, and search daily client work data across **4 Divided Service Categories**:

1. 🪪 **Category 1: UC Aadhaar** (`Date`, `SID Number`, `Name`, `Status`, `Total Amt`, `Fee`, `Mobile/Others`, `Remarks`)
2. 🌐 **Category 2: Aadhaar Online** (`Date`, `Name`, `SRN Number`, `Mobile No`, `Remarks`, `Status`)
3. 💳 **Category 3: PAN Card** (`Date`, `Name`, `PAN Change / New`, `Mobile Number`, `Remarks`, `Status`)
4. 🏥 **Category 4: Ayushman / Ration Card** (`Date`, `Ration / Ayushman No`, `Name`, `Mobile No`, `Remarks`, `Status`)

---

## 🛡️ Permanent Local Safe Place Architecture

### 🟢 Local Hard Drive SQLite Database (`data/khodal_office.db`)
- **Permanent Local Storage**: All uploaded office records and client files are saved directly to the **SQLite Database on your local hard drive (`D:\Khodal_info\data\khodal_office.db`)** and the `uploads/` folder.
- **Immune to Browser History Cleaning**: Clearing your browser history, cache, or cookies in Google Chrome, Microsoft Edge, or Firefox on this computer or any connected mobile device will **NEVER delete your office records** because data lives on the computer's hard drive, not in temporary browser memory.
- **Auto-Sync Backups**: Every write automatically mirrors to `data/backups/khodal_backup_latest.json` for rolling disaster recovery.

---

## 📱 Multi-Device Wi-Fi Connection (Phones, Tablets & Laptops)

You can use Khodal Office Hub across **multiple devices at the same time** (mobile phones, tablets, other staff laptops) all sharing the **same central database** on your main PC:

### Quick 3-Step Setup for Any Device:
1. **Connect to Same Wi-Fi**: Connect your mobile phone or laptop to the **same office Wi-Fi** or mobile hotspot as this main computer.
2. **Scan QR Code or Open Link**:
   - On the main computer, click the **📱 Connect Devices** button in the top navigation bar.
   - Point your phone camera at the **QR Code** displayed on screen, or type the Wi-Fi link into Chrome/Safari (e.g. `http://192.168.1.7:8000`).
3. **Start Working**: Any record created or Excel sheet uploaded on your phone is **automatically saved directly into the main computer's database (`khodal_office.db`)**.

### 🔓 Windows Firewall Troubleshooting (`ALLOW_FIREWALL_PORT_8000.bat`)
If your mobile phone or another laptop says *“Site can’t be reached”* or hangs when connecting:
- Windows Defender Firewall is blocking inbound connections on port 8000.
- Double-click **`ALLOW_FIREWALL_PORT_8000.bat`** in `D:\Khodal_info`.
- This unblocks port 8000 in Windows Firewall with 1 click, allowing all office devices to connect instantly!

---

## 💻 How to Run on This Computer Daily

### Method 1: Double-Click Desktop Shortcut (Fastest)
1. Go to your Windows **Desktop**.
2. Double-click the **"Khodal Office Data Hub"** shortcut icon.
3. Your browser automatically opens to `http://localhost:8000`.

### Method 2: Batch Launcher
1. Open folder `D:\Khodal_info`.
2. Double-click **`START_KHODAL_OFFICE.bat`**.
3. It displays your local URL (`http://localhost:8000`) and your office Wi-Fi URL (`http://<LAN_IP>:8000`), then launches your browser automatically.

---

## 🆕 How to Set Up on a Brand New Computer (`SETUP_NEW_DEVICE.bat`)

If you get a new computer or want to install Khodal Office Hub on a secondary PC:

1. Copy the entire **`Khodal_info`** folder onto the new computer (e.g. onto `D:\` or `C:\`).
2. Double-click **`SETUP_NEW_DEVICE.bat`**:
   - Verifies Python 3.10+ installation.
   - Automatically installs required dependencies (`pip install -r requirements.txt`).
   - Creates required folders (`data`, `uploads`, `exports`).
   - Automatically configures Windows Firewall for port 8000.
   - Creates the **"Khodal Office Data Hub"** icon on the new computer's Desktop.
   - Starts the database server and opens `http://localhost:8000`!
3. **To Transfer Your Existing Data**:
   - Copy the `data\khodal_office.db` file from the old computer into the new computer's `data\` folder, OR
   - On the old computer, click **Backup DB** -> **Download Backup (.json)**, then on the new computer, click **Restore Backup** and select that file.

---

## 🌟 Key Architecture & Data Rules

### 🚫 Zero Static / Fake Data Policy
- **No Mock or Demo Data**: All static and fake sample records have been completely removed from the project folder.
- **Pure Excel Data Source**: Records are only taken from Excel (`.xlsx`, `.xls`) or CSV (`.csv`) files uploaded by the user directly through the browser.
- **Clean Starting State**: Starts with **0 records** and displays a clean empty state with an upload prompt. Fake or dummy records will **never** appear.

---

## 🌟 Key Features

### 1. 📤 Browser Excel Upload (.xlsx / .xls / .csv)
- **Automatic Service Detection**: Upload single or multi-sheet Excel files. The system automatically inspects sheet names and column headers to assign records to UC Aadhaar, Aadhaar Online, PAN Card, or Ayushman Card.
- **Header & Date Parsing**: Automatically parses various date formats (DD-MM-YYYY, DD/MM/YYYY, ISO, Excel numeric dates) and extracts client contact numbers.
- **Original File Preservation**: Uploaded files and raw binary blobs are permanently stored in SQLite (`data/khodal_office.db`) and `uploads/`.

### 2. 🗂️ Field-Divided Service Tabs
- **Instant Tab Switching**: Seamlessly switch between **All Services**, **UC Aadhaar**, **Aadhaar Online**, **PAN Card**, and **Ayushman Card**.
- **Dynamic Columns**: Each tab shows only the columns relevant to that specific category (e.g. *SID Number & Fee* for UC Aadhaar, *SRN Number* for Aadhaar Online, *PAN Change/New* for PAN Card, *Ration Card No* for Ayushman).
- **Live Badges**: Real-time counter badges on each tab reflect current loaded records.

### 3. 📅 Daily Progress Tracker
- **Date Selector**: View progress for **Today**, **Yesterday**, **All Dates**, or choose any specific calendar day.
- **Live Progress Metric Cards**:
  - 📋 **Total Applications** (daily & total)
  - 🟢 **Completed Work** (with % completion rate)
  - 🟡 **In-Process / Active Applications**
  - 🔴 **Baki / Action Required** (tracks dues like `200 BAKI`, `HOF THI BAKI`, `NOT RECIV`)
  - 💰 **Total Revenue / Fee Collected** (e.g. `₹48,950`)
- **1-Click Status Toggling**: Click any status pill (e.g. `InProgress`) to toggle it to `Completed` or `Rejected` directly from the table.

### 4. 🔍 Multi-Field Live Search
- 👤 **Search by Name**: Live matching as you type (e.g. `Khunt`, `Patel`, `Jadwani`, `Sharma`).
- 📱 **Search by Mobile No**: Instant digit matching (e.g. `98250`, `9328318876`).
- 🔢 **Search by ID Number**: Fast search across **SID Numbers**, **SRN Numbers**, and **Ration / Ayushman Card Numbers**.
- 🏷️ **Quick Filters**: One-click filter for **Completed Only**, **In-Process Only**, or **Baki Cases Only**.
- 💬 **Direct WhatsApp Web**: Instant green chat button next to every customer phone number (`https://wa.me/91<number>`).

### 5. 📥 One-Click Export & Backup
- **Export to Excel (`.xlsx`)**: Downloads a formatted spreadsheet organized according to the selected service category.
- **1-Click JSON Backup**: Downloads `khodal_backup_<date>.json` containing all client records and files for instant transfer to another device.

---

## 🔐 Master Users & Authentication

All master user credentials and authentication sessions are permanently stored in the **SQLite Database (`data/khodal_office.db`)**:

- **Default Master Users**:
  - `manish` &mdash; Password: `manish@7575`
  - `admin` &mdash; Password: `admin@7575`
- **Dynamic Master User Creation**: Click the **Master Users** button in the top navigation bar to view all active master users or add new master users with custom usernames and passwords.
- **Secure Sessions**: Login sessions are authenticated via database session tokens; no user passwords or sensitive record data are exposed in browser storage.

---

## 📁 Excel Upload & Templates

To import data, click the **Upload Office File** button in the header or in the table empty state, select your Excel spreadsheet (`.xlsx`, `.xls`, or `.csv`), and confirm.

Standard templates are available in the `templates/` directory and can also be downloaded directly from the application:
- `Khodal_Office_Master_Template.xlsx` (Multi-sheet: UC Aadhaar, Aadhaar Online, PAN Card, Ayushman Card)
- `Template_1_UC_Aadhaar.xlsx`
- `Template_2_Aadhaar_Online.xlsx`
- `Template_3_PAN_Card.xlsx`
- `Template_4_Ayushman_Card.xlsx`
