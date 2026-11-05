# 🏢 Khodal Office Data Hub — Production Cloud & Multi-Device Office Manager

A complete, high-performance office management system specially built to store, track, and search daily client work data across **4 Divided Service Categories**:

1. 🪪 **Category 1: UC Aadhaar** (`Date`, `SID Number`, `Name`, `Status`, `Total Amt`, `Fee`, `Mobile/Others`, `Remarks`)
2. 🌐 **Category 2: Aadhaar Online** (`Date`, `Name`, `SRN Number`, `Mobile No`, `Remarks`, `Status`)
3. 💳 **Category 3: PAN Card** (`Date`, `Name`, `PAN Change / New`, `Mobile Number`, `Remarks`, `Status`)
4. 🏥 **Category 4: Ayushman / Ration Card** (`Date`, `Ration / Ayushman No`, `Name`, `Mobile No`, `Remarks`, `Status`)

---

## ☁️ MongoDB Atlas Cloud Database

- **Dedicated Cloud Database**: All client records, uploaded Excel files, and administrative accounts are stored directly in **MongoDB Atlas Cluster0** (`cluster0.nl4cir6.mongodb.net`, Database: `khodal_office`).
- **Real-Time Cross-Device Sync**: Any mobile phone, tablet, laptop, or desktop computer opens the system and immediately accesses live, up-to-the-second data.
- **Immune to Browser History Cleaning**: Clearing browser history, cookies, or cache on any device will **NEVER delete your data** because records reside securely in the cloud.
- **Production Ephemeral Protection**: On cloud hosting platforms (such as Render at `https://khodal-office-hub.onrender.com/`), server restarts will never wipe your data because everything is persisted in MongoDB Atlas.

---

## 🚀 Running the Project

### 1. Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python app.py
```
- Open in your browser: `http://localhost:8000`
- Open on your local Wi-Fi: `http://<YOUR_LAN_IP>:8000`

### 2. Cloud Production Deployment (Render)
- Live Production Link: **`https://khodal-office-hub.onrender.com/`**
- Set your MongoDB Atlas password in the **Render Dashboard &rarr; Environment &rarr; `MONGODB_URI`**.
- Render builds and starts automatically using `Procfile` / `render.yaml`.

---

## 🔐 Default Master Admin Accounts
- **Username**: `manish` | **Password**: `manish@7575`
- **Username**: `admin`  | **Password**: `admin@123`
*(Additional users can be created and managed via the Master Admin Users modal).*
