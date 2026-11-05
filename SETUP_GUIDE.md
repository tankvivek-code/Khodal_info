# 📖 Khodal Office Data Hub — Complete Setup & User Guide

Welcome to the **Khodal Office Data Hub**. This guide explains step-by-step how to run, use, connect multiple devices, and set up this project on any new computer.

---

## 📌 Quick Summary
* **Database Location**: Stored permanently on hard drive at `D:\Khodal_info\data\khodal_office.db`
* **Immune to Browser History Cleaning**: Clearing cache/history on Chrome, Edge, or mobile will **NEVER delete your data**.
* **Default Login Credentials**:
  * Username: `manish` | Password: `manish@7575`
  * Username: `admin`  | Password: `admin@7575`

---

## 🖥️ PART 1: How to Run on This Main Computer (Daily Use)

Follow these steps every day when you open your office:

1. **Step 1: Start the Database Server**
   * Double-click the **"Khodal Office Data Hub"** shortcut icon on your Windows Desktop.
   * *(Or open `D:\Khodal_info` and double-click `START_KHODAL_OFFICE.bat`)*

2. **Step 2: Browser Opens Automatically**
   * Your web browser will automatically open:
     👉 **`http://localhost:8000`**

3. **Step 3: Log In**
   * Enter username `manish` and password `manish@7575` (or `admin` / `admin@7575`).

4. **Step 4: Upload or Enter Data**
   * Click **Upload Office File** to import your Excel sheet (`.xlsx`, `.xls`, `.csv`).
   * Or click **`+` (New Entry)** to add individual client records.
   * All data is immediately saved onto your hard drive in `data\khodal_office.db`.

---

## 📱 PART 2: How to Connect Other Devices (Phones, Tablets & Laptops)

You can use the system on multiple mobile phones and laptops at the same time:

```
                      ┌──────────────────────────────────────┐
                      │          Office Wi-Fi Router         │
                      └──────────────────┬───────────────────┘
                                         │
       ┌─────────────────────────────────┼────────────────────────────────┐
       ▼                                 ▼                                ▼
💻 Main Office PC                📱 Mobile Phones                 💻 Staff Laptops
 (Runs Server & DB)              (Scan QR Code)                   (Open in Chrome)
 http://localhost:8000           http://192.168.1.7:8000          http://192.168.1.7:8000
 [data/khodal_office.db]         (Saves to Main PC DB)            (Saves to Main PC DB)
```

### Steps to Connect Any Mobile or Laptop:

1. **Step 1: Connect to Same Office Wi-Fi**
   * Make sure your mobile phone or laptop is connected to the **same office Wi-Fi** (or mobile hotspot) as the main computer.

2. **Step 2: Open "Connect Devices" on Main PC**
   * On the main computer screen, click the green **"📱 Connect Devices"** button in the top navigation bar.

3. **Step 3: Scan QR Code or Type Link**
   * **On Mobile Phone**: Open your phone's camera and point it at the **QR Code** on screen. Tap the link that appears.
   * **On Another Laptop**: Open Google Chrome or Safari and type your office Wi-Fi URL (example: `http://192.168.1.7:8000`).

4. **Step 4: Start Using Immediately**
   * Any client record added or Excel sheet uploaded on your phone is **automatically saved directly into the main computer's database**.
   * Even if someone clears their phone's browser history, the data is 100% safe on the main computer's hard drive!

### ⚠️ Troubleshooting: Phone Says "Site Can't Be Reached"?
If your mobile phone cannot open the link, Windows Firewall on the main computer is blocking port 8000.
* **The 1-Click Fix**: In `D:\Khodal_info`, double-click **`ALLOW_FIREWALL_PORT_8000.bat`**.
* This unblocks port 8000 in Windows Firewall so other devices connect freely.

---

## 🆕 PART 3: How to Set Up on a Brand New Computer

If you buy a new computer or want to install Khodal Office on a second PC:

1. **Step 1: Copy the Project Folder**
   * Copy the entire **`Khodal_info`** folder using a USB pen drive to the new computer (e.g. into `D:\Khodal_info` or `C:\Khodal_info`).

2. **Step 2: Make Sure Python is Installed**
   * Check if Python is installed: open Command Prompt and type `python --version`.
   * If not installed: download Python 3.10+ from [python.org/downloads](https://www.python.org/downloads/).
   * ⚠️ **CRITICAL**: Check the box **"Add Python to PATH"** during installation.

3. **Step 3: Run the 1-Click Setup Wizard**
   * Open the `Khodal_info` folder on the new computer.
   * Double-click **`SETUP_NEW_DEVICE.bat`**.
   * The setup wizard will automatically:
     1. Install all required dependencies (`FastAPI`, `Uvicorn`, `Pandas`, `Openpyxl`).
     2. Create all required folders (`data`, `uploads`, `exports`).
     3. Configure Windows Firewall to allow port 8000.
     4. Create the **"Khodal Office Data Hub"** shortcut icon on the new computer's Desktop.
     5. Start the server and launch the browser!

4. **Step 4: Transfer Your Existing Records (Optional)**
   * **Option A**: Copy `data\khodal_office.db` from your old computer into `data\` on the new computer.
   * **Option B**: On the old computer, click **Backup DB** -> **Download Backup (.json)**. On the new computer, open the site, click **Restore Backup**, and select your `.json` file.

---

## 💾 PART 4: 1-Click Database Backup & Restore

Always keep a copy of your records for peace of mind:

### To Create a Backup:
1. In the top navigation bar, click **Backup DB**.
2. Click **Download Backup (.json)**.
3. A file like `khodal_backup_2026-11-05.json` will be saved to your Downloads folder. You can copy this file to Google Drive, a USB drive, or WhatsApp.

### To Restore From a Backup:
1. Click **Connect Devices** (or open the backup section).
2. Click **Restore Backup**.
3. Select your `.json` backup file.
4. All client records and files are instantly re-imported into your SQLite database.

---

## ❓ PART 5: Frequently Asked Questions (FAQ)

### Q1: Will clearing browser history on my PC or phone delete my data?
**NO, NEVER.** All client data, master users, and Excel files are stored in the SQLite database file on the computer's hard drive (`data/khodal_office.db`). Browser history only stores temporary web cache, not your database.

### Q2: Does the office setup need an active internet connection?
**NO.** The system runs 100% locally on your office local area network (LAN) or mobile hotspot. Even if internet is down, all computers and phones on the same Wi-Fi can work without interruption.

### Q3: Can multiple staff members enter records at the same time?
**YES.** Staff on their phones and computers can all add entries simultaneously. All entries are saved into the single centralized database.

### Q4: How do I create a new master user or change password?
Click the **Master Users** button in the top navigation bar to view all active master users or add new users with custom usernames and passwords.

---

## 📁 Key File Index for Quick Reference:
* **`START_KHODAL_OFFICE.bat`**: Starts the local server and opens browser (`http://localhost:8000`).
* **`SETUP_NEW_DEVICE.bat`**: 1-click installer and setup wizard for any new computer.
* **`ALLOW_FIREWALL_PORT_8000.bat`**: 1-click Windows Firewall unblock for port 8000.
* **`CREATE_DESKTOP_SHORTCUT.bat`**: Re-creates the Desktop shortcut if deleted.
* **`data/khodal_office.db`**: The permanent SQLite database file containing all your records.
* **`templates/`**: Folder containing master Excel templates for data entry and upload.
