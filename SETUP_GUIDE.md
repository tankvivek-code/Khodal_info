# 📖 Khodal Office Data Hub — Production Setup & Deployment Guide

Welcome to the **Khodal Office Data Hub**. The project is built as a **Production-Grade Cloud Application** powered by **FastAPI** and **MongoDB Atlas Cloud Database**.

---

## ☁️ Architecture Overview
* **Cloud Database**: MongoDB Atlas Cluster0 (`cluster0.nl4cir6.mongodb.net`, Database: `khodal_office`).
* **Multi-Device Real-Time Sync**: Any mobile phone, tablet, laptop, or desktop computer accesses and edits the exact same database in real-time from anywhere.
* **Platform Independent**: No Windows batch (`.bat`) files needed. Runs natively on Linux cloud servers (Render, Docker, AWS, Heroku) and locally via standard Python commands (`python app.py`).
* **Zero Ephemeral Loss**: Cloud hosts (like Render) restart frequently; because all data lives in MongoDB Atlas, restarts never lose a single record or file!

---

## 🚀 PART 1: MongoDB Atlas Cloud Database Setup

1. **MongoDB Connection URI**:
   ```
   mongodb+srv://tankvivek65_db_user:<YOUR_ACTUAL_PASSWORD>@cluster0.nl4cir6.mongodb.net/?compressors=zlib
   ```
2. **Setting the Password Locally**:
   - In `.env` file in the project folder:
     ```env
     MONGODB_URI=mongodb+srv://tankvivek65_db_user:YOUR_PASSWORD_HERE@cluster0.nl4cir6.mongodb.net/?compressors=zlib
     MONGODB_DB_NAME=khodal_office
     ```
   - *OR* open the web app at `http://localhost:8000`, click **"Enter Password Now"** in the top banner, and submit your password in the Cloud Settings modal.

3. **Setting the Password on Render Production (`https://khodal-office-hub.onrender.com/`)**:
   - Open your **Render Dashboard** (`dashboard.render.com`).
   - Click on your service **`khodal-office-hub`**.
   - Go to **Environment** tab.
   - Add/Edit the Environment Variable:
     - **Key**: `MONGODB_URI`
     - **Value**: `mongodb+srv://tankvivek65_db_user:YOUR_PASSWORD_HERE@cluster0.nl4cir6.mongodb.net/?compressors=zlib`
     - **Key**: `MONGODB_DB_NAME`
     - **Value**: `khodal_office`
   - Click **Save Changes**. Render automatically redeploys and connects to MongoDB Atlas!

---

## 💻 PART 2: Running Locally on Any Computer

### Prerequisites
* Python 3.10+ (Recommended: Python 3.12)
* Git

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/tankvivek-code/Khodal_info.git
   cd Khodal_info
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Start the Application**:
   ```bash
   python app.py
   ```
4. **Open in Browser**:
   - Local: `http://localhost:8000`
   - Office LAN (Wi-Fi): `http://<YOUR_LOCAL_IP>:8000` (e.g. `http://192.168.1.7:8000`)

---

## 🌐 PART 3: Cloud Deployment (Render / Docker)

### Deploying to Render
1. Push your changes to GitHub:
   ```bash
   git push origin main
   ```
2. Render automatically detects `render.yaml` and `Procfile`:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. Enter `MONGODB_URI` in the Render Environment Variables tab with your MongoDB Atlas password.

### Running with Docker
```bash
docker build -t khodal-office-hub .
docker run -p 8000:8000 -e MONGODB_URI="mongodb+srv://tankvivek65_db_user:PASSWORD@cluster0.nl4cir6.mongodb.net/?compressors=zlib" khodal-office-hub
```

---

## 🔐 Default Master Admin Credentials
* **Username**: `manish` | **Password**: `manish@7575`
* **Username**: `admin`  | **Password**: `admin@123`
*(New admin accounts can be created and managed via the Master Admin Users modal).*
