# 🏢 Khodal Office Data Hub — Daily Work Progress & Search

A complete, high-performance office management system specially built to store, track, and search daily client work data across **4 Divided Service Categories**:

1. 🪪 **Category 1: UC Aadhaar** (`Date`, `SID Number`, `Name`, `Status`, `Total Amt`, `Fee`, `Mobile/Others`, `Remarks`)
2. 🌐 **Category 2: Aadhaar Online** (`Date`, `Name`, `SRN Number`, `Mobile No`, `Remarks`, `Status`)
3. 💳 **Category 3: PAN Card** (`Date`, `Name`, `PAN Change / New`, `Mobile Number`, `Remarks`, `Status`)
4. 🏥 **Category 4: Ayushman / Ration Card** (`Date`, `Ration / Ayushman No`, `Name`, `Mobile No`, `Remarks`, `Status`)

---

## 📱 100% Fully Responsive (Mobile, Tablet & Desktop)

The entire interface has been upgraded with a responsive mobile-first architecture:
- 📱 **Mobile (320px–480px)**: Compact navigation bar with 1-tap `+` (New Entry) and `Upload` buttons. Secondary actions (Master Users, Cloud DB, Backup DB, Uploaded Files, Master Excel Template, LAN Share) smoothly expand from a collapsible drawer menu.
- 🪪 **Swipeable Service Tabs**: Smooth horizontal touch swiping across all 5 service categories without cutting off badges or breaking screen bounds.
- 📊 **Responsive Metric Cards**: 2-column grid on phones, 3-column grid on tablets, and 6-column grid on desktops with auto-scaling text.
- 📋 **Table Freeze Pane & Sticky Header**: On small screens, the table scrolls horizontally with momentum (`-webkit-overflow-scrolling: touch`), a sticky header (`thead th`), and a sticky primary column (`#` / Sr No) with a shadow boundary so you always retain row context.
- 🪟 **Adaptive Modals**: All modals use dynamic viewport units (`max-height: 92dvh`), scrollable form bodies, and flexible grids (`grid-cols-1 sm:grid-cols-2`) to stay fully accessible even with on-screen mobile keyboards.
- 🎯 **Touch Optimizations**: Hit targets are calibrated to 40–44px, and inputs are protected against unwanted iOS Safari auto-zoom.

---

## 🌐 Live & Production Deployment

When deployed to production (live on the internet):
- **Central Cloud Database**: The application runs on your live server or cloud host (`https://khodal-office-hub.onrender.com/`). All client records and uploaded Excel files are stored on that server's persistent disk storage (`data/khodal_office.db` and `uploads/`).
- **All Clients Share the Same Data**: Anyone who visits your live URL from Chrome, Edge, Safari, iPhone, Android, or desktop connects to the **same live database**.
- **No Browser History Vulnerability**: A client clearing browser history on their phone or laptop has **zero impact** on the server's database. The data is safely hosted on the cloud server.

### 🚀 Production Deployment Options

#### Option 1: Render.com (Live Web Service)
- **Live URL**: `https://khodal-office-hub.onrender.com/`
- Configured via `render.yaml` with persistent disk mounting `/var/data` for zero-data-loss durability.

#### Option 2: Docker Compose on Cloud VPS (DigitalOcean, AWS, Linode)
```bash
git clone <your-repo-url> khodal-info
cd khodal-info
docker compose up -d
```
All records are permanently stored in the `khodal_office_data` Docker volume.

#### Option 3: Local Office Server with Free Public HTTPS (Cloudflare Tunnel)
1. Run `START_KHODAL_OFFICE.bat` on the office computer.
2. Run Cloudflare Tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

---

## 🛡️ Local Safe Place Architecture

### 🟢 SQLite Hard Drive Database (`data/khodal_office.db`)
- **Permanent Local Storage**: All uploaded office records and client files are saved to the **SQLite Database file on your local hard drive (`D:\Khodal_info\data\khodal_office.db`)** and `uploads/` folder.
- **Immune to Browser History Cleaning**: Clearing your browser history, cache, or cookies in Google Chrome, Microsoft Edge, or Firefox will **NEVER** delete your uploaded office data because the database lives on your hard drive, not in temporary browser storage.
- **Cross-Protocol Auto-Detection**: Whether you open the app via `http://localhost:8000` or double-click `index.html` (`file:///`), the application automatically links to the local SQLite database server.
- **Multi-Tiered Backup & Recovery**: Records are also mirrored to `data/records.js` on disk, persistent IndexedDB, and rolling JSON backups.

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

### 5. 📥 One-Click Export
- **Export to Excel (`.xlsx`)**: Downloads a formatted spreadsheet organized according to the selected service category.
- **Export to CSV**: Quick lightweight text export.

### 6. 🌐 Office Network Sharing
- Connect from any computer, tablet, or mobile phone on the same office Wi-Fi at `http://<your-lan-ip>:8000`.

---

## 🚀 How to Run Locally

### Method 1: Double-Click Desktop Shortcut (Recommended)
1. Run **`CREATE_DESKTOP_SHORTCUT.bat`** once to create the **"Khodal Office Data Hub"** icon on your Desktop.
2. Double-click the shortcut anytime to launch the safe place database server. Your browser will automatically open to `http://localhost:8000`.

### Method 2: Batch Launcher
Double-click **`START_KHODAL_OFFICE.bat`** in `D:\Khodal_info`.

### Method 3: Command Line
```powershell
python app.py
```

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
