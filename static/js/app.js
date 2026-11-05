// Khodal Office Data Hub - Multi-Service & Daily Work Progress Manager







let currentServiceTab = "all";







let currentDateFilter = "";







let currentStatusFilter = "all";







let isBakiOnly = false;







let currentPage = 1;







let pageSize = 25;







let totalPages = 1;







let totalRecords = 0;







let currentRecords = [];







let searchDebounceTimer = null;







let selectedUploadFile = null;







let lanShareUrl = "";







let currentViewRecord = null;







// Service Badges and Colors Mapping







const SERVICE_META = {







    ucaadhar: { name: "UC Aadhaar", color: "blue", label: "🪪 UC Aadhaar (SID)" },







    aadhar_online: { name: "Aadhaar Online", color: "emerald", label: "🌐 Aadhaar Online (SRN)" },







    pancard: { name: "PAN Card", color: "amber", label: "💳 PAN Card" },







    aayushman: { name: "Ayushman Card", color: "purple", label: "🏥 Ayushman Card" },







    all: { name: "All Services", color: "brand", label: "🌟 All Services" }







};







// =========================================================================







// DATE FORMATTERS (Strict DD-MM-YYYY User Display)







// =========================================================================







const MONTH_NAMES_MAP = {







    jan: "01", january: "01",







    feb: "02", february: "02",







    mar: "03", march: "03",







    apr: "04", april: "04",







    may: "05",







    jun: "06", june: "06",







    jul: "07", july: "07",







    aug: "08", august: "08",







    sep: "09", sept: "09", september: "09",







    oct: "10", october: "10",







    nov: "11", november: "11",







    dec: "12", december: "12"







};







function formatDateDisplay(val) {







    if (!val) return "-";







    // 1. JS Date object







    if (val instanceof Date && !isNaN(val)) {







        const day = String(val.getDate()).padStart(2, '0');







        const month = String(val.getMonth() + 1).padStart(2, '0');







        const year = val.getFullYear();







        return `${day}-${month}-${year}`;







    }







    // 2. Numeric Excel serial date (e.g. 46328)







    if (typeof val === "number" && val >= 30000 && val <= 65000) {







        const d = new Date(Math.round((val - 25569) * 86400 * 1000));







        const day = String(d.getUTCDate()).padStart(2, '0');







        const month = String(d.getUTCMonth() + 1).padStart(2, '0');







        const year = d.getUTCFullYear();







        return `${day}-${month}-${year}`;







    }







    const s = String(val).trim();







    if (!s || s === "-" || s.toLowerCase() === "nan") return "-";







    // 3. String numeric Excel serial (e.g. "46328")







    if (/^\d{5}(\.\d+)?$/.test(s)) {







        const num = parseFloat(s);







        if (num >= 30000 && num <= 65000) {







            const d = new Date(Math.round((num - 25569) * 86400 * 1000));







            const day = String(d.getUTCDate()).padStart(2, '0');







            const month = String(d.getUTCMonth() + 1).padStart(2, '0');







            const year = d.getUTCFullYear();







            return `${day}-${month}-${year}`;







        }







    }







    // 4. Match ISO YYYY-MM-DD or YYYY/MM/DD or YYYY-DD-MM (Excel US-locale flip)







    const mIso = s.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);







    if (mIso) {







        const y = mIso[1];







        const p1 = parseInt(mIso[2], 10);







        const p2 = parseInt(mIso[3], 10);







        if (p2 === 10 && p1 >= 1 && p1 <= 12) {







            return `${String(p1).padStart(2, '0')}-10-${y}`;







        }







        if (p2 === 11 && p1 >= 1 && p1 <= 12) {







            return `${String(p1).padStart(2, '0')}-11-${y}`;







        }







        return `${String(p2).padStart(2, '0')}-${String(p1).padStart(2, '0')}-${y}`;







    }







    // 5. Match DD-MM-YYYY or DD/MM/YYYY or D-M-YYYY







    const mDm = s.match(/(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})/);







    if (mDm) {







        const day = String(mDm[1]).padStart(2, '0');







        const month = String(mDm[2]).padStart(2, '0');







        let year = mDm[3];







        if (year.length === 2) year = "20" + year;







        return `${day}-${month}-${year}`;







    }







    // 6. Match DD-MonthName-YYYY (e.g. 15-Oct-2026 or 15 October 2026)







    const mNamed = s.match(/^(\d{1,2})[-/\s]+([a-zA-Z]+)[-/\s]+(\d{2,4})/);







    if (mNamed) {







        const day = String(mNamed[1]).padStart(2, '0');







        const monthKey = mNamed[2].toLowerCase();







        const month = MONTH_NAMES_MAP[monthKey] || "01";







        let year = mNamed[3];







        if (year.length === 2) year = "20" + year;







        return `${day}-${month}-${year}`;







    }







    return s;







}







function normalizeDateToIso(val) {







    if (!val) return "";







    if (val instanceof Date && !isNaN(val)) {







        const y = val.getFullYear();







        const m = String(val.getMonth() + 1).padStart(2, '0');







        const d = String(val.getDate()).padStart(2, '0');







        return `${y}-${m}-${d}`;







    }







    const s = String(val).trim();







    if (!s || s === "-" || s.toLowerCase() === "nan") return "";







    const mDm = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);







    if (mDm) {







        return `${mDm[3]}-${String(mDm[2]).padStart(2, '0')}-${String(mDm[1]).padStart(2, '0')}`;







    }







    const mIso = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);







    if (mIso) {







        const y = mIso[1];







        const p1 = parseInt(mIso[2], 10);







        const p2 = parseInt(mIso[3], 10);







        if (p2 === 10 && p1 >= 1 && p1 <= 12) {







            return `${y}-10-${String(p1).padStart(2, '0')}`;







        }







        if (p2 === 11 && p1 >= 1 && p1 <= 12) {







            return `${y}-11-${String(p1).padStart(2, '0')}`;







        }







        return `${y}-${String(p1).padStart(2, '0')}-${String(p2).padStart(2, '0')}`;







    }







    return s;







}







// =========================================================================







// HYBRID DATA STORE (Seamless GitHub Pages & Static Mode Support)







// =========================================================================







// Automatically purge old demo stores







try {







    localStorage.removeItem("khodal_records_store_v3");







    localStorage.removeItem("khodal_files_list_v3");







    localStorage.removeItem("khodal_records_store_v2");







    localStorage.removeItem("khodal_files_list_v2");







    localStorage.removeItem("khodal_records_store_v1");







    localStorage.removeItem("khodal_records_store");







} catch (e) {}







const isGitHubPages = window.location.hostname.includes("github.io");







const isFileProtocol = window.location.protocol === "file:";







const DEFAULT_BACKEND_URL = "http://localhost:8000";



const CUSTOM_CLOUD_URL_KEY = "khodal_custom_cloud_url";



let customCloudUrl = "";



try {



    customCloudUrl = localStorage.getItem(CUSTOM_CLOUD_URL_KEY) || "";



} catch (e) {}











let API_BASE = "";







let isStaticMode = true;







let staticRecords = [];







const STORAGE_KEY = "khodal_records_store_v8";







const FILES_STORAGE_KEY = "khodal_files_list_v8";







const USERS_STORAGE_KEY = "khodal_static_users_v8";







const AUTH_SESSION_KEY = "khodal_static_auth_session_v8";







function getActiveSessionToken() {



    try {



        return localStorage.getItem("khodal_session_token") || sessionStorage.getItem("khodal_session_token") || "";



    } catch (e) {



        return "";



    }



}







// Safe API URL builder supporting both localhost:8000 and file:/// protocols







function apiUrl(path) {







    if (!path) return API_BASE || "";







    if (path.startsWith("http://") || path.startsWith("https://")) return path;







    if (!path.startsWith("/")) path = "/" + path;







    return `${API_BASE}${path}`;







}







// Automatic detection of SQLite backend server (safe place on disk)







async function detectApiBase() {
    // 0. Recover cloud URL from IndexedDB if not found in localStorage
    if (!customCloudUrl) {
        try {
            const idbUrl = await getFromIndexedDB("custom_cloud_url");
            if (idbUrl) {
                customCloudUrl = idbUrl;
                try { localStorage.setItem(CUSTOM_CLOUD_URL_KEY, idbUrl); } catch (e) {}
            }
        } catch (e) {}
    }

    // 1. Check custom Cloud Server URL if provided
    if (customCloudUrl) {



        try {



            const controller = new AbortController();



            const to = setTimeout(() => controller.abort(), 3500);



            const res = await fetch(`${customCloudUrl}/api/info`, { signal: controller.signal });



            clearTimeout(to);



            if (res.ok) {



                API_BASE = customCloudUrl;



                return true;



            }



        } catch (e) {}



    }







    // 2. Check same-origin API (if hosted full-stack or on localhost)



    if (!isFileProtocol && !isGitHubPages) {



        try {



            const controller = new AbortController();



            const to = setTimeout(() => controller.abort(), 1200);



            const res = await fetch("/api/info", { signal: controller.signal });



            clearTimeout(to);



            if (res.ok) {



                API_BASE = "";



                return true;



            }



        } catch (e) {}



    }







    // 3. Check localhost backend (file:/// or local development)



    if (isFileProtocol || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {



        try {



            const controller = new AbortController();



            const to = setTimeout(() => controller.abort(), 1200);



            const res = await fetch(`${DEFAULT_BACKEND_URL}/api/info`, { signal: controller.signal });



            clearTimeout(to);



            if (res.ok) {



                API_BASE = DEFAULT_BACKEND_URL;



                return true;



            }



        } catch (e) {}



    }

    // 4. Auto-detect Render Cloud backend if running on GitHub Pages
    if (isGitHubPages) {
        const defaultCandidates = ["https://khodal-office-hub.onrender.com"];
        for (const cand of defaultCandidates) {
            try {
                const controller = new AbortController();
                const to = setTimeout(() => controller.abort(), 2500);
                const res = await fetch(`${cand}/api/info`, { signal: controller.signal });
                clearTimeout(to);
                if (res.ok) {
                    API_BASE = cand;
                    customCloudUrl = cand;
                    try {
                        localStorage.setItem(CUSTOM_CLOUD_URL_KEY, cand);
                        saveToIndexedDB("custom_cloud_url", cand).catch(() => {});
                    } catch (e) {}
                    return true;
                }
            } catch (e) {}
        }
    }







    return false;



}







function openKhodalIDB() {







    return new Promise((resolve) => {







        if (!window.indexedDB) return resolve(null);







        try {







            const req = indexedDB.open("khodal_safe_place_db", 1);







            req.onupgradeneeded = (e) => {







                const db = e.target.result;







                if (!db.objectStoreNames.contains("safe_store")) {







                    db.createObjectStore("safe_store");







                }







            };







            req.onsuccess = (e) => resolve(e.target.result);







            req.onerror = () => resolve(null);







        } catch (e) {







            resolve(null);







        }







    });







}







async function saveToIndexedDB(key, val) {







    try {







        const db = await openKhodalIDB();







        if (!db) return false;







        return new Promise((resolve) => {







            const tx = db.transaction("safe_store", "readwrite");







            const store = tx.objectStore("safe_store");







            store.put(val, key);







            tx.oncomplete = () => resolve(true);







            tx.onerror = () => resolve(false);







        });







    } catch (e) {







        return false;







    }







}







async function getFromIndexedDB(key) {







    try {







        const db = await openKhodalIDB();







        if (!db) return null;







        return new Promise((resolve) => {







            const tx = db.transaction("safe_store", "readonly");







            const store = tx.objectStore("safe_store");







            const req = store.get(key);







            req.onsuccess = () => resolve(req.result);







            req.onerror = () => resolve(null);







        });







    } catch (e) {







        return null;







    }







}







const DEFAULT_MASTER_USERS = [







    { id: 1, username: "manish", full_name: "Manish", role: "master", is_active: 1, password: "manish@7575", created_at: "2026-11-03 15:18:20", last_login: "2026-11-03 21:00:00" },







    { id: 2, username: "admin", full_name: "Master Admin", role: "master", is_active: 1, password: "admin@7575", created_at: "2026-11-03 16:00:00", last_login: "2026-11-03 21:00:00" }







];







// Purge only legacy browser storage keys from earlier iterations







(function purgeLegacyData() {







    const legacyKeys = [







        "khodal_records_store_v7", "khodal_files_list_v7", "khodal_static_users_v7", "khodal_static_auth_session_v7",







        "khodal_master_session_v1", "khodal_master_session", "khodal_auth",







        "khodal_records_store_v6", "khodal_files_list_v6",







        "khodal_records_store_v5", "khodal_files_list_v5",







        "khodal_records_store_v4", "khodal_files_list_v4",







        "khodal_records_store_v3", "khodal_files_list_v3",







        "khodal_records_store_v2", "khodal_files_list_v2",







        "khodal_records_store_v1", "khodal_files_list_v1",







        "khodal_records_store", "khodal_files_list"







    ];







    legacyKeys.forEach(k => {







        try {







            localStorage.removeItem(k);







            sessionStorage.removeItem(k);







        } catch (e) {}







    });







})();







function getStaticUsers() {







    try {







        const saved = localStorage.getItem(USERS_STORAGE_KEY);







        if (saved) {







            const parsed = JSON.parse(saved);







            if (Array.isArray(parsed) && parsed.length > 0) return parsed;







        }







    } catch (e) {}







    if (window.KHODAL_MASTER_USERS && Array.isArray(window.KHODAL_MASTER_USERS) && window.KHODAL_MASTER_USERS.length > 0) {







        const users = window.KHODAL_MASTER_USERS.map(u => ({







            ...u,







            password: (u.username === "admin") ? "admin@7575" : "manish@7575"







        }));







        saveStaticUsers(users);







        return users;







    }







    return DEFAULT_MASTER_USERS.slice();







}







function saveStaticUsers(users) {







    try {







        localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users || []));







    } catch (e) {}







}







function getStaticFiles() {







    const saved = localStorage.getItem(FILES_STORAGE_KEY);







    if (saved) {







        try {







            const parsed = JSON.parse(saved);







            if (Array.isArray(parsed) && parsed.length > 0) return parsed;







        } catch (e) {}







    }







    if (window.KHODAL_INITIAL_FILES && Array.isArray(window.KHODAL_INITIAL_FILES) && window.KHODAL_INITIAL_FILES.length > 0) {







        return window.KHODAL_INITIAL_FILES.slice();







    }







    return [];







}







function saveStaticFiles(filesList) {







    try {







        localStorage.setItem(FILES_STORAGE_KEY, JSON.stringify(filesList || []));







    } catch (e) {}







    saveToIndexedDB("files", filesList || []).catch(() => {});







}







function saveStaticRecords(records) {



    staticRecords = records || [];



    try {



        localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));



    } catch (e) {}



    saveToIndexedDB("records", staticRecords).catch(() => {});



}







async function initDataStore() {







    // 1. Detect if SQLite disk server is online (Safe Place)







    const isOnline = await detectApiBase();







    if (isOnline) {







        isStaticMode = false;







        updateDatabaseStatusBadge();







        if (navigator.storage && navigator.storage.persist) {







            navigator.storage.persist().catch(() => {});







        }







        return;







    }







    // 2. Offline / Client-Side mode: use multi-tier persistent storage







    isStaticMode = true;







    staticRecords = [];







    // Tier A: Check localStorage







    const cached = localStorage.getItem(STORAGE_KEY);







    if (cached) {







        try {







            const parsed = JSON.parse(cached);







            if (Array.isArray(parsed) && parsed.length > 0) {







                staticRecords = parsed;







            }







        } catch (e) {}







    }







    // Tier B: Check IndexedDB (survives standard browser history clearing)







    if (!staticRecords || staticRecords.length === 0) {







        try {







            const idbRecords = await getFromIndexedDB("records");







            if (Array.isArray(idbRecords) && idbRecords.length > 0) {







                staticRecords = idbRecords;







                try {







                    saveStaticRecords(staticRecords);







                } catch (e) {}







            }







        } catch (e) {}







    }







    // Tier C: Recover real uploaded records from disk file (data/records.js) if available







    if (!staticRecords || staticRecords.length === 0) {







        if (window.KHODAL_RECORDS && Array.isArray(window.KHODAL_RECORDS) && window.KHODAL_RECORDS.length > 0) {







            staticRecords = window.KHODAL_RECORDS.slice();







            try {







                saveStaticRecords(staticRecords);







                saveToIndexedDB("records", staticRecords).catch(() => {});







            } catch (e) {}







        }







    }







    // Initialize files and users







    let files = getStaticFiles();







    if (!files || files.length === 0) {







        try {







            const idbFiles = await getFromIndexedDB("files");







            if (Array.isArray(idbFiles) && idbFiles.length > 0) {







                files = idbFiles;







            }







        } catch (e) {}







    }







    saveStaticFiles(files);







    const users = getStaticUsers();







    saveStaticUsers(users);







    // Request persistent storage permission so browser history clearing avoids wiping data







    if (navigator.storage && navigator.storage.persist) {







        navigator.storage.persist().catch(() => {});







    }







    updateDatabaseStatusBadge();







}







// Background auto-reconnect checker: connects to SQLite server when user starts it







setInterval(async () => {







    if (isStaticMode) {







        const connected = await detectApiBase();







        if (connected) {







            isStaticMode = false;







            showToast("🟢 Connected to SQLite Disk Database! Data is now safe on disk.", "success");







            updateDatabaseStatusBadge();







            await syncOfflineRecordsToServer();







            await loadDailyProgress();







            await fetchRecords(1);







        }







    }







}, 3000);







async function checkServerConnection() {







    showToast("Checking connection to Khodal Office Server...", "info");







    const ok = await detectApiBase();







    if (ok) {







        isStaticMode = false;







        updateDatabaseStatusBadge();







        showToast("🟢 Connected to SQLite Disk Database! Safe Place active on disk.", "success");







        await syncOfflineRecordsToServer();







        await loadDailyProgress();







        await fetchRecords(1);







    } else {







        showToast("⚠️ Server is not running. Double-click START_KHODAL_OFFICE.bat in D:\\Khodal_info", "warning");







    }







}







async function syncOfflineRecordsToServer() {



    if (isStaticMode || !staticRecords || staticRecords.length === 0) return;



    try {



        const token = getActiveSessionToken();



        const headers = { "Content-Type": "application/json" };



        if (token) headers["X-Session-Token"] = token;



        



        showToast(`Syncing ${staticRecords.length} records into SQLite database Safe Place...`, "info");



        const res = await fetch(apiUrl("/api/records/bulk"), {



            method: "POST",



            headers: headers,



            credentials: "include",



            body: JSON.stringify({ records: staticRecords })



        });



        if (res.ok) {



            const data = await res.json();



            showToast(`✅ Synced ${data.imported || staticRecords.length} records into SQLite Safe Place!`, "success");



            localStorage.removeItem(STORAGE_KEY);



            localStorage.removeItem(FILES_STORAGE_KEY);



            saveToIndexedDB("records", []).catch(() => {});



            saveToIndexedDB("files", []).catch(() => {});



            staticRecords = [];



            await loadDailyProgress();



            await fetchRecords(1);



        }



    } catch (e) {



        console.warn("Could not sync offline records to server:", e);



    }



}







async function initApp() {







    refreshIcons();







    await initDataStore();







    await fetchSystemInfo();







    await loadDailyProgress();







    await fetchRecords(1);







}







function refreshIcons() {







    if (window.lucide && typeof window.lucide.createIcons === "function") {







        try {







            lucide.createIcons();







        } catch (e) {}







    } else {







        setTimeout(() => {







            if (window.lucide && typeof window.lucide.createIcons === "function") {







                try {







                    lucide.createIcons();







                } catch (e) {}







            }







        }, 300);







    }







}







// =========================================================================







// API & DATA LOADERS







// =========================================================================







async function fetchSystemInfo() {



    const isLiveCloud = window.location.protocol.startsWith("http") && 



                        !["localhost", "127.0.0.1"].includes(window.location.hostname) && 



                        !window.location.hostname.startsWith("192.168.") &&



                        !window.location.hostname.startsWith("10.");







    const labelEl = document.getElementById("lan-label-display");



    const displayEl = document.getElementById("lan-url-display");



    const shareBox = document.getElementById("lan-share-box");







    if (isLiveCloud) {



        lanShareUrl = window.location.origin;



        if (labelEl) labelEl.textContent = "Live Cloud:";



        if (displayEl) displayEl.textContent = window.location.host;



        if (shareBox) shareBox.classList.remove("hidden");



        return;



    }







    if (isStaticMode) {



        lanShareUrl = window.location.href;



        if (labelEl) labelEl.textContent = "Mode:";



        if (displayEl) {



            displayEl.textContent = window.location.hostname.includes("github.io") ? "GitHub Pages" : "Client-Side";



        }



        if (shareBox) shareBox.classList.remove("hidden");



        return;



    }







    try {



        const res = await fetch(apiUrl("/api/info"));



        const data = await res.json();



        if (data && data.office_share_url) {



            lanShareUrl = data.office_share_url;



            if (labelEl) labelEl.textContent = "Office LAN:";



            if (displayEl) displayEl.textContent = data.office_share_url.replace("http://", "");
            const modalUrlEl = document.getElementById("lan-modal-url");
            if (modalUrlEl) modalUrlEl.textContent = data.office_share_url;
            const modalOpenLink = document.getElementById("lan-modal-open-link");
            if (modalOpenLink) modalOpenLink.href = data.office_share_url;



            if (shareBox) shareBox.classList.remove("hidden");



        }



    } catch (err) {



        isStaticMode = true;



    }



}







async function loadDailyProgress() {







    if (isStaticMode) {







        let records = staticRecords.slice();







        if (currentServiceTab && currentServiceTab !== "all") {







            records = records.filter(r => (r.service_type || "").toLowerCase() === currentServiceTab.toLowerCase());







        }







        if (currentDateFilter) {







            records = records.filter(r => (r.record_date || "").startsWith(currentDateFilter));







        }







        const total = records.length;







        let completed = 0;







        let inProcess = 0;







        let rejected = 0;







        let baki = 0;







        let fee = 0.0;







        records.forEach(r => {







            const st = (r.status || "").toLowerCase();







            if (st.includes("reject") || st.includes("cancel") || st.includes("fail")) rejected++;







            else if (st.includes("complete") || st.includes("done") || st.includes("ok")) completed++;







            else if (st) inProcess++;







            if (r.is_baki === 1 || (r.remark || "").toUpperCase().includes("BAKI")) baki++;







            fee += Number(r.fee_amt || 0);







        });







        const completionRate = total > 0 ? Math.round((completed / total) * 1000) / 10 : 0.0;







        const rejectionRate = total > 0 ? Math.round((rejected / total) * 1000) / 10 : 0.0;







        document.getElementById("stat-progress-total").textContent = total.toLocaleString();







        document.getElementById("stat-progress-completed").textContent = completed.toLocaleString();







        document.getElementById("stat-progress-inprocess").textContent = inProcess.toLocaleString();







        const statRejEl = document.getElementById("stat-progress-rejected");







        if (statRejEl) statRejEl.textContent = rejected.toLocaleString();







        const statRejRateEl = document.getElementById("stat-progress-reject-rate");







        if (statRejRateEl) statRejRateEl.textContent = `${rejectionRate}%`;







        document.getElementById("stat-progress-baki").textContent = baki.toLocaleString();







        document.getElementById("stat-progress-fees").textContent = fee.toLocaleString();







        document.getElementById("stat-progress-rate").textContent = `${completionRate}%`;







        document.getElementById("stat-progress-date-pill").textContent = currentDateFilter ? formatDateDisplay(currentDateFilter) : "All";







        // Tab Badges







        const breakdown = {







            ucaadhar: 0,







            aadhar_online: 0,







            pancard: 0,







            aayushman: 0







        };







        staticRecords.forEach(r => {







            const s = (r.service_type || "").toLowerCase();







            if (breakdown[s] !== undefined) breakdown[s]++;







        });







        ['ucaadhar', 'aadhar_online', 'pancard', 'aayushman'].forEach(svc => {







            const badgeEl = document.getElementById(`tab-badge-${svc}`);







            if (badgeEl) badgeEl.textContent = breakdown[svc] || 0;







        });







        const badgeAllEl = document.getElementById("tab-badge-all");







        if (badgeAllEl) badgeAllEl.textContent = staticRecords.length;







        // Populate Date Selector







        const dateSet = new Set();







        staticRecords.forEach(r => {







            if (r.record_date && r.record_date.length >= 10) dateSet.add(r.record_date.substring(0, 10));







        });







        populateDateSelector(Array.from(dateSet).sort().reverse());







        return;







    }







    try {







        const queryStr = new URLSearchParams();







        if (currentDateFilter) queryStr.append("date", currentDateFilter);







        if (currentServiceTab && currentServiceTab !== "all") queryStr.append("service_type", currentServiceTab);







        const res = await fetch(apiUrl(`/api/progress?${queryStr.toString()}`));







        const data = await res.json();







        // Update Stat Cards







        document.getElementById("stat-progress-total").textContent = (data.total_applications || 0).toLocaleString();







        document.getElementById("stat-progress-completed").textContent = (data.completed || 0).toLocaleString();







        document.getElementById("stat-progress-inprocess").textContent = (data.in_process || 0).toLocaleString();







        const statRejEl = document.getElementById("stat-progress-rejected");







        if (statRejEl) statRejEl.textContent = (data.rejected || 0).toLocaleString();







        const statRejRateEl = document.getElementById("stat-progress-reject-rate");







        if (statRejRateEl) statRejRateEl.textContent = `${data.rejection_rate || 0}%`;







        document.getElementById("stat-progress-baki").textContent = (data.baki_pending || 0).toLocaleString();







        document.getElementById("stat-progress-fees").textContent = (data.total_fee || 0).toLocaleString();







        document.getElementById("stat-progress-rate").textContent = `${data.completion_rate || 0}%`;







        document.getElementById("stat-progress-date-pill").textContent = currentDateFilter ? formatDateDisplay(currentDateFilter) : "All";







        // Update Service Tab Badges







        const breakdown = data.service_breakdown || {};







        let totalCountAll = 0;







        ['ucaadhar', 'aadhar_online', 'pancard', 'aayushman'].forEach(svc => {







            const count = breakdown[svc] ? breakdown[svc].total : 0;







            totalCountAll += count;







            const badgeEl = document.getElementById(`tab-badge-${svc}`);







            if (badgeEl) badgeEl.textContent = count;







        });







        const badgeAllEl = document.getElementById("tab-badge-all");







        if (badgeAllEl) badgeAllEl.textContent = totalCountAll;







        // Populate Date Selector dropdown if not already populated







        populateDateSelector(data.available_dates || []);







    } catch (err) {







        console.error("Error loading daily progress", err);







    }







}







function populateDateSelector(availableDates) {







    const select = document.getElementById("quick-date-selector");







    if (!select) return;







    const currentVal = currentDateFilter || select.value;







    select.innerHTML = '<option value="">All Dates (Overview)</option>';







    availableDates.forEach(d => {







        const opt = document.createElement("option");







        opt.value = d;







        opt.textContent = `📅 ${formatDateDisplay(d)}`;







        select.appendChild(opt);







    });







    if (currentVal && availableDates.includes(currentVal)) {







        select.value = currentVal;







    } else {







        select.value = "";







    }







    const showcaseInput = document.getElementById("showcase-date-input");







    if (showcaseInput && currentVal) {







        showcaseInput.value = currentVal;







    }







}







function getSearchParams() {







    const searchDateEl = document.getElementById("search-date");







    const activeDate = currentDateFilter || (searchDateEl ? searchDateEl.value.trim() : "");







    return {







        service_type: currentServiceTab,







        name: document.getElementById("search-name").value.trim(),







        mobile: document.getElementById("search-mobile").value.trim(),







        id_number: document.getElementById("search-id").value.trim(),







        date: activeDate,







        status: currentStatusFilter !== "all" ? currentStatusFilter : (document.getElementById("filter-status").value !== "all" ? document.getElementById("filter-status").value : null),







        baki_only: isBakiOnly,







        page: currentPage,







        page_size: pageSize







    };







}







async function fetchRecords(page = 1) {







    currentPage = page;







    const params = getSearchParams();







    params.page = page;







    const spinner = document.getElementById("table-loading-spinner");







    if (spinner) spinner.classList.remove("hidden");







    if (isStaticMode) {







        let filtered = staticRecords.slice();







        if (params.service_type && params.service_type !== "all") {







            filtered = filtered.filter(r => (r.service_type || "").toLowerCase() === params.service_type.toLowerCase());







        }







        if (params.date) {







            const isoD = normalizeDateToIso(params.date);







            filtered = filtered.filter(r => {







                const rd = r.record_date || "";







                return rd.startsWith(params.date) || (isoD && rd.startsWith(isoD)) || formatDateDisplay(rd).includes(params.date);







            });







        }







        if (params.name) {







            const q = params.name.toLowerCase();







            filtered = filtered.filter(r => (r.name || "").toLowerCase().includes(q) || (r.record_date || "").includes(q) || formatDateDisplay(r.record_date).toLowerCase().includes(q));







        }







        if (params.mobile) {







            const mobClean = params.mobile.replace(/\D/g, "");







            filtered = filtered.filter(r => (r.mobile || "").includes(params.mobile) || (r.normalized_mobile || "").includes(mobClean));







        }







        if (params.id_number) {







            const q = params.id_number.toLowerCase();







            filtered = filtered.filter(r => (r.id_number || "").toLowerCase().includes(q) || (r.record_date || "").includes(q) || formatDateDisplay(r.record_date).toLowerCase().includes(q));







        }







        if (params.status && params.status !== "all") {







            filtered = filtered.filter(r => (r.status || "").toLowerCase() === params.status.toLowerCase());







        }







        if (params.baki_only) {







            filtered = filtered.filter(r => r.is_baki === 1 || (r.remark || "").toUpperCase().includes("BAKI"));







        }







        // Cross-date matching feedback hint







        const hintCross = document.getElementById("cross-date-match-hint");







        if (filtered.length === 0 && params.date && (params.name || params.mobile || params.id_number)) {







            const globalMatches = staticRecords.filter(r => {







                let ok = true;







                if (params.service_type && params.service_type !== "all") {







                    ok = ok && (r.service_type || "").toLowerCase() === params.service_type.toLowerCase();







                }







                if (params.name) {







                    const q = params.name.toLowerCase();







                    ok = ok && ((r.name || "").toLowerCase().includes(q) || (r.record_date || "").includes(q) || formatDateDisplay(r.record_date).toLowerCase().includes(q));







                }







                if (params.mobile) {







                    const mobClean = params.mobile.replace(/\D/g, "");







                    ok = ok && ((r.mobile || "").includes(params.mobile) || (r.normalized_mobile || "").includes(mobClean));







                }







                if (params.id_number) {







                    const q = params.id_number.toLowerCase();







                    ok = ok && ((r.id_number || "").toLowerCase().includes(q) || (r.record_date || "").includes(q) || formatDateDisplay(r.record_date).toLowerCase().includes(q));







                }







                return ok;







            });







            if (globalMatches.length > 0 && hintCross) {







                hintCross.innerHTML = `<span class="bg-amber-100 text-amber-900 px-2 py-0.5 rounded text-[11px] font-semibold ml-2">⚠️ Found ${globalMatches.length} matching record(s) on other dates. <button onclick="resetDateFilter()" class="underline font-bold text-brand-700 ml-1">Search All Dates</button></span>`;







            } else if (hintCross) {







                hintCross.innerHTML = "";







            }







        } else if (hintCross) {







            hintCross.innerHTML = "";







        }







        totalRecords = filtered.length;







        totalPages = Math.max(1, Math.ceil(totalRecords / params.page_size));







        const start = (params.page - 1) * params.page_size;







        currentRecords = filtered.slice(start, start + params.page_size);







        renderTableHeaders(currentServiceTab);







        renderRecordsTable(currentRecords, currentServiceTab);







        updatePaginationUI({







            page: params.page,







            page_size: params.page_size,







            total_count: totalRecords,







            total_pages: totalPages







        });







        document.getElementById("badge-total-records").textContent = `${totalRecords.toLocaleString()} records`;







        const activeTitle = SERVICE_META[currentServiceTab] ? SERVICE_META[currentServiceTab].label : "All Services";







        document.getElementById("active-service-title").textContent = `${activeTitle} Records`;







        // Update empty state button







        const emptyBtn = document.getElementById("empty-state-btn");







        if (params.date && (params.name || params.mobile || params.id_number) && filtered.length === 0) {







            document.getElementById("empty-state-desc").textContent = `No records matching search on date ${formatDateDisplay(params.date)}. Try searching across all dates.`;







            if (emptyBtn) {







                emptyBtn.textContent = "Search Across All Dates";







                emptyBtn.setAttribute("onclick", "resetDateFilter()");







            }







        } else {







            document.getElementById("empty-state-desc").textContent = 'Try clearing search terms or selecting "All Dates".';







            if (emptyBtn) {







                emptyBtn.textContent = "Reset Filters";







                emptyBtn.setAttribute("onclick", "resetAllFilters()");







            }







        }







        if (spinner) spinner.classList.add("hidden");







        return;







    }







    const queryStr = new URLSearchParams();







    if (params.service_type) queryStr.append("service_type", params.service_type);







    if (params.name) queryStr.append("name", params.name);







    if (params.mobile) queryStr.append("mobile", params.mobile);







    if (params.id_number) queryStr.append("id_number", params.id_number);







    if (params.date) queryStr.append("date", params.date);







    if (params.status && params.status !== "all") queryStr.append("status", params.status);







    if (params.baki_only) queryStr.append("baki_only", "true");







    queryStr.append("page", params.page);







    queryStr.append("page_size", params.page_size);







    // spinner already declared above







    if (spinner) spinner.classList.remove("hidden");







    try {







        const res = await fetch(apiUrl(`/api/records?${queryStr.toString()}`));







        const data = await res.json();







        currentRecords = data.items || [];







        totalRecords = data.total_count || 0;







        totalPages = data.total_pages || 1;







        renderTableHeaders(currentServiceTab);







        renderRecordsTable(currentRecords, currentServiceTab);







        updatePaginationUI(data);







        document.getElementById("badge-total-records").textContent = `${totalRecords.toLocaleString()} records`;







        const activeTitle = SERVICE_META[currentServiceTab] ? SERVICE_META[currentServiceTab].label : "All Services";







        document.getElementById("active-service-title").textContent = `${activeTitle} Records`;







    } catch (err) {







        console.error("Error fetching records", err);







        showToast("Error loading records from database", "error");







    } finally {







        spinner.classList.add("hidden");







    }







}







// =========================================================================







// TABLE RENDERERS (FIELD-DIVIDED COLUMNS)







// =========================================================================







function renderTableHeaders(serviceType) {







    const thead = document.getElementById("records-table-head");







    let trHtml = "";







    if (serviceType === "ucaadhar") {







        trHtml = `







            <tr>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 w-10 text-center whitespace-nowrap">#</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Date</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Name</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">SID Number</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Mobile No</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center whitespace-nowrap">Status</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-right whitespace-nowrap">Total (₹)</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-right whitespace-nowrap">Fee (₹)</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Remarks</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center w-28 whitespace-nowrap">Actions</th>







            </tr>







        `;







    } else if (serviceType === "aadhar_online") {







        trHtml = `







            <tr>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 w-10 text-center whitespace-nowrap">#</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Date</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Name</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">SRN Number</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Mobile No</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center whitespace-nowrap">Status</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Remarks</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center w-28 whitespace-nowrap">Actions</th>







            </tr>







        `;







    } else if (serviceType === "pancard") {







        // PAN Card does NOT need status







        trHtml = `







            <tr>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 w-10 text-center whitespace-nowrap">#</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Date</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Name</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Mobile Number</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">PAN Change / New</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-right whitespace-nowrap">Fee (₹)</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Remarks</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center w-28 whitespace-nowrap">Actions</th>







            </tr>







        `;







    } else if (serviceType === "aayushman") {







        // Ayushman Card does NOT need status







        trHtml = `







            <tr>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 w-10 text-center whitespace-nowrap">#</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Date</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Name</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Ration / Ayushman No</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Mobile No</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Remarks</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center w-28 whitespace-nowrap">Actions</th>







            </tr>







        `;







    } else {







        // All Services: Starts with Sr No, Date, Name, Service, ID Number, Mobile No...







        trHtml = `







            <tr>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 w-10 text-center whitespace-nowrap">#</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Date</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Name</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Service</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">ID / Number</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Mobile No</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center whitespace-nowrap">Status</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-right whitespace-nowrap">Fee (₹)</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 whitespace-nowrap">Remarks</th>







                <th class="py-2.5 sm:py-3 px-2.5 sm:px-3 text-center w-28 whitespace-nowrap">Actions</th>







            </tr>







        `;







    }







    thead.innerHTML = trHtml;







}









// =========================================================================

// RESPONSIVE VIEW MODE CONTROLLERS (CARDS VS TABLE)

// =========================================================================

let currentViewMode = localStorage.getItem("khodal_preferred_view") || (window.innerWidth < 768 ? "cards" : "table");



function setViewMode(mode) {

    currentViewMode = mode;

    localStorage.setItem("khodal_preferred_view", mode);

    updateViewModeUI();

    refreshIcons();

}



function updateViewModeUI() {

    const btnCards = document.getElementById("btn-view-cards");

    const btnTable = document.getElementById("btn-view-table");

    const tableWrapper = document.getElementById("records-table-wrapper");

    const cardsView = document.getElementById("records-cards-view");

    const emptyState = document.getElementById("table-empty-state");



    const isEmpty = emptyState && !emptyState.classList.contains("hidden");



    if (currentViewMode === "cards") {

        if (btnCards) {

            btnCards.className = "px-2.5 py-1 text-xs font-semibold rounded-md transition flex items-center gap-1 cursor-pointer bg-white text-brand-700 shadow-2xs";

        }

        if (btnTable) {

            btnTable.className = "px-2.5 py-1 text-xs font-semibold rounded-md transition flex items-center gap-1 cursor-pointer text-slate-600 hover:text-slate-900";

        }

        if (tableWrapper) tableWrapper.classList.add("hidden");

        if (cardsView) {

            if (isEmpty) {

                cardsView.classList.add("hidden");

            } else {

                cardsView.classList.remove("hidden");

            }

        }

    } else {

        if (btnCards) {

            btnCards.className = "px-2.5 py-1 text-xs font-semibold rounded-md transition flex items-center gap-1 cursor-pointer text-slate-600 hover:text-slate-900";

        }

        if (btnTable) {

            btnTable.className = "px-2.5 py-1 text-xs font-semibold rounded-md transition flex items-center gap-1 cursor-pointer bg-white text-brand-700 shadow-2xs";

        }

        if (cardsView) cardsView.classList.add("hidden");

        if (tableWrapper) {

            if (isEmpty) {

                tableWrapper.classList.add("hidden");

            } else {

                tableWrapper.classList.remove("hidden");

            }

        }

    }

}



// 1-Click Clipboard Copy with Mobile Support

function copyToClipboard(text, label = "Text") {

    if (!text) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {

        navigator.clipboard.writeText(text).then(() => {

            showToast(`${label} copied to clipboard!`, "success");

        }).catch(() => {

            legacyCopyToClipboard(text, label);

        });

    } else {

        legacyCopyToClipboard(text, label);

    }

}



function legacyCopyToClipboard(text, label) {

    const ta = document.createElement("textarea");

    ta.value = text;

    ta.style.position = "fixed";

    ta.style.opacity = "0";

    ta.style.pointerEvents = "none";

    document.body.appendChild(ta);

    ta.select();

    try {

        document.execCommand("copy");

        showToast(`${label} copied to clipboard!`, "success");

    } catch (e) {

        showToast("Could not copy text", "error");

    }

    document.body.removeChild(ta);

}



// Render Mobile Card View

function renderRecordsCards(records, serviceType) {

    const container = document.getElementById("records-cards-view");

    if (!container) return;

    container.innerHTML = "";



    const nameQuery = document.getElementById("search-name") ? document.getElementById("search-name").value.trim() : "";

    const mobileQuery = document.getElementById("search-mobile") ? document.getElementById("search-mobile").value.trim() : "";

    const idQuery = document.getElementById("search-id") ? document.getElementById("search-id").value.trim() : "";



    records.forEach((r, idx) => {

        const globalIdx = (currentPage - 1) * pageSize + idx + 1;

        const hlName = highlightText(r.name || "-", nameQuery);

        const hlMobile = highlightText(r.mobile || "-", mobileQuery);

        const hlId = highlightText(r.id_number || "-", idQuery);

        const waUrl = getWhatsAppUrl(r.mobile, r.name);

        const callUrl = r.mobile ? `tel:${r.mobile}` : "#";

        const statusBadge = renderStatusBadge(r);

        const svcBadge = renderServiceBadge(r.service_type);



        let idLabel = "ID Number";

        const svc = (r.service_type || serviceType || "").toLowerCase();

        if (svc === "ucaadhar") idLabel = "SID Number";

        else if (svc === "aadhar_online") idLabel = "SRN Number";

        else if (svc === "pancard") idLabel = "PAN / Ack No";

        else if (svc === "aayushman") idLabel = "Ration / Card";



        const card = document.createElement("div");

        card.className = "record-card group";



        const hasFee = (r.fee_amt > 0 || r.total_amt > 0);

        const feeDisplay = r.fee_amt > 0 ? `₹${r.fee_amt}` : (r.total_amt > 0 ? `₹${r.total_amt}` : "-");



        card.innerHTML = `

            <div>

                <!-- Top Header: Index, Service Badge, Date -->

                <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 text-xs">

                    <div class="flex items-center gap-1.5 flex-wrap">

                        <span class="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">#${globalIdx}</span>

                        ${svcBadge}

                    </div>

                    <span class="font-mono text-xs font-medium text-slate-500 shrink-0">${escapeHtml(formatDateDisplay(r.record_date))}</span>

                </div>



                <!-- Main Content: Customer Name, Status Badge, ID -->

                <div class="pt-2.5 pb-1">

                    <div class="flex items-start justify-between gap-2">

                        <h4 class="font-bold text-slate-900 text-sm hover:text-brand-600 transition cursor-pointer break-words leading-tight" onclick="viewRecordDetails(${r.id})">

                            ${hlName}

                        </h4>

                        <div class="shrink-0 text-right">

                            ${statusBadge}

                        </div>

                    </div>



                    ${r.id_number ? `

                    <div class="flex items-center justify-between mt-2 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-150 text-xs">

                        <span class="text-[11px] font-medium text-slate-500">${escapeHtml(idLabel)}:</span>

                        <div class="flex items-center gap-1.5">

                            <span class="font-mono font-bold text-brand-700 select-all">${hlId}</span>

                            <button type="button" onclick="copyToClipboard('${escapeHtml(r.id_number)}', '${escapeHtml(idLabel)}')" title="Copy ID" class="text-slate-400 hover:text-brand-600 p-0.5 rounded cursor-pointer transition">

                                <i data-lucide="copy" class="w-3.5 h-3.5"></i>

                            </button>

                        </div>

                    </div>` : ''}



                    ${r.pan_type ? `

                    <div class="mt-1.5 text-xs font-bold ${(r.pan_type || '').includes('NEW') ? 'text-blue-700' : 'text-amber-700'}">

                        Type: ${escapeHtml(r.pan_type)}

                    </div>` : ''}

                </div>



                <!-- Contact & Communication Bar -->

                <div class="py-2 flex items-center justify-between gap-2 border-t border-slate-100 mt-2">

                    <div class="flex items-center gap-1.5 text-xs font-mono font-semibold text-slate-700">

                        <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400"></i>

                        <span>${r.mobile ? hlMobile : '<span class="text-slate-400 font-normal">No Mobile</span>'}</span>

                    </div>

                    ${r.mobile ? `

                    <div class="flex items-center gap-1.5 shrink-0">

                        ${waUrl ? `

                        <a href="${waUrl}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 active:bg-emerald-200 text-emerald-700 border border-emerald-200 text-xs font-semibold transition" title="Send WhatsApp Message">

                            <i data-lucide="message-circle" class="w-3.5 h-3.5 text-emerald-600"></i>

                            <span>Chat</span>

                        </a>` : ''}

                        <a href="${callUrl}" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 text-indigo-700 border border-indigo-200 text-xs font-semibold transition" title="Call Customer">

                            <i data-lucide="phone-call" class="w-3.5 h-3.5 text-indigo-600"></i>

                            <span>Call</span>

                        </a>

                    </div>` : ''}

                </div>



                <!-- Financial & Remarks -->

                <div class="pt-2 pb-1 text-xs flex flex-wrap items-center justify-between gap-2 border-t border-slate-100">

                    <div>

                        ${hasFee ? `

                        <span class="text-slate-500 font-medium">Fee: </span>

                        <span class="font-mono font-bold text-emerald-700">${feeDisplay}</span>

                        ` : '<span class="text-slate-400 text-[11px]">Fee: -</span>'}

                    </div>

                    ${r.remark ? `

                    <div class="text-right text-[11px] max-w-[190px] truncate" title="${escapeHtml(r.remark)}">

                        ${renderRemarkWithBaki(r.remark)}

                    </div>` : ''}

                </div>

            </div>



            <!-- Bottom Actions -->

            <div class="pt-2 border-t border-slate-100 flex items-center justify-between gap-1.5 text-xs mt-2">

                <button type="button" onclick="viewRecordDetails(${r.id})" class="flex-1 py-1.5 px-2 bg-slate-50 hover:bg-brand-50 hover:text-brand-700 text-slate-700 rounded-lg font-semibold flex items-center justify-center gap-1 border border-slate-200 transition cursor-pointer min-h-[36px]">

                    <i data-lucide="eye" class="w-3.5 h-3.5 text-brand-600"></i>

                    <span>Details</span>

                </button>

                <button type="button" onclick="openEditRecordModal(${r.id})" class="flex-1 py-1.5 px-2 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded-lg font-semibold flex items-center justify-center gap-1 border border-slate-200 transition cursor-pointer min-h-[36px]">

                    <i data-lucide="edit-2" class="w-3.5 h-3.5 text-slate-600"></i>

                    <span>Edit</span>

                </button>

                <button type="button" onclick="deleteRecordAction(${r.id})" class="py-1.5 px-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg font-semibold flex items-center justify-center border border-rose-200 transition cursor-pointer min-h-[36px]" title="Delete Record">

                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>

                </button>

            </div>

        `;



        container.appendChild(card);

    });

}



function renderRecordsTable(records, serviceType) {

    const tbody = document.getElementById("records-table-body");

    const emptyState = document.getElementById("table-empty-state");

    const cardsContainer = document.getElementById("records-cards-view");

    const tableWrapper = document.getElementById("records-table-wrapper");



    tbody.innerHTML = "";

    if (cardsContainer) cardsContainer.innerHTML = "";



    if (!records || records.length === 0) {

        if (emptyState) emptyState.classList.remove("hidden");

        if (tableWrapper) tableWrapper.classList.add("hidden");

        if (cardsContainer) cardsContainer.classList.add("hidden");







        emptyState.classList.remove("hidden");







        const emptyTitle = document.getElementById("empty-state-title");







        const emptyDesc = document.getElementById("empty-state-desc");







        const emptyBtn = document.getElementById("empty-state-btn");







        if (totalRecords === 0) {







            if (emptyTitle) emptyTitle.textContent = "No Office Records Loaded Yet";







            if (emptyDesc) emptyDesc.textContent = "Upload your Excel (.xlsx, .xls) or CSV file to start viewing and searching records.";







            if (emptyBtn) {







                emptyBtn.innerHTML = '<i data-lucide="upload-cloud" class="w-4 h-4 inline mr-1"></i> Upload Office File';







                emptyBtn.onclick = openUploadModal;







            }







        } else {







            if (emptyTitle) emptyTitle.textContent = "No Records Found";







            if (emptyDesc) emptyDesc.textContent = "Try clearing search terms or selecting 'All Dates'.";







            if (emptyBtn) {







                emptyBtn.innerHTML = 'Reset Filters';







                emptyBtn.onclick = resetAllFilters;







            }







        }







        refreshIcons();







        return;







    }







    emptyState.classList.add("hidden");







    const nameQuery = document.getElementById("search-name").value.trim();







    const mobileQuery = document.getElementById("search-mobile").value.trim();







    const idQuery = document.getElementById("search-id").value.trim();







    records.forEach((r, idx) => {







        const globalIdx = (currentPage - 1) * pageSize + idx + 1;







        const tr = document.createElement("tr");







        tr.className = "hover:bg-slate-50/80 transition-colors border-b border-slate-100 group";







        const hlName = highlightText(r.name || "-", nameQuery);







        const hlMobile = highlightText(r.mobile || "-", mobileQuery);







        const hlId = highlightText(r.id_number || "-", idQuery);







        const waUrl = getWhatsAppUrl(r.mobile, r.name);







        const callUrl = r.mobile ? `tel:${r.mobile}` : "#";







        // Status Badge & Quick Toggle (Aadhaar 3-way, PAN/Ayushman blank)







        const statusBadge = renderStatusBadge(r);







        // Service Badge for All Services tab







        const svcBadge = renderServiceBadge(r.service_type);







        let rowHtml = "";







        if (serviceType === "ucaadhar") {







            // UC Aadhaar: Sr No -> Date -> Name -> SID Number -> Mobile No -> Status -> Total -> Fee -> Remarks -> Actions







            rowHtml = `







                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>







                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(formatDateDisplay(r.record_date))}</td>







                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[190px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>







                <td class="py-3 px-3 font-mono text-xs font-semibold text-brand-700 max-w-[200px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>







                <td class="py-3 px-3">







                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">







                        ${r.mobile ? `<span>${hlMobile}</span>` : `<span class="text-slate-400 font-normal">-</span>`}







                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}







                    </div>







                </td>







                <td class="py-3 px-3 text-center">${statusBadge}</td>







                <td class="py-3 px-3 text-xs text-right font-mono text-slate-600">${r.total_amt > 0 ? '₹' + r.total_amt : '-'}</td>







                <td class="py-3 px-3 text-xs text-right font-mono font-bold text-emerald-700">${r.fee_amt > 0 ? '₹' + r.fee_amt : '-'}</td>







                <td class="py-3 px-3 text-xs text-slate-600 max-w-[160px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>







                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>







            `;







        } else if (serviceType === "aadhar_online") {







            // Aadhaar Online: Sr No -> Date -> Name -> SRN Number -> Mobile No -> Status -> Remarks -> Actions







            rowHtml = `







                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>







                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(formatDateDisplay(r.record_date))}</td>







                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>







                <td class="py-3 px-3 font-mono text-xs font-bold text-indigo-700 max-w-[170px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>







                <td class="py-3 px-3">







                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">







                        <span>${hlMobile}</span>







                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}







                    </div>







                </td>







                <td class="py-3 px-3 text-center">${statusBadge}</td>







                <td class="py-3 px-3 text-xs text-slate-700 max-w-[180px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>







                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>







            `;







        } else if (serviceType === "pancard") {







            // PAN Card: Sr No -> Date -> Name -> Mobile Number -> PAN Change/New -> Fee -> Remarks -> Actions (NO STATUS)







            rowHtml = `







                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>







                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(formatDateDisplay(r.record_date))}</td>







                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>







                <td class="py-3 px-3">







                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">







                        <span>${hlMobile}</span>







                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}







                    </div>







                </td>







                <td class="py-3 px-3 text-xs font-bold ${(r.pan_type || '').includes('NEW') ? 'text-blue-700' : 'text-amber-700'}">${escapeHtml(r.pan_type || '-')}</td>







                <td class="py-3 px-3 text-xs text-right font-mono font-bold text-emerald-700">${r.fee_amt > 0 ? '₹' + r.fee_amt : '-'}</td>







                <td class="py-3 px-3 text-xs text-slate-600">${renderRemarkWithBaki(r.remark)}</td>







                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>







            `;







        } else if (serviceType === "aayushman") {







            // Ayushman Card: Sr No -> Date -> Name -> Ration/Ayushman No -> Mobile No -> Remarks -> Actions (NO STATUS)







            rowHtml = `







                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>







                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(formatDateDisplay(r.record_date))}</td>







                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>







                <td class="py-3 px-3 font-mono text-xs font-bold text-purple-700 max-w-[170px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>







                <td class="py-3 px-3">







                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">







                        <span>${hlMobile}</span>







                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}







                    </div>







                </td>







                <td class="py-3 px-3 text-xs text-slate-600 max-w-[180px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>







                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>







            `;







        } else {







            // All Services: Sr No -> Date -> Name -> Service -> ID Number -> Mobile No -> Status -> Fee -> Remarks -> Actions







            rowHtml = `







                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>







                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(formatDateDisplay(r.record_date))}</td>







                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[180px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>







                <td class="py-3 px-3">${svcBadge}</td>







                <td class="py-3 px-3 font-mono text-xs font-semibold text-slate-700 max-w-[150px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>







                <td class="py-3 px-3">







                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">







                        ${r.mobile ? `<span>${hlMobile}</span>` : `<span class="text-slate-400">-</span>`}







                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}







                    </div>







                </td>







                <td class="py-3 px-3 text-center">${statusBadge}</td>







                <td class="py-3 px-3 text-xs text-right font-mono font-bold text-emerald-700">${r.fee_amt > 0 ? '₹' + r.fee_amt : '-'}</td>







                <td class="py-3 px-3 text-xs text-slate-600 max-w-[150px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>







                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>







            `;







        }







        tr.innerHTML = rowHtml;







        tbody.appendChild(tr);

    });



    // Populate mobile cards view

    renderRecordsCards(records, serviceType);



    updateViewModeUI();

    refreshIcons();

}



function renderStatusBadge(r) {







    const svc = (r.service_type || "").toLowerCase();







    // In PAN Card and Ayushman Card, status is NOT needed







    if (svc === "pancard" || svc === "aayushman") {







        return `<span class="text-slate-400 font-normal">-</span>`;







    }







    const stRaw = (r.status || "").toLowerCase();







    let normalized = "InProgress";







    let nextStatus = "Rejected";







    if (stRaw.includes("reject") || stRaw.includes("cancel") || stRaw.includes("fail")) {







        normalized = "Rejected";







        nextStatus = "Completed";







    } else if (stRaw.includes("complete") || stRaw.includes("done") || stRaw.includes("success") || stRaw.includes("ok")) {







        normalized = "Completed";







        nextStatus = "InProgress";







    } else {







        normalized = "InProgress";







        nextStatus = "Rejected";







    }







    if (normalized === "Completed") {







        return `<button onclick="toggleRecordStatus(${r.id}, '${nextStatus}')" title="Status: Completed (Click to change to InProgress)" class="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border border-emerald-300 transition shadow-2xs">







            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Completed







        </button>`;







    } else if (normalized === "InProgress") {







        return `<button onclick="toggleRecordStatus(${r.id}, '${nextStatus}')" title="Status: InProgress (Click to change to Rejected)" class="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 hover:bg-amber-200 border border-amber-300 transition shadow-2xs">







            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> InProgress







        </button>`;







    } else {







        return `<button onclick="toggleRecordStatus(${r.id}, '${nextStatus}')" title="Status: Rejected (Click to change to Completed)" class="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 hover:bg-rose-200 border border-rose-300 transition shadow-2xs">







            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Rejected







        </button>`;







    }







}







function renderServiceBadge(svc) {







    if (svc === "ucaadhar") {







        return `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">UC AADHAAR</span>`;







    } else if (svc === "aadhar_online") {







        return `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">AADHAAR ONL</span>`;







    } else if (svc === "pancard") {







        return `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">PAN CARD</span>`;







    } else if (svc === "aayushman") {







        return `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">AYUSHMAN</span>`;







    }







    return `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800">GENERAL</span>`;







}







function renderRemarkWithBaki(remark) {







    if (!remark) return "-";







    const lower = remark.toLowerCase();







    if (lower.includes("baki") || lower.includes("not reciv") || lower.includes("no reciv") || lower.includes("not resiv")) {







        return `<span class="font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">${escapeHtml(remark)}</span>`;







    }







    return escapeHtml(remark);







}







function renderActions(r, waUrl, callUrl) {







    return `







        <div class="flex items-center justify-center gap-1 opacity-90 group-hover:opacity-100">







            <button onclick="copyRecordCard(${r.id})" title="Copy Summary" class="p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer">







                <i data-lucide="copy" class="w-3.5 h-3.5"></i>







            </button>







            <button onclick="viewRecordDetails(${r.id})" title="View Details" class="p-1.5 rounded text-brand-600 hover:text-brand-800 hover:bg-brand-50 transition cursor-pointer">







                <i data-lucide="eye" class="w-3.5 h-3.5"></i>







            </button>







            <button onclick="openEditRecordModal(${r.id})" title="Edit" class="p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer">







                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>







            </button>







            <button onclick="deleteRecordAction(${r.id})" title="Delete" class="p-1.5 rounded text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition cursor-pointer">







                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>







            </button>







        </div>







    `;







}







function updatePaginationUI(data) {







    const startIdx = totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1;







    const endIdx = Math.min(currentPage * pageSize, totalRecords);







    document.getElementById("page-start-idx").textContent = startIdx;







    document.getElementById("page-end-idx").textContent = endIdx;







    document.getElementById("page-total-items").textContent = totalRecords.toLocaleString();







    document.getElementById("current-page-num").textContent = currentPage;







    document.getElementById("total-pages-num").textContent = totalPages;







    document.getElementById("btn-prev-page").disabled = currentPage <= 1;







    document.getElementById("btn-next-page").disabled = currentPage >= totalPages;







}







function goToPage(page) {







    if (page < 1 || page > totalPages) return;







    fetchRecords(page);







}







function changePageSize(newSize) {







    pageSize = parseInt(newSize, 10) || 25;







    fetchRecords(1);







}







// =========================================================================







// TAB SWITCHING & FILTERS







// =========================================================================







function switchServiceTab(tab) {







    currentServiceTab = tab;







    // Update active tab buttons







    document.querySelectorAll(".service-tab-btn").forEach(btn => {







        btn.classList.remove("bg-brand-600", "text-white", "shadow-2xs", "active");







        btn.classList.add("text-slate-600", "hover:bg-slate-100");







    });







    const activeBtn = document.getElementById(`tab-${tab}`);







    if (activeBtn) {







        activeBtn.classList.remove("text-slate-600", "hover:bg-slate-100");







        activeBtn.classList.add("bg-brand-600", "text-white", "shadow-2xs", "active");







    }







    loadDailyProgress();







    fetchRecords(1);







}







function getAvailableDates() {







    if (isStaticMode) {







        const set = new Set();







        staticRecords.forEach(r => {







            if (r.record_date && r.record_date.length >= 10) set.add(r.record_date.substring(0, 10));







        });







        return Array.from(set).sort().reverse();







    }







    const select = document.getElementById("quick-date-selector");







    if (select) {







        return Array.from(select.options).map(o => o.value).filter(Boolean);







    }







    return [];







}







function getLatestRecordDate() {







    const dates = getAvailableDates();







    return dates.length > 0 ? dates[0] : "";







}







function applyDateFilter(val) {







    currentDateFilter = normalizeDateToIso(val) || "";







    const showcaseInput = document.getElementById("showcase-date-input");







    if (showcaseInput) showcaseInput.value = currentDateFilter;







    const selector = document.getElementById("quick-date-selector");







    if (selector) selector.value = currentDateFilter;







    const searchDateInput = document.getElementById("search-date");







    if (searchDateInput) {







        searchDateInput.value = currentDateFilter;







        toggleClearButton("search-date", "clear-search-date");







    }







    updateDateFilterHint();







    loadDailyProgress();







    fetchRecords(1);







}







function onCustomDateFilterChange(val) {







    applyDateFilter(val);







}







function onDateSelectorChange(val) {







    applyDateFilter(val);







}







function onSearchDateChange(val) {







    applyDateFilter(val);







}







function clearSearchDate() {







    applyDateFilter("");







}







function selectLatestDate() {







    const latest = getLatestRecordDate();







    if (!latest) {







        showToast("No record dates found in the data", "info");







        return;







    }







    applyDateFilter(latest);







    showToast(`Showing latest work date: ${formatDateDisplay(latest)}`, "success");







}







function setTodayDate() {







    const today = new Date().toISOString().split("T")[0];







    applyDateFilter(today);







    setTimeout(() => {







        if (totalRecords === 0) {







            showToast(`No records for today (${formatDateDisplay(today)}). Click 'Latest Date' to view uploaded data.`, "info");







        }







    }, 350);







}







function resetDateFilter() {







    applyDateFilter("");







    showToast("Showing all dates", "info");







}







function updateDateFilterHint() {







    const hintEl = document.getElementById("table-filter-hint");







    const displayEl = document.getElementById("active-date-display");







    if (!hintEl) return;







    if (currentDateFilter) {







        hintEl.classList.remove("hidden");







        if (displayEl) displayEl.textContent = formatDateDisplay(currentDateFilter);







    } else {







        hintEl.classList.add("hidden");







    }







}







function filterByStatusQuick(status) {







    currentStatusFilter = status;







    document.getElementById("filter-status").value = status.toLowerCase();







    fetchRecords(1);







    showToast(`Filtering by ${status}`, "info");







}







function toggleBakiFilter() {







    isBakiOnly = !isBakiOnly;







    const badge = document.getElementById("baki-active-badge");







    if (isBakiOnly) {







        badge.textContent = "FILTER ACTIVE";







        badge.classList.add("bg-rose-600", "text-white");







        showToast("Showing only Baki / Dues / Action Pending cases", "info");







    } else {







        badge.textContent = "pending";







        badge.classList.remove("bg-rose-600", "text-white");







    }







    fetchRecords(1);







}







function triggerSearchDebounced() {







    toggleClearButton("search-name", "clear-name");







    toggleClearButton("search-mobile", "clear-mobile");







    toggleClearButton("search-id", "clear-id");







    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);







    searchDebounceTimer = setTimeout(() => {







        fetchRecords(1);







    }, 280);







}







function toggleClearButton(inputId, clearBtnId) {







    const input = document.getElementById(inputId);







    const btn = document.getElementById(clearBtnId);







    if (!input || !btn) return;







    if (input.value.trim().length > 0) btn.classList.remove("hidden");







    else btn.classList.add("hidden");







}







function clearInput(inputId) {







    const input = document.getElementById(inputId);







    if (input) {







        input.value = "";







        triggerSearchDebounced();







        input.focus();







    }







}







function resetAllFilters() {







    document.getElementById("search-name").value = "";







    document.getElementById("search-mobile").value = "";







    document.getElementById("search-id").value = "";







    const searchDateEl = document.getElementById("search-date");







    if (searchDateEl) searchDateEl.value = "";







    







    document.getElementById("filter-status").value = "all";







    currentStatusFilter = "all";







    isBakiOnly = false;







    currentDateFilter = "";







    







    const showcaseInput = document.getElementById("showcase-date-input");







    if (showcaseInput) showcaseInput.value = "";







    const selector = document.getElementById("quick-date-selector");







    if (selector) selector.value = "";







    const badge = document.getElementById("baki-active-badge");







    if (badge) {







        badge.textContent = "pending";







        badge.classList.remove("bg-rose-600", "text-white");







    }







    toggleClearButton("search-name", "clear-name");







    toggleClearButton("search-mobile", "clear-mobile");







    toggleClearButton("search-id", "clear-id");







    toggleClearButton("search-date", "clear-search-date");







    updateDateFilterHint();







    const hintCross = document.getElementById("cross-date-match-hint");







    if (hintCross) hintCross.innerHTML = "";







    loadDailyProgress();







    fetchRecords(1);







    showToast("Filters reset to view all records", "info");







}







// =========================================================================







// STATUS TOGGLE & CRUD







// =========================================================================







async function toggleRecordStatus(recordId, newStatus) {







    if (isStaticMode) {







        const rec = staticRecords.find(r => r.id === recordId);







        if (rec) {







            rec.status = newStatus;







            saveStaticRecords(staticRecords);







            showToast(`Status updated to ${newStatus}`, "success");







            await loadDailyProgress();







            await fetchRecords(currentPage);







        }







        return;







    }







    try {







        const res = await fetch(apiUrl(`/api/records/${recordId}/status`), {







            method: "PATCH",







            headers: { "Content-Type": "application/json" },







            body: JSON.stringify({ status: newStatus })







        });







        if (!res.ok) throw new Error("Failed to update status");







        showToast(`Status updated to ${newStatus}`, "success");







        await loadDailyProgress();







        await fetchRecords(currentPage);







    } catch (err) {







        showToast(err.message, "error");







    }







}







function viewRecordDetails(recordId) {







    const record = currentRecords.find(r => r.id === recordId);







    if (!record) return;







    currentViewRecord = record;







    document.getElementById("view-record-id").textContent = record.id;







    document.getElementById("view-name").textContent = record.name || "Unnamed";







    document.getElementById("view-avatar").textContent = (record.name && record.name.length > 0) ? record.name.charAt(0).toUpperCase() : "K";







    document.getElementById("view-service-badge").textContent = (record.service_type || "general").toUpperCase();







    document.getElementById("view-date").textContent = formatDateDisplay(record.record_date);







    document.getElementById("view-id-num").textContent = record.id_number || "-";







    document.getElementById("view-mobile").textContent = record.mobile || "-";







    const statusRow = document.getElementById("view-row-status");







    const recSvc = (record.service_type || "").toLowerCase();







    if (recSvc === "pancard" || recSvc === "aayushman") {







        if (statusRow) statusRow.classList.add("hidden");







    } else {







        if (statusRow) statusRow.classList.remove("hidden");







        const viewStatusEl = document.getElementById("view-status");







        if (viewStatusEl) viewStatusEl.textContent = record.status || "Completed";







    }







    document.getElementById("view-remark").textContent = record.remark || "-";







    const feeEl = document.getElementById("view-fee");







    if (record.fee_amt > 0 || record.total_amt > 0) {







        feeEl.textContent = `₹${record.fee_amt || record.total_amt}`;







        document.getElementById("view-row-fee").classList.remove("hidden");







    } else {







        document.getElementById("view-row-fee").classList.add("hidden");







    }







    const waUrl = getWhatsAppUrl(record.mobile, record.name);







    const waBtn = document.getElementById("btn-view-whatsapp");







    if (waUrl) {







        waBtn.href = waUrl;







        waBtn.classList.remove("opacity-40", "pointer-events-none");







    } else {







        waBtn.href = "#";







        waBtn.classList.add("opacity-40", "pointer-events-none");







    }







    const callBtn = document.getElementById("btn-view-call");







    if (record.mobile) {







        callBtn.href = `tel:${record.mobile}`;







        callBtn.classList.remove("opacity-40", "pointer-events-none");







    } else {







        callBtn.href = "#";







        callBtn.classList.add("opacity-40", "pointer-events-none");







    }







    openModal("modal-view-record");







    refreshIcons();







}







function copyCurrentViewCard() {







    if (!currentViewRecord) return;







    copyRecordCard(currentViewRecord.id);







}







function copyRecordCard(recordId) {







    const r = currentRecords.find(item => item.id === recordId) || currentViewRecord;







    if (!r) return;







    let text = `📌 Khodal Office Update\n`;







    text += `🔹 Service: ${(r.service_type || 'Office').toUpperCase()}\n`;







    text += `📅 Date: ${formatDateDisplay(r.record_date)}\n`;







    text += `👤 Name: ${r.name || '-'}\n`;







    if (r.id_number) text += `🔢 Number (SID/SRN/Card): ${r.id_number}\n`;







    if (r.mobile) text += `📱 Mobile: ${r.mobile}\n`;







    if (r.pan_type) text += `💳 PAN: ${r.pan_type}\n`;







    if (r.fee_amt) text += `💰 Fee: ₹${r.fee_amt}\n`;







    if (r.status) text += `📊 Status: ${r.status}\n`;







    if (r.remark) text += `📝 Remarks: ${r.remark}\n`;







    navigator.clipboard.writeText(text).then(() => {







        showToast("Record card copied to clipboard!", "success");







    }).catch(() => {







        showToast("Failed to copy", "error");







    });







}







function updateFormIdLabel(svc) {







    const label = document.getElementById("form-id-label");







    const input = document.getElementById("form-id-number");







    const statusContainer = document.getElementById("form-status-container");







    const panInput = document.getElementById("form-pan-type");







    const panContainer = panInput ? panInput.closest("div") : null;







    if (!label || !input) return;







    if (svc === "ucaadhar") {







        label.textContent = "SID Number (UC Aadhaar) *";







        input.placeholder = "e.g. S148796318971020261001104627";







        if (statusContainer) statusContainer.classList.remove("hidden");







        if (panContainer) panContainer.classList.add("hidden");







    } else if (svc === "aadhar_online") {







        label.textContent = "SRN Number (Aadhaar Online) *";







        input.placeholder = "e.g. S1311143561680";







        if (statusContainer) statusContainer.classList.remove("hidden");







        if (panContainer) panContainer.classList.add("hidden");







    } else if (svc === "pancard") {







        label.textContent = "PAN / Acknowledgement No";







        input.placeholder = "e.g. ABCDE1234F / Ack No";







        if (statusContainer) statusContainer.classList.add("hidden");







        if (panContainer) panContainer.classList.remove("hidden");







    } else if (svc === "aayushman") {







        label.textContent = "Ration / Ayushman Card No";







        input.placeholder = "e.g. PAJYXBXFU... / 109904008663704";







        if (statusContainer) statusContainer.classList.add("hidden");







        if (panContainer) panContainer.classList.add("hidden");







    } else {







        label.textContent = "SID / SRN / Card No";







        input.placeholder = "e.g. S131114... / PAJY...";







        if (statusContainer) statusContainer.classList.remove("hidden");







        if (panContainer) panContainer.classList.remove("hidden");







    }







}







function handleFormIdInput(val) {







    const clean = (val || "").trim().toUpperCase();







    const svcSelect = document.getElementById("form-service-type");







    if (!svcSelect) return;







    // SID Number ALWAYS means UC Aadhaar







    // SRN Number ALWAYS means Aadhaar Online







    if (clean.startsWith("SID") || (clean.startsWith("S") && clean.length >= 18)) {







        if (svcSelect.value !== "ucaadhar") {







            svcSelect.value = "ucaadhar";







            updateFormIdLabel("ucaadhar");







        }







        // Auto-extract date from SID timestamp: S...YYYYMMDD...







        const mDate = clean.match(/S\d{10,14}(202[0-9])(0[1-9]|1[0-2])([0-3][0-9])/);







        if (mDate) {







            const sidDate = `${mDate[1]}-${mDate[2]}-${mDate[3]}`;







            const dateInput = document.getElementById("form-date");







            if (dateInput) {







                dateInput.value = sidDate;







            }







        }







    } else if (clean.startsWith("SRN") || (clean.startsWith("S") && clean.length >= 10 && clean.length <= 16)) {







        if (svcSelect.value !== "aadhar_online") {







            svcSelect.value = "aadhar_online";







            updateFormIdLabel("aadhar_online");







        }







    }







}







function openAddRecordModal() {







    document.getElementById("record-form-title").textContent = "New Office Entry";







    document.getElementById("form-record-id").value = "";







    document.getElementById("record-form").reset();







    







    // Default to active date filter, or latest date from records, or today







    const defaultDate = normalizeDateToIso(currentDateFilter) || getLatestRecordDate() || new Date().toISOString().split("T")[0];







    document.getElementById("form-date").value = defaultDate;







    







    const initialSvc = currentServiceTab !== "all" ? currentServiceTab : "ucaadhar";







    document.getElementById("form-service-type").value = initialSvc;







    updateFormIdLabel(initialSvc);







    openModal("modal-record-form");







}







function openEditRecordModal(recordId) {







    const r = currentRecords.find(item => item.id === recordId);







    if (!r) return;







    document.getElementById("record-form-title").textContent = "Edit Office Entry";







    document.getElementById("form-record-id").value = r.id;







    const recSvc = r.service_type || "ucaadhar";







    document.getElementById("form-service-type").value = recSvc;







    updateFormIdLabel(recSvc);







    document.getElementById("form-date").value = normalizeDateToIso(r.record_date) || "";







    document.getElementById("form-name").value = r.name || "";







    document.getElementById("form-mobile").value = r.mobile || "";







    document.getElementById("form-id-number").value = r.id_number || "";







    const stSelect = document.getElementById("form-status");







    if (stSelect) {







        if (["Completed", "InProgress", "Rejected"].includes(r.status)) {







            stSelect.value = r.status;







        } else if ((r.status || "").toLowerCase().includes("process")) {







            stSelect.value = "InProgress";







        } else if ((r.status || "").toLowerCase().includes("reject")) {







            stSelect.value = "Rejected";







        } else {







            stSelect.value = "Completed";







        }







    }







    const panInput = document.getElementById("form-pan-type");







    if (panInput) panInput.value = r.pan_type || "";







    document.getElementById("form-fee").value = r.fee_amt || r.total_amt || "";







    document.getElementById("form-remark").value = r.remark || "";







    openModal("modal-record-form");







}







async function handleRecordFormSubmit(e) {







    e.preventDefault();







    const recordId = document.getElementById("form-record-id").value;







    const isEdit = !!recordId;







    const svc = document.getElementById("form-service-type").value;







    let stVal = document.getElementById("form-status").value;







    // PAN card and Ayushman card do NOT need status







    if (svc === "pancard" || svc === "aayushman") {







        stVal = "";







    } else {







        if (!["Completed", "InProgress", "Rejected"].includes(stVal)) {







            stVal = "InProgress";







        }







    }







    const payload = {







        service_type: svc,







        record_date: document.getElementById("form-date").value,







        name: document.getElementById("form-name").value.trim(),







        mobile: document.getElementById("form-mobile").value.trim(),







        id_number: document.getElementById("form-id-number").value.trim(),







        status: stVal,







        pan_type: document.getElementById("form-pan-type").value.trim(),







        fee_amt: parseFloat(document.getElementById("form-fee").value) || 0.0,







        total_amt: parseFloat(document.getElementById("form-fee").value) || 0.0,







        remark: document.getElementById("form-remark").value.trim()







    };







    if (isStaticMode) {







        if (isEdit) {







            const idx = staticRecords.findIndex(r => r.id === Number(recordId));







            if (idx !== -1) {







                staticRecords[idx] = { ...staticRecords[idx], ...payload, id: Number(recordId) };







            }







        } else {







            const nextId = staticRecords.reduce((max, r) => Math.max(max, r.id || 0), 0) + 1;







            staticRecords.unshift({







                id: nextId,







                ...payload,







                normalized_mobile: (payload.mobile || "").replace(/\D/g, "").slice(-10),







                is_baki: (payload.remark || "").toUpperCase().includes("BAKI") ? 1 : 0







            });







        }







        saveStaticRecords(staticRecords);







        showToast(isEdit ? "Record updated" : "Entry added successfully", "success");







        closeModal("modal-record-form");







        await loadDailyProgress();







        await fetchRecords(currentPage);







        return;







    }







    try {







        const url = apiUrl(isEdit ? `/api/records/${recordId}` : "/api/records");







        const method = isEdit ? "PUT" : "POST";







        const tok = getActiveSessionToken();



        const recHeaders = { "Content-Type": "application/json" };



        if (tok) recHeaders["X-Session-Token"] = tok;



        const res = await fetch(url, {



            method: method,



            headers: recHeaders,



            credentials: "include",



            body: JSON.stringify(payload)



        });







        const data = await res.json();







        if (!res.ok) throw new Error(data.detail || "Failed to save record");







        showToast(isEdit ? "Record updated" : "Entry added successfully", "success");







        closeModal("modal-record-form");







        await loadDailyProgress();







        await fetchRecords(currentPage);







    } catch (err) {







        showToast(err.message, "error");







    }







}







async function deleteRecordAction(recordId) {







    if (!confirm("Are you sure you want to delete this record?")) return;







    if (isStaticMode) {







        staticRecords = staticRecords.filter(r => r.id !== Number(recordId));







        saveStaticRecords(staticRecords);







        showToast("Record deleted", "info");







        await loadDailyProgress();







        await fetchRecords(currentPage);







        return;







    }







    try {







        const res = await fetch(apiUrl(`/api/records/${recordId}`), { method: "DELETE" });







        if (!res.ok) throw new Error("Failed to delete record");







        showToast("Record deleted", "info");







        await loadDailyProgress();







        await fetchRecords(currentPage);







    } catch (err) {







        showToast(err.message, "error");







    }







}







// =========================================================================







// DAILY UPLOADS & FILE MANAGER







// =========================================================================







function setupDropzone() {







    const dropzone = document.getElementById("dropzone");







    if (!dropzone) return;







    ['dragenter', 'dragover'].forEach(eventName => {







        dropzone.addEventListener(eventName, (e) => {







            e.preventDefault();







            e.stopPropagation();







            dropzone.classList.add("dropzone-active");







        }, false);







    });







    ['dragleave', 'drop'].forEach(eventName => {







        dropzone.addEventListener(eventName, (e) => {







            e.preventDefault();







            e.stopPropagation();







            dropzone.classList.remove("dropzone-active");







        }, false);







    });







    dropzone.addEventListener('drop', (e) => {







        const dt = e.dataTransfer;







        const files = dt.files;







        if (files.length > 0) handleSelectedFile(files[0]);







    }, false);







}







function setupWindowDragAndDrop() {







    const overlay = document.getElementById("fullscreen-drop-overlay");







    let dragCounter = 0;







    window.addEventListener("dragenter", (e) => {







        if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes("Files")) {







            e.preventDefault();







            dragCounter++;







            if (overlay) {







                overlay.classList.remove("hidden");







                overlay.classList.remove("pointer-events-none");







            }







        }







    });







    window.addEventListener("dragover", (e) => {







        if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes("Files")) {







            e.preventDefault();







        }







    });







    window.addEventListener("dragleave", (e) => {







        e.preventDefault();







        dragCounter--;







        if (dragCounter <= 0) {







            dragCounter = 0;







            if (overlay) {







                overlay.classList.add("hidden");







                overlay.classList.add("pointer-events-none");







            }







        }







    });







    window.addEventListener("drop", async (e) => {







        e.preventDefault();







        dragCounter = 0;







        if (overlay) {







            overlay.classList.add("hidden");







            overlay.classList.add("pointer-events-none");







        }







        const dt = e.dataTransfer;







        if (dt && dt.files && dt.files.length > 0) {







            const file = dt.files[0];







            const name = (file.name || "").toLowerCase();







            if (name.endsWith(".xlsx") || name.endsWith(".xls") || name.endsWith(".csv")) {







                await processAndImportFileDirectly(file);







            } else {







                showToast("Please drop an Excel (.xlsx, .xls) or CSV file.", "warning");







            }







        }







    });







}







async function processAndImportFileDirectly(file) {







    handleSelectedFile(file);







    openModal("modal-upload");







    showToast(`Processing & importing ${file.name}...`, "info");







    await submitFileUpload();







}







function handleFileSelect(event) {







    const files = event.target.files;







    if (files.length > 0) handleSelectedFile(files[0]);







}







function handleSelectedFile(file) {







    selectedUploadFile = file;







    const nameDisplay = document.getElementById("selected-file-name");







    const submitBtn = document.getElementById("btn-submit-upload");







    nameDisplay.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;







    nameDisplay.classList.remove("hidden");







    submitBtn.disabled = false;







}







async function submitFileUpload() {







    if (!selectedUploadFile) return;







    const svcType = document.getElementById("upload-service-select").value;







    const formData = new FormData();







    formData.append("file", selectedUploadFile);







    formData.append("service_type", svcType);







    const progressBox = document.getElementById("upload-progress-container");







    const submitBtn = document.getElementById("btn-submit-upload");







    progressBox.classList.remove("hidden");







    submitBtn.disabled = true;







    // 1. ONLINE SERVER MODE: Upload to FastAPI backend & SQLite database







    if (!isStaticMode) {







        try {







            const tok = getActiveSessionToken();



            const upHeaders = {};



            if (tok) upHeaders["X-Session-Token"] = tok;



            const res = await fetch(apiUrl("/api/upload"), {



                method: "POST",



                headers: upHeaders,



                credentials: "include",



                body: formData



            });







            const data = await res.json();







            if (!res.ok) throw new Error(data.detail || "Upload failed");







            showToast(data.message || `Successfully imported ${data.imported_rows} records!`, "success");







            closeModal("modal-upload");







            selectedUploadFile = null;







            document.getElementById("file-input").value = "";







            document.getElementById("selected-file-name").classList.add("hidden");







            await loadDailyProgress();







            await fetchRecords(1);







        } catch (err) {







            showToast(err.message, "error");







        } finally {







            progressBox.classList.add("hidden");







            submitBtn.disabled = false;







        }







        return;







    }







    // 2. OFFLINE CLIENT-SIDE FALLBACK (only if opened via file:/// without server)







    if (isStaticMode) {







        if (!window.XLSX) {







            showToast("SheetJS library is loading, please try again", "warning");







            progressBox.classList.add("hidden");







            submitBtn.disabled = false;







            return;







        }







        const reader = new FileReader();







        reader.onload = async function(e) {







            try {







                const data = new Uint8Array(e.target.result);







                const workbook = XLSX.read(data, { type: "array" });







                const sheetNames = workbook.SheetNames || [];







                







                let totalImported = 0;







                let sheetsProcessed = 0;







                const newFileId = Date.now();







                let detectedOverallService = svcType !== "auto" ? svcType : null;







                const cleanHdr = (str) => {







                    if (!str) return "";







                    return String(str).toLowerCase().trim().replace(/[_\-\.\(\)\[\]\/\\:]+/g, " ").replace(/\s+/g, " ");







                };







                const parseDateStr = (val) => {







                    if (!val) return "";







                    // Numeric Excel serial date (e.g. 46328)







                    if (typeof val === "number" && val >= 30000 && val <= 65000) {







                        const d = new Date(Math.round((val - 25569) * 86400 * 1000));







                        const y = d.getUTCFullYear();







                        const m = String(d.getUTCMonth() + 1).padStart(2, '0');







                        const day = String(d.getUTCDate()).padStart(2, '0');







                        return `${y}-${m}-${day}`;







                    }







                    if (val instanceof Date && !isNaN(val)) {







                        const y = val.getFullYear();







                        const m = String(val.getMonth() + 1).padStart(2, '0');







                        const day = String(val.getDate()).padStart(2, '0');







                        return `${y}-${m}-${day}`;







                    }







                    const s = String(val).trim();







                    if (/^\d{5}(\.\d+)?$/.test(s)) {







                        const num = parseFloat(s);







                        if (num >= 30000 && num <= 65000) {







                            const d = new Date(Math.round((num - 25569) * 86400 * 1000));







                            const y = d.getUTCFullYear();







                            const m = String(d.getUTCMonth() + 1).padStart(2, '0');







                            const day = String(d.getUTCDate()).padStart(2, '0');







                            return `${y}-${m}-${day}`;







                        }







                    }







                    // Match YYYY-MM-DD or YYYY-DD-MM (Excel US-locale export flip)







                    const mIso = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);







                    if (mIso) {







                        const y = mIso[1];







                        const p1 = parseInt(mIso[2], 10);







                        const p2 = parseInt(mIso[3], 10);







                        if (p1 >= 1 && p1 <= 31 && p2 === 10) {







                            return `${y}-10-${String(p1).padStart(2, '0')}`;







                        }







                        return `${y}-${String(p1).padStart(2, '0')}-${String(p2).padStart(2, '0')}`;







                    }







                    // Match DD-MM-YYYY or DD/MM/YYYY or D-M-YYYY







                    const mDm = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})/);







                    if (mDm) {







                        let yr = mDm[3];







                        if (yr.length === 2) yr = "20" + yr;







                        else if (yr.length === 3) yr = "2026";







                        return `${yr}-${String(mDm[2]).padStart(2, '0')}-${String(mDm[1]).padStart(2, '0')}`;







                    }







                    return "";







                };







                const detectSheetService = (sName, hdrs, fName) => {







                    const cleanS = cleanHdr(sName);







                    if (cleanS.includes("srn") || cleanS.includes("online")) return "aadhar_online";







                    if (cleanS.includes("pan")) return "pancard";







                    if (cleanS.includes("ration") || cleanS.includes("ayushman") || cleanS.includes("aayushman")) return "aayushman";







                    if (cleanS.includes("sid") || cleanS.includes("uc")) return "ucaadhar";







                    const joinedH = hdrs.map(cleanHdr).join(" ");







                    if (joinedH.includes("sid")) return "ucaadhar";







                    if (joinedH.includes("srn")) return "aadhar_online";







                    if (joinedH.includes("pan change") || joinedH.includes("pan new") || joinedH.includes("pancard") || joinedH.includes("pan")) return "pancard";







                    if (joinedH.includes("ration") || joinedH.includes("ayushman") || joinedH.includes("aayushman")) return "aayushman";







                    const lowF = (fName || "").toLowerCase();







                    if (lowF.includes("ucaadhar") || lowF.includes("uc_aadhar") || lowF.includes("sid")) return "ucaadhar";







                    if (lowF.includes("aadhar_online") || lowF.includes("online_aadhar") || lowF.includes("srn")) return "aadhar_online";







                    if (lowF.includes("pan")) return "pancard";







                    if (lowF.includes("ayushman") || lowF.includes("aayushman") || lowF.includes("ration")) return "aayushman";







                    return "ucaadhar";







                };







                // Iterate over EVERY sheet in the uploaded Excel workbook







                const allImportedRecordSvcs = [];







                sheetNames.forEach(sheetName => {







                    const sheet = workbook.Sheets[sheetName];







                    if (!sheet) return;







                    const rawRows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });







                    if (!rawRows || rawRows.length === 0) return;







                    const sheetDateCandidate = parseDateStr(sheetName);







                    let currentSheetDate = sheetDateCandidate || "";







                    if (!currentSheetDate) {







                        for (let scanIdx = 0; scanIdx < Math.min(rawRows.length, 60); scanIdx++) {







                            const scanRow = rawRows[scanIdx] || [];







                            for (const cellVal of scanRow) {







                                if (!cellVal) continue;







                                const cellStr = String(cellVal).trim();







                                const mSidDate = cellStr.match(/S\d{10,14}(202[0-9])(0[1-9]|1[0-2])([0-3][0-9])/);







                                if (mSidDate) {







                                    currentSheetDate = `${mSidDate[1]}-${mSidDate[2]}-${mSidDate[3]}`;







                                    break;







                                }







                                const pScan = parseDateStr(cellVal);







                                if (pScan && cellStr.length <= 15) {







                                    currentSheetDate = pScan;







                                    break;







                                }







                            }







                            if (currentSheetDate) break;







                        }







                    }







                    if (!currentSheetDate) {







                        currentSheetDate = new Date().toISOString().split("T")[0];







                    }







                    let headers = [];







                    let idxDate = -1;







                    let idxName = -1;







                    let idxSid = -1;







                    let idxSrn = -1;







                    let idxPan = -1;







                    let idxRation = -1;







                    let idxMobile = -1;







                    let idxStatus = -1;







                    let idxTotal = -1;







                    let idxFee = -1;







                    let idxRemark = -1;







                    const updateColumns = (rowCells) => {







                        headers = rowCells.map(cleanHdr);







                        const findC = (syns, exclude = []) => {







                            for (const syn of syns) {







                                for (let i = 0; i < headers.length; i++) {







                                    const h = headers[i];







                                    if (!h) continue;







                                    if (exclude.some(ex => h.includes(ex))) continue;







                                    if (h === syn || (syn.length >= 3 && h.includes(syn)) || (h.length >= 3 && syn.includes(h)) || (['mo', 'mo.', 'mob'].includes(h) && ['mo', 'mobile'].includes(syn))) {







                                        return i;







                                    }







                                }







                            }







                            return -1;







                        };







                        idxDate = findC(['date', 'dt'], ['enrol', 'enroll']);







                        idxName = findC(['name', 'party', 'client']);







                        idxSid = findC(['sid', 'enrolment', 'enrollment']);







                        idxSrn = findC(['srn']);







                        idxPan = findC(['pan change', 'pan new', 'pan type', 'pan']);







                        idxRation = findC(['ration', 'ayushman', 'aayushman']);







                        idxMobile = findC(['mobile', 'mo', 'contact', 'phone']);







                        idxStatus = findC(['status']);







                        idxTotal = findC(['total', 'amount', 'amt']);







                        idxFee = findC(['fee']);







                        idxRemark = findC(['remark', 'others', 'note']);







                    };







                    let sheetSvc = (svcType && svcType !== "auto") ? svcType : detectSheetService(sheetName, (rawRows[0] || []).map(String), selectedUploadFile.name);







                    let sheetRowCount = 0;







                    for (let r = 0; r < rawRows.length; r++) {







                        const row = rawRows[r];







                        if (!row || row.length === 0) continue;







                        const rowStr = row.map(c => (c !== null && c !== undefined) ? String(c).trim() : "");







                        if (rowStr.every(c => c === "" || c.toLowerCase() === "nan")) continue;







                        const joinedUpper = rowStr.join(" ").toUpperCase();







                        const firstCell = (rowStr[0] || "").replace(/\.0$/, "").trim();







                        const hasIntegerIndex = /^\d+$/.test(firstCell);







                        const hasPhone = rowStr.some(c => /\b[6-9]\d{9}\b/.test(c.replace(/\.0$/, "").replace(/\s+/g, "")));







                        const hasSid = rowStr.some(c => /S\d{15,30}/i.test(c));







                        // 1. Check if header row (Never treat a data row as header!)







                        if (!hasIntegerIndex && !hasPhone && !hasSid) {







                            const headerWords = ["NAME", "PARTY", "DATE", "MOBILE", "MO", "PHONE", "SRN", "SID", "PAN", "STATUS", "REMARK", "TOTAL", "FEE", "RATION", "AYUSHMAN", "SLNO", "SR NO", "ENROLMENT"];







                            const matchCount = headerWords.filter(w => new RegExp(`\\b${w}\\b`, 'i').test(joinedUpper)).length;







                            if (matchCount >= 2 && /NAME|PARTY|SRN|SID|PAN|RATION|ENROLMENT|SLNO|SR NO/i.test(joinedUpper)) {







                                updateColumns(rowStr);







                                continue;







                            }







                            if (joinedUpper.includes("ENROLMENT") || joinedUpper.includes("SID NUMBER") || joinedUpper.includes("SRN") || joinedUpper.includes("RATION CARD") ||







                                (rowStr.slice(0, 2).some(cell => ["NO", "SLNO", "SR NO", "SRNO"].includes(cell.toUpperCase())) && (joinedUpper.includes("NAME") || joinedUpper.includes("STATUS") || joinedUpper.includes("TOTAL") || joinedUpper.includes("SID") || joinedUpper.includes("DATE")))) {







                                updateColumns(rowStr);







                                continue;







                            }







                        }







                        if (headers.length === 0) {







                            updateColumns(['SLNO', 'ENROLMENT', 'STATUS', 'TOTAL', 'FEE', 'OTHERS']);







                        }







                        // 2. Check if date divider row







                        const nonEmpty = rowStr.filter(s => s !== "" && s.toLowerCase() !== "nan");







                        if (nonEmpty.length <= 2 && !hasPhone && !hasSid) {







                            const dMatches = nonEmpty.map(parseDateStr).filter(Boolean);







                            if (dMatches.length > 0 && !hasIntegerIndex) {







                                currentSheetDate = dMatches[0];







                                continue;







                            }







                        }







                        // 3. Check if subtotal summary row or ID divider row







                        if (!hasSid && !hasPhone) {







                            if (nonEmpty.every(s => /^[\d\.\,]+$/.test(s))) continue;







                            if (/BRIJAL ID|MANISH ID|TOTAL/i.test(joinedUpper) && !hasIntegerIndex) continue;







                        }







                        // 4. Extract SID / SRN / ID Number & authoritative Date from SID







                        let idNum = "";







                        let recSid = "";







                        for (const s of rowStr) {







                            const m = s.match(/\b(S\d{20,30})\b/i);







                            if (m) {







                                recSid = m[1].toUpperCase();







                                break;







                            }







                        }







                        let recDate = currentSheetDate;







                        if (recSid) {







                            idNum = recSid;







                            const mDate = recSid.match(/S\d{10,14}(202[0-9])(0[1-9]|1[0-2])([0-3][0-9])/);







                            if (mDate) {







                                recDate = `${mDate[1]}-${mDate[2]}-${mDate[3]}`;







                            }







                        } else if (idxDate !== -1 && idxDate < rowStr.length && rowStr[idxDate]) {







                            const pd = parseDateStr(rowStr[idxDate]);







                            if (pd) {







                                recDate = pd;







                                currentSheetDate = pd;







                            }







                        }







                        if (!idNum && idxSid !== -1 && idxSid < rowStr.length && rowStr[idxSid]) {







                            const val = rowStr[idxSid];







                            const m = val.match(/\b(S\d{10,30})\b/i);







                            if (m) {







                                idNum = m[1].toUpperCase();







                            }







                        }







                        if (!idNum && idxSrn !== -1 && idxSrn < rowStr.length && rowStr[idxSrn]) {







                            idNum = rowStr[idxSrn];







                        }







                        if (!idNum && idxRation !== -1 && idxRation < rowStr.length && rowStr[idxRation]) {







                            idNum = rowStr[idxRation];







                        }







                        // 5. Name extraction







                        const NON_NAME_SET = new Set([







                            "NAME", "ADDRESS", "MOBILE", "MO", "MOB", "PHONE", "SPEED", "NEW", "RIPIT", "REPEAT",







                            "OK", "NOT RECIV", "NOT RICIV", "NO RECIV", "CALL NOT PICKUP", "CALL NOT RECEIVRD",







                            "MANISH ID", "BRIJAL ID", "TOTAL", "STATUS", "SLNO", "ENROLMENT_NO_DATE", "SID NUMBER",







                            "OTHERS", "REMARK", "FEE", "NAME CHANGE", "NAME CHANJ"







                        ]);







                        let name = "";







                        if (idxName !== -1 && idxName < rowStr.length && rowStr[idxName]) {







                            const cand = rowStr[idxName];







                            if (!cand.startsWith("S1") && !/^[\d\.]+$/.test(cand) && !parseDateStr(cand)) {







                                name = cand;







                            }







                        }







                        // Case A: Format 1 (Col 1 is SID, Col 2 is Name)







                        if (!name && rowStr.length > 2 && recSid && (rowStr[1].toUpperCase().startsWith("S1") || rowStr[0].toUpperCase().startsWith("S1"))) {







                            const sidCol = rowStr[1].toUpperCase().startsWith("S1") ? 1 : 0;







                            const candCol = sidCol + 1;







                            if (candCol < rowStr.length) {







                                const cand = rowStr[candCol];







                                const candU = cand.toUpperCase();







                                if (cand && !candU.startsWith("COMPLET") && !candU.startsWith("INPROCESS") && !candU.startsWith("REJECT") && !/^[\d\.]+$/.test(cand) && !parseDateStr(cand)) {







                                    name = cand;







                                }







                            }







                        }







                        // Case B: Col 1 is Customer Name directly







                        if (!name && rowStr.length > 1) {







                            const cand = rowStr[1];







                            const candU = cand.toUpperCase();







                            if (cand && !cand.startsWith("S1") && !candU.startsWith("COMPLET") && !candU.startsWith("INPROCESS") && !candU.startsWith("REJECT") && !/^[\d\.]+$/.test(cand) && !parseDateStr(cand)) {







                                if (!NON_NAME_SET.has(candU) && !candU.includes("ID") && !candU.includes("TOTAL")) {







                                    name = cand;







                                }







                            }







                        }







                        // Case C: Label 'NAME' in later column







                        if (!name) {







                            for (let i = 0; i < rowStr.length; i++) {







                                if (["NAME", "NAME:"].includes(rowStr[i].toUpperCase()) && i + 1 < rowStr.length) {







                                    const nextC = rowStr[i + 1];







                                    if (nextC && !NON_NAME_SET.has(nextC.toUpperCase()) && !/^[\d\.]+$/.test(nextC) && !parseDateStr(nextC)) {







                                        name = nextC;







                                        break;







                                    }







                                }







                            }







                        }







                        // Case D: Person name in extra columns







                        if (!name) {







                            for (let i = 2; i < rowStr.length; i++) {







                                const c = rowStr[i];







                                const cU = c.toUpperCase();







                                if (!c || /^[\d\.]+$/.test(c) || /\b[6-9]\d{9}\b/.test(c) || parseDateStr(c)) continue;







                                if (c.includes("/")) {







                                    const part0 = c.split("/")[0].trim();







                                    if (part0.split(/\s+/).length >= 2 && !NON_NAME_SET.has(part0.toUpperCase()) && !parseDateStr(part0)) {







                                        name = part0;







                                        break;







                                    }







                                } else if (c.includes("-") && cU.includes("NAME")) {







                                    const cleanNm = c.replace(/\bNAME\b/gi, "").replace("-", "").trim();







                                    if (cleanNm && !parseDateStr(cleanNm)) {







                                        name = cleanNm;







                                        break;







                                    }







                                } else if (c.split(/\s+/).length >= 2 && !NON_NAME_SET.has(cU) && !parseDateStr(c)) {







                                    name = c;







                                    break;







                                }







                            }







                        }







                        if (!name && recSid) {







                            name = "—";







                        }







                        // 6. PAN Type







                        let panType = "";







                        if (idxPan !== -1 && idxPan < rowStr.length && rowStr[idxPan]) {







                            panType = rowStr[idxPan];







                        } else {







                            for (const c of rowStr) {







                                const cU = c.toUpperCase();







                                if (cU === "PAN NEW" || cU === "PAN CHANGE" || cU.includes("PAN")) {







                                    panType = c;







                                    break;







                                }







                            }







                        }







                        // 7. Status (Completed, InProgress, Rejected for Aadhaar; None for PAN/Ayushman)







                        let status = "Completed";







                        if (/REJECT/i.test(joinedUpper)) status = "Rejected";







                        else if (/INPROCESS|IN PROCESS/i.test(joinedUpper) || /PENDING/i.test(joinedUpper)) status = "InProgress";







                        else if (idxStatus !== -1 && idxStatus < rowStr.length && rowStr[idxStatus]) {







                            const stRaw = rowStr[idxStatus].toLowerCase();







                            if (stRaw.includes("process") || stRaw.includes("pending")) status = "InProgress";







                            else if (stRaw.includes("reject") || stRaw.includes("cancel")) status = "Rejected";







                            else if (stRaw.includes("complet")) status = "Completed";







                        }







                        // 8. Total & Fee







                        let totalAmt = 0;







                        let feeAmt = 0;







                        if (idxTotal !== -1 && idxTotal < rowStr.length && rowStr[idxTotal]) {







                            const parsed = parseFloat(rowStr[idxTotal]);







                            if (!isNaN(parsed)) totalAmt = parsed;







                            if (idxFee !== -1 && idxFee < rowStr.length && rowStr[idxFee]) {







                                const pf = parseFloat(rowStr[idxFee]);







                                if (!isNaN(pf)) feeAmt = pf;







                            } else if (idxTotal + 1 < rowStr.length && rowStr[idxTotal + 1]) {







                                const pf = parseFloat(rowStr[idxTotal + 1]);







                                if (!isNaN(pf)) feeAmt = pf;







                            }







                        } else {







                            const nums = [];







                            rowStr.forEach((c, idx) => {







                                if (idx === 0 && /^\d+(\.0)?$/.test(c) && parseFloat(c) < 1000) return;







                                if (/^\d+(\.\d+)?$/.test(c) && !/\b[6-9]\d{9}\b/.test(c)) {







                                    const val = parseFloat(c);







                                    if (val <= 1000) nums.push(val);







                                }







                            });







                            if (nums.length >= 2) {







                                totalAmt = nums[0];







                                feeAmt = nums[1];







                            } else if (nums.length === 1) {







                                totalAmt = nums[0];







                            }







                        }







                        // 9. Mobile & Remarks







                        let rawMob = (idxMobile !== -1 && idxMobile < rowStr.length) ? rowStr[idxMobile] : "";







                        if (!rawMob) {







                            const mPh = joinedUpper.match(/\b[6-9]\d{9}\b/);







                            if (mPh) rawMob = mPh[0];







                        }







                        rawMob = rawMob.replace(/\.0$/, "").trim();







                        const remarksList = [];







                        if (idxRemark !== -1 && idxRemark < rowStr.length && rowStr[idxRemark]) {







                            const rVal = rowStr[idxRemark];







                            if (rVal !== name && rVal !== idNum && rVal !== rawMob && rVal !== panType && !parseDateStr(rVal)) {







                                remarksList.push(rVal);







                            }







                        }







                        rowStr.forEach((c, cIdx) => {







                            if (!c) return;







                            if (c === name || c === idNum || c === rawMob || c.replace(/\.0$/, "") === rawMob) return;







                            if (c === panType || (idxPan !== -1 && cIdx === idxPan)) return;







                            if (parseDateStr(c) || (idxDate !== -1 && cIdx === idxDate)) return;







                            if (/COMPLETED|INPROCESS|IN PROCESS|REJECT|REJECTED|PENDING/i.test(c)) return;







                            if (/^[\d\.]+$/.test(c) && parseFloat(c) < 1000) return;







                            if (["NO", "SLNO", "SR NO", "SRNO", "SID NUMBER", "TOTAL", "STATUS", "NAME", "MOBILE"].includes(c.toUpperCase())) return;







                            if (!remarksList.includes(c)) remarksList.push(c);







                        });







                        const remark = remarksList.join(" | ");







                        // 10. Service determination







                        let rowSvc = sheetSvc;







                        const cleanId = (idNum || "").trim().toUpperCase();







                        if (!svcType || svcType === "auto") {







                            if (cleanId.startsWith("SID") || (cleanId.startsWith("S") && cleanId.length >= 18)) {







                                rowSvc = "ucaadhar";







                            } else if (cleanId.startsWith("SRN") || (cleanId.startsWith("S") && cleanId.length >= 10 && cleanId.length <= 16)) {







                                rowSvc = "aadhar_online";







                            } else if (panType || (idxPan !== -1 && rowStr[idxPan])) {







                                rowSvc = "pancard";







                            } else if (idxRation !== -1 && rowStr[idxRation]) {







                                rowSvc = "aayushman";







                            } else if (cleanId.startsWith("S")) {







                                rowSvc = "ucaadhar";







                            }







                        }







                        // Add record if we have name, idNum, or rawMob







                        if (name || idNum || rawMob) {







                            const nextId = staticRecords.reduce((max, rec) => Math.max(max, rec.id || 0), 0) + 1;







                            const normMob = rawMob.replace(/\D/g, "").slice(-10);







                            const isBaki = /BAKI|NOT RECIV|NOT RESIV|NO RECIV/i.test(remark) ? 1 : 0;







                            staticRecords.unshift({







                                id: nextId,







                                file_id: newFileId,







                                service_type: rowSvc,







                                record_date: recDate,







                                name: name,







                                mobile: rawMob,







                                normalized_mobile: normMob,







                                id_number: idNum,







                                pan_type: panType || ((rowSvc === "pancard" && idxPan !== -1) ? rowStr[idxPan] : ""),







                                status: (rowSvc === "pancard" || rowSvc === "aayushman") ? "" : (status || "Completed"),







                                fee_amt: feeAmt,







                                total_amt: totalAmt,







                                remark: remark,







                                is_baki: isBaki







                            });







                            allImportedRecordSvcs.push(rowSvc);







                            sheetRowCount++;







                            totalImported++;







                        }







                    }







                    if (sheetRowCount > 0) {







                        sheetsProcessed++;







                    }







                });







                if (!detectedOverallService && allImportedRecordSvcs.length > 0) {







                    const counts = {};







                    allImportedRecordSvcs.forEach(s => counts[s] = (counts[s] || 0) + 1);







                    detectedOverallService = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);







                }







                let files = getStaticFiles();







                files.unshift({







                    id: newFileId,







                    filename: selectedUploadFile.name,







                    service_type: detectedOverallService || (svcType !== "auto" ? svcType : "ucaadhar"),







                    row_count: totalImported,







                    file_size: selectedUploadFile.size,







                    uploaded_at: new Date().toISOString().replace("T", " ").substring(0, 19)







                });







                saveStaticFiles(files);







                saveStaticRecords(staticRecords);







                const sheetInfo = sheetsProcessed > 1 ? ` across ${sheetsProcessed} sheets` : "";







                showToast(`Successfully imported ${totalImported} records${sheetInfo}!`, "success");







                closeModal("modal-upload");







                selectedUploadFile = null;







                document.getElementById("file-input").value = "";







                document.getElementById("selected-file-name").classList.add("hidden");







                







                // Immediately select the latest date from the imported records in the showcase!







                const latestImportedDate = getLatestRecordDate();







                if (latestImportedDate) {







                    applyDateFilter(latestImportedDate);







                } else {







                    await loadDailyProgress();







                    await fetchRecords(1);







                }







            } catch (err) {







                showToast("Failed to parse file: " + err.message, "error");







            } finally {







                progressBox.classList.add("hidden");







                submitBtn.disabled = false;







            }







        };







        reader.readAsArrayBuffer(selectedUploadFile);







        return;







    }







}







async function openFilesModal() {







    openModal("modal-files");







    const container = document.getElementById("files-list-container");







    container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Loading files...</div>';







    let files = [];







    if (isStaticMode) {







        files = getStaticFiles();







    } else {







        try {







            const res = await fetch(apiUrl("/api/files"));







            if (res.ok) {







                files = await res.json();







            } else {







                files = getStaticFiles();







            }







        } catch (err) {







            files = getStaticFiles();







        }







    }







    if (!files || files.length === 0) {







        container.innerHTML = `







            <div class="text-center py-8">







                <p class="text-xs text-slate-500 mb-3">No office files currently loaded. Upload an Excel or CSV file to start.</p>







                <button onclick="openUploadModal(); closeModal('modal-files');" class="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-xs">







                    <i data-lucide="upload-cloud" class="w-3.5 h-3.5"></i> Upload Office File







                </button>







            </div>







        `;







        refreshIcons();







        return;







    }







    container.innerHTML = "";







    files.forEach(f => {







        const card = document.createElement("div");







        card.className = "flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200 hover:border-brand-300 transition group";







        const sizeKb = f.file_size ? (f.file_size / 1024).toFixed(1) : "15.0";







        const rowCount = f.row_count || 0;







        card.innerHTML = `







            <div class="flex items-center gap-3 min-w-0 pr-2">







                <div class="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">







                    <i data-lucide="file-spreadsheet" class="w-5 h-5"></i>







                </div>







                <div class="min-w-0">







                    <h4 class="text-xs font-bold text-slate-900 truncate" title="${escapeHtml(f.filename)}">${escapeHtml(f.filename)}</h4>







                    <div class="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5 flex-wrap">







                        <span class="font-bold text-brand-700 uppercase">${escapeHtml(f.service_type || 'General')}</span>







                        <span>•</span>







                        <span class="font-semibold text-slate-700">${rowCount.toLocaleString()} rows</span>







                        <span>•</span>







                        <span>${sizeKb} KB</span>







                        ${f.uploaded_at || f.file_date ? `<span>•</span><span class="font-mono">📅 ${formatDateDisplay(f.uploaded_at || f.file_date)}</span>` : ""}







                    </div>







                </div>







            </div>







            <div class="flex items-center gap-2 shrink-0">







                <button onclick="confirmDeleteFile(${f.id}, '${escapeHtml(f.filename)}')" class="p-2 bg-rose-50 hover:bg-rose-100 text-rose-600 hover:text-rose-700 border border-rose-200 rounded-lg text-xs font-semibold transition inline-flex items-center gap-1" title="Delete file and remove its imported records">







                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>







                    <span class="hidden sm:inline">Delete File</span>







                </button>







            </div>







        `;







        container.appendChild(card);







    });







    refreshIcons();







}







async function confirmDeleteFile(fileId, filename) {







    if (!confirm(`Are you sure you want to delete '${filename}' and remove all its imported records?`)) return;







    if (isStaticMode) {







        let files = getStaticFiles();







        files = files.filter(f => f.id !== fileId);







        saveStaticFiles(files);







        // Remove all records associated with this fileId







        staticRecords = staticRecords.filter(r => r.file_id !== fileId);







        try {







            saveStaticRecords(staticRecords);







        } catch (e) {}







        showToast(`Deleted '${filename}' and its imported records`, "info");







        await loadDailyProgress();







        await openFilesModal();







        await fetchRecords(1);







        return;







    }







    try {







        const res = await fetch(apiUrl(`/api/files/${fileId}`), { method: "DELETE" });







        if (!res.ok) {







            const errData = await res.json().catch(() => ({}));







            throw new Error(errData.detail || "Failed to delete file from database");







        }







        showToast(`Deleted ${filename} from database`, "info");







        await loadDailyProgress();







        await openFilesModal();







        await fetchRecords(1);







    } catch (err) {







        showToast("Error: " + err.message, "error");







    }







}







async function clearAllRecordsData() {







    if (!confirm("Are you sure you want to remove all files and records?")) return;







    localStorage.removeItem(FILES_STORAGE_KEY);







    localStorage.removeItem(STORAGE_KEY);







    staticRecords = [];







    if (!isStaticMode) {







        try {







            await fetch(apiUrl("/api/files"), { method: "DELETE" });







        } catch (e) {}







    }







    showToast("All data cleared successfully!", "info");







    await loadDailyProgress();







    await openFilesModal();







    await fetchRecords(1);







}







// =========================================================================







// EXPORTS & HELPERS







// =========================================================================







function exportCurrentView(format = "excel") {







    const params = getSearchParams();







    if (isStaticMode) {







        let records = staticRecords.slice();







        if (params.service_type && params.service_type !== "all") {







            records = records.filter(r => (r.service_type || "").toLowerCase() === params.service_type.toLowerCase());







        }







        if (params.date) {







            const isoD = normalizeDateToIso(params.date);







            records = records.filter(r => {







                const rd = r.record_date || "";







                return rd.startsWith(params.date) || (isoD && rd.startsWith(isoD)) || formatDateDisplay(rd).includes(params.date);







            });







        }







        const currentSvc = (params.service_type || "all").toLowerCase();







        if (format === "excel" && window.XLSX) {







            let wsData = [];







            if (currentSvc === "ucaadhar") {







                wsData = records.map((r, i) => ({







                    "Sr No": i + 1,







                    "Date": formatDateDisplay(r.record_date),







                    "Name": r.name || "",







                    "SID Number": r.id_number || "",







                    "Mobile No": r.mobile || "",







                    "Status": r.status || "Completed",







                    "Govt Total": r.total_amt || 0,







                    "Fee": r.fee_amt || 0,







                    "Remarks": r.remark || ""







                }));







            } else if (currentSvc === "aadhar_online") {







                wsData = records.map((r, i) => ({







                    "Sr No": i + 1,







                    "Date": formatDateDisplay(r.record_date),







                    "Name": r.name || "",







                    "SRN Number": r.id_number || "",







                    "Mobile No": r.mobile || "",







                    "Status": r.status || "Completed",







                    "Remarks": r.remark || ""







                }));







            } else if (currentSvc === "pancard") {







                wsData = records.map((r, i) => ({







                    "Sr No": i + 1,







                    "Date": formatDateDisplay(r.record_date),







                    "Name": r.name || "",







                    "Mobile No": r.mobile || "",







                    "PAN Type": r.pan_type || "",







                    "Fee": r.fee_amt || 0,







                    "Remarks": r.remark || ""







                }));







            } else if (currentSvc === "aayushman") {







                wsData = records.map((r, i) => ({







                    "Sr No": i + 1,







                    "Date": formatDateDisplay(r.record_date),







                    "Name": r.name || "",







                    "Ration / Ayushman No": r.id_number || "",







                    "Mobile No": r.mobile || "",







                    "Remarks": r.remark || ""







                }));







            } else {







                wsData = records.map((r, i) => {







                    const rowSvc = (r.service_type || "").toLowerCase();







                    const st = (rowSvc === "pancard" || rowSvc === "aayushman") ? "" : (r.status || "Completed");







                    return {







                        "Sr No": i + 1,







                        "Date": formatDateDisplay(r.record_date),







                        "Name": r.name || "",







                        "Service": (r.service_type || "").toUpperCase(),







                        "ID Number": r.id_number || "",







                        "Mobile No": r.mobile || "",







                        "Status": st,







                        "Amount": r.fee_amt || 0,







                        "Remarks": r.remark || ""







                    };







                });







            }







            const wb = XLSX.utils.book_new();







            const ws = XLSX.utils.json_to_sheet(wsData);







            XLSX.utils.book_append_sheet(wb, ws, "Records");







            XLSX.writeFile(wb, `Khodal_${params.service_type || "ALL"}_Export.xlsx`);







            showToast("Excel exported successfully!", "success");







            return;







        }







        // CSV export







        let csv = "";







        if (currentSvc === "ucaadhar") {







            csv = "Sr No,Date,Name,SID Number,Mobile No,Status,Govt Total,Fee,Remarks\n";







            records.forEach((r, idx) => {







                csv += [







                    idx + 1,







                    `"${formatDateDisplay(r.record_date)}"`,







                    `"${(r.name || '').replace(/"/g, '""')}"`,







                    `"${r.id_number || ''}"`,







                    `"${r.mobile || ''}"`,







                    `"${r.status || 'Completed'}"`,







                    r.total_amt || 0,







                    r.fee_amt || 0,







                    `"${(r.remark || '').replace(/"/g, '""')}"`







                ].join(",") + "\n";







            });







        } else if (currentSvc === "aadhar_online") {







            csv = "Sr No,Date,Name,SRN Number,Mobile No,Status,Remarks\n";







            records.forEach((r, idx) => {







                csv += [







                    idx + 1,







                    `"${formatDateDisplay(r.record_date)}"`,







                    `"${(r.name || '').replace(/"/g, '""')}"`,







                    `"${r.id_number || ''}"`,







                    `"${r.mobile || ''}"`,







                    `"${r.status || 'Completed'}"`,







                    `"${(r.remark || '').replace(/"/g, '""')}"`







                ].join(",") + "\n";







            });







        } else if (currentSvc === "pancard") {







            csv = "Sr No,Date,Name,Mobile No,PAN Type,Fee,Remarks\n";







            records.forEach((r, idx) => {







                csv += [







                    idx + 1,







                    `"${formatDateDisplay(r.record_date)}"`,







                    `"${(r.name || '').replace(/"/g, '""')}"`,







                    `"${r.mobile || ''}"`,







                    `"${r.pan_type || ''}"`,







                    r.fee_amt || 0,







                    `"${(r.remark || '').replace(/"/g, '""')}"`







                ].join(",") + "\n";







            });







        } else if (currentSvc === "aayushman") {







            csv = "Sr No,Date,Name,Ration / Ayushman No,Mobile No,Remarks\n";







            records.forEach((r, idx) => {







                csv += [







                    idx + 1,







                    `"${formatDateDisplay(r.record_date)}"`,







                    `"${(r.name || '').replace(/"/g, '""')}"`,







                    `"${r.id_number || ''}"`,







                    `"${r.mobile || ''}"`,







                    `"${(r.remark || '').replace(/"/g, '""')}"`







                ].join(",") + "\n";







            });







        } else {







            csv = "Sr No,Date,Name,Service,ID Number,Mobile No,Status,Amount,Remarks\n";







            records.forEach((r, idx) => {







                const rowSvc = (r.service_type || "").toLowerCase();







                const st = (rowSvc === "pancard" || rowSvc === "aayushman") ? "" : (r.status || "Completed");







                csv += [







                    idx + 1,







                    `"${formatDateDisplay(r.record_date)}"`,







                    `"${(r.name || '').replace(/"/g, '""')}"`,







                    `"${(r.service_type || '').toUpperCase()}"`,







                    `"${r.id_number || ''}"`,







                    `"${r.mobile || ''}"`,







                    `"${st}"`,







                    r.fee_amt || 0,







                    `"${(r.remark || '').replace(/"/g, '""')}"`







                ].join(",") + "\n";







            });







        }







        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });







        const url = URL.createObjectURL(blob);







        const a = document.createElement("a");







        a.href = url;







        a.download = `Khodal_${params.service_type || 'all'}_Export.csv`;







        a.click();







        showToast("CSV exported successfully!", "success");







        return;







        a.download = `Khodal_${params.service_type || 'all'}_Export.csv`;







        a.click();







        showToast("CSV exported successfully!", "success");







        return;







    }







    const queryStr = new URLSearchParams();







    if (params.service_type) queryStr.append("service_type", params.service_type);







    if (params.name) queryStr.append("name", params.name);







    if (params.mobile) queryStr.append("mobile", params.mobile);







    if (params.id_number) queryStr.append("id_number", params.id_number);







    if (params.date) queryStr.append("date", params.date);







    const endpoint = apiUrl(format === "excel" ? "/api/export" : "/api/export/csv");







    window.location.href = `${endpoint}?${queryStr.toString()}`;







    showToast(`Downloading ${format.toUpperCase()} export...`, "info");







}







function copyShareUrl() {







    if (!lanShareUrl) {







        showToast("Sharing URL not available", "error");







        return;







    }







    navigator.clipboard.writeText(lanShareUrl).then(() => {







        showToast(`Office share link copied: ${lanShareUrl}`, "success");







    }).catch(() => {







        showToast("Could not copy link", "error");







    });







}







function getWhatsAppUrl(mobile, name = "") {







    if (!mobile) return null;







    const digits = mobile.replace(/\D/g, "");







    if (!digits || digits.length < 10) return null;







    let waNumber = digits;







    if (digits.length === 10 && ['6', '7', '8', '9'].includes(digits.charAt(0))) {







        waNumber = `91${digits}`;







    }







    const greeting = name ? `Hello ${encodeURIComponent(name)}, ` : "Hello, ";







    return `https://wa.me/${waNumber}?text=${greeting}`;







}







function highlightText(text, query) {







    if (!text) return "";







    if (!query || query.trim() === "") return escapeHtml(text);







    const safeText = escapeHtml(text);







    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');







    const regex = new RegExp(`(${escapedQuery})`, "gi");







    return safeText.replace(regex, `<mark class="bg-amber-200 text-amber-950 font-bold px-0.5 rounded">$1</mark>`);







}







function escapeHtml(str) {







    if (typeof str !== "string") return str;







    return str







        .replace(/&/g, "&amp;")







        .replace(/</g, "&lt;")







        .replace(/>/g, "&gt;")







        .replace(/"/g, "&quot;")







        .replace(/'/g, "&#039;");







}







function openModal(id) {



    closeMobileMenu();



    const el = document.getElementById(id);







    if (el) {







        el.classList.remove("hidden");







        refreshIcons();







    }







}







function closeModal(id) {







    const el = document.getElementById(id);







    if (el) el.classList.add("hidden");







}







function openUploadModal() {
    const noticeEl = document.getElementById("upload-mode-notice");
    if (noticeEl) {
        noticeEl.classList.remove("hidden");
        if (!isStaticMode) {
            noticeEl.className = "p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-xs text-emerald-900 flex items-center gap-2.5 shadow-2xs";
            noticeEl.innerHTML = `
                <i data-lucide="shield-check" class="w-5 h-5 text-emerald-600 shrink-0"></i>
                <div>
                    <strong class="font-bold text-emerald-950">Target: Permanent Local Database (khodal_office.db)</strong>
                    <div class="text-[11px] text-emerald-800">Your uploaded Excel data will be written directly into SQLite on your computer disk (D: drive). Stored permanently and immune to browser history clears!</div>
                </div>
            `;
        } else {
            noticeEl.className = "p-3 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs";
            noticeEl.innerHTML = `
                <div>
                    <div class="flex items-center gap-1.5 font-bold text-amber-950">
                        <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-600 shrink-0"></i>
                        Target: Temporary Browser Memory (GitHub Pages)
                    </div>
                    <div class="text-[11px] text-amber-800 mt-0.5">
                        GitHub Pages cannot write to your PC's <code>khodal_office.db</code> file directly. If you clear browser history, these records will be wiped.
                        To save directly into <code>khodal_office.db</code>, double-click <strong>START_KHODAL_OFFICE.bat</strong> and open <strong>http://localhost:8000</strong>.
                    </div>
                </div>
                <a href="http://localhost:8000" target="_blank" class="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shrink-0 inline-flex items-center gap-1 cursor-pointer">
                    <i data-lucide="external-link" class="w-3.5 h-3.5"></i> Open Localhost
                </a>
            `;
        }
    }
    openModal("modal-upload");
    refreshIcons();
}







function setupKeyboardListeners() {







    document.addEventListener("keydown", (e) => {







        if (e.key === "Escape") {







            closeModal("modal-upload");







            closeModal("modal-record-form");







            closeModal("modal-view-record");







            closeModal("modal-files");







        }







    });







}







function showToast(message, type = "info") {







    const container = document.getElementById("toast-container");







    if (!container) return;







    const toast = document.createElement("div");







    toast.className = "toast px-4 py-3 rounded-xl shadow-lg border text-xs font-semibold flex items-center gap-2 max-w-sm";







    if (type === "success") {







        toast.className += " bg-emerald-800 text-white border-emerald-700";







        toast.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 shrink-0"></i> <span>${escapeHtml(message)}</span>`;







    } else if (type === "error") {







        toast.className += " bg-rose-800 text-white border-rose-700";







        toast.innerHTML = `<i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i> <span>${escapeHtml(message)}</span>`;







    } else {







        toast.className += " bg-slate-900 text-white border-slate-800";







        toast.innerHTML = `<i data-lucide="info" class="w-4 h-4 shrink-0"></i> <span>${escapeHtml(message)}</span>`;







    }







    container.appendChild(toast);







    refreshIcons();







    setTimeout(() => {







        toast.classList.add("toast-out");







        setTimeout(() => toast.remove(), 250);







    }, 3800);







}







// =========================================================================







// PERMANENT DATABASE BACKUP & RESTORE







// =========================================================================







function updateDatabaseStatusBadge() {
    const banner = document.getElementById("db-storage-status-banner");
    const textEl = document.getElementById("db-status-text");
    if (!textEl) return;
    const isLiveCloud = window.location.protocol.startsWith("http") &&
                        !["localhost", "127.0.0.1"].includes(window.location.hostname) &&
                        !window.location.hostname.startsWith("192.168.");

    if (!isStaticMode) {
        const storeLabel = isLiveCloud ? "Live Production Cloud" : "data/khodal_office.db";
        const pathLabel = isLiveCloud ? "Live Cloud Host" : "Local Disk (D: Drive)";
        textEl.innerHTML = `
            <div class="flex flex-wrap items-center justify-between gap-2 w-full py-0.5">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        🟢 LOCAL SAFE PLACE ACTIVE
                    </span>
                    <span class="text-xs text-emerald-950 font-semibold">
                        Permanent SQLite Database (<code>${storeLabel}</code>). Saved on hard drive — immune to browser history clears.
                    </span>
                </div>
                <div class="flex items-center gap-2 flex-wrap">
                    <button onclick="openLanDevicesModal()" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-2xs flex items-center gap-1 cursor-pointer" title="Connect Phones & Other Devices via Wi-Fi">
                        <i data-lucide="smartphone" class="w-3.5 h-3.5"></i> Connect Other Devices
                    </button>
                    <div class="text-[11px] font-mono text-emerald-800 bg-emerald-100/70 px-2.5 py-0.5 rounded font-bold hidden sm:inline-block">
                        Store: ${pathLabel}
                    </div>
                </div>
            </div>
        `;
        if (banner) {
            banner.className = "mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-xs text-emerald-900 transition shadow-2xs";
        }
        checkAndPromptBrowserSync();
    } else {
        const count = staticRecords ? staticRecords.length : 0;
        textEl.innerHTML = `
            <div class="flex flex-wrap items-center justify-between gap-2 w-full py-0.5">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        ⚠️ TEMPORARY BROWSER STORAGE (${count} records)
                    </span>
                    <span class="text-xs text-amber-950 font-medium">
                        You are viewing <strong>GitHub Pages / Static Mode</strong>. Browsers cannot write to your PC's <code>khodal_office.db</code> file from the internet! To save permanently on your PC, run <strong>START_KHODAL_OFFICE.bat</strong> and open <strong>http://localhost:8000</strong>.
                    </span>
                </div>
                <div class="flex items-center gap-2 flex-wrap">
                    <button onclick="backupDatabase()" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-2xs flex items-center gap-1 cursor-pointer" title="Download backup file to import into SQLite">
                        <i data-lucide="download" class="w-3.5 h-3.5"></i> Download Backup (.json)
                    </button>
                    <a href="http://localhost:8000" target="_blank" class="px-2.5 py-1 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold transition shadow-2xs flex items-center gap-1 cursor-pointer" title="Open Localhost Database Server">
                        <i data-lucide="external-link" class="w-3.5 h-3.5"></i> Open Localhost
                    </a>
                </div>
            </div>
        `;
        if (banner) {
            banner.className = "mb-4 p-3 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-900 transition shadow-2xs";
        }
    }
    refreshIcons();
}

function checkAndPromptBrowserSync() {
    if (document.getElementById("browser-sync-prompt-banner")) return;
    try {
        const cached = localStorage.getItem(STORAGE_KEY);
        if (!cached) return;
        const records = JSON.parse(cached);
        if (!Array.isArray(records) || records.length === 0) return;

        const statusBanner = document.getElementById("db-storage-status-banner");
        if (!statusBanner) return;

        const promptBox = document.createElement("div");
        promptBox.id = "browser-sync-prompt-banner";
        promptBox.className = "mb-4 p-3.5 rounded-xl bg-blue-50 border border-blue-300 text-xs text-blue-950 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shadow-2xs animate-slide-down";
        promptBox.innerHTML = `
            <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 font-bold">
                    <i data-lucide="cloud-download" class="w-4 h-4"></i>
                </div>
                <div>
                    <strong>Found ${records.length} records in browser storage!</strong>
                    <p class="text-blue-800 text-[11px] mt-0.5">Click "Sync to khodal_office.db" to permanently transfer them into SQLite so clearing browser history will never delete them.</p>
                </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
                <button onclick="syncBrowserRecordsToDatabase()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-2xs cursor-pointer">
                    <i data-lucide="database" class="w-3.5 h-3.5"></i> Sync to khodal_office.db
                </button>
                <button onclick="dismissBrowserSyncPrompt()" class="px-2 py-1 text-slate-500 hover:text-slate-700 text-xs font-semibold cursor-pointer">
                    Dismiss
                </button>
            </div>
        `;
        statusBanner.insertAdjacentElement("afterend", promptBox);
        refreshIcons();
    } catch (e) {}
}

function dismissBrowserSyncPrompt() {
    const el = document.getElementById("browser-sync-prompt-banner");
    if (el) el.remove();
}

async function syncBrowserRecordsToDatabase() {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (!cached) return;
    try {
        const records = JSON.parse(cached);
        if (!Array.isArray(records) || records.length === 0) return;

        showToast(`Syncing ${records.length} records into khodal_office.db...`, "info");
        const tok = getActiveSessionToken();
        const headers = { "Content-Type": "application/json" };
        if (tok) headers["X-Session-Token"] = tok;

        const res = await fetch(apiUrl("/api/records/bulk"), {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ records: records })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`Successfully saved ${data.imported || records.length} records into khodal_office.db!`, "success");
            localStorage.removeItem(STORAGE_KEY);
            dismissBrowserSyncPrompt();
            await fetchRecords(1);
            await loadDailyProgress();
        } else {
            showToast(data.detail || "Failed to sync records to database", "error");
        }
    } catch (e) {
        showToast("Error syncing to database: " + e.message, "error");
    }
}







async function backupDatabase() {







    showToast("Preparing database backup...", "info");







    if (!isStaticMode) {







        window.location.href = apiUrl("/api/database/backup");







        setTimeout(() => {







            showToast("Database backup downloaded successfully!", "success");







        }, 800);







        return;







    }







    try {







        const files = getStaticFiles();







        const payload = {







            version: "1.0",







            exported_at: new Date().toISOString(),







            total_files: files.length,







            total_records: staticRecords.length,







            files: files,







            records: staticRecords







        };







        const str = JSON.stringify(payload, null, 2);







        const blob = new Blob([str], { type: "application/json" });







        const url = URL.createObjectURL(blob);







        const a = document.createElement("a");







        const todayStr = new Date().toISOString().split("T")[0];







        a.href = url;







        a.download = `Khodal_Office_DB_Backup_${todayStr}.json`;







        document.body.appendChild(a);







        a.click();







        document.body.removeChild(a);







        URL.revokeObjectURL(url);







        showToast(`Saved backup with ${staticRecords.length} records!`, "success");







    } catch (e) {







        showToast(`Backup error: ${e.message}`, "error");







    }







}







async function handleRestoreBackupFile(event) {







    const file = event.target.files && event.target.files[0];







    if (!file) return;







    if (!confirm(`Are you sure you want to restore database from ${file.name}? This will safely update your client records.`)) {







        event.target.value = "";







        return;







    }







    showToast("Restoring database from backup file...", "info");







    if (!isStaticMode) {







        const formData = new FormData();







        formData.append("file", file);







        try {







            const resp = await fetch(apiUrl("/api/database/restore"), {







                method: "POST",







                body: formData







            });







            const data = await resp.json();







            if (resp.ok) {







                showToast(data.message || "Database restored successfully!", "success");







                await initApp();







                closeFilesModal();







            } else {







                showToast(data.detail || "Failed to restore database", "error");







            }







        } catch (e) {







            showToast(`Restore error: ${e.message}`, "error");







        }







        event.target.value = "";







        return;







    }







    const reader = new FileReader();







    reader.onload = async function(e) {







        try {







            const parsed = JSON.parse(e.target.result);







            let recs = parsed.records || [];







            let files = parsed.files || [];







            if (!recs && Array.isArray(parsed)) recs = parsed;







            if (!Array.isArray(recs) || recs.length === 0) {







                showToast("No valid records found in the backup file.", "error");







                return;







            }







            recs.forEach(r => {







                if (r.record_date) r.record_date = normalizeDateToIso(r.record_date);







            });







            staticRecords = recs;







            saveStaticRecords(staticRecords);







            saveStaticFiles(files);







            showToast(`Successfully restored ${recs.length} records and ${files.length} files!`, "success");







            await loadDailyProgress();







            await fetchRecords(1);







            renderStaticFilesList();







            updateDatabaseStatusBadge();







            closeFilesModal();







        } catch (err) {







            showToast(`Invalid backup JSON file: ${err.message}`, "error");







        }







        event.target.value = "";







    };







    reader.readAsText(file);







}







// =========================================================================







// MASTER USER AUTHENTICATION & DATABASE SESSION







// =========================================================================







let currentMasterUser = null;







async function checkAuthentication() {







    if (!isStaticMode) {







        try {







            const resp = await fetch(apiUrl("/api/auth/me"), { 



                credentials: "include",



                headers: (getActiveSessionToken() ? { "X-Session-Token": getActiveSessionToken() } : {})



            });







            if (resp.ok) {







                const data = await resp.json();







                if (data.status === "success" && data.user) {







                    currentMasterUser = data.user;







                    showAuthenticatedUI(currentMasterUser);







                    return true;







                }







            }







        } catch (e) {







            console.warn("Database auth verification failed, checking client session...", e);







        }







    }







    // Static mode or fallback session check







    try {







        const savedSession = localStorage.getItem(AUTH_SESSION_KEY) || sessionStorage.getItem(AUTH_SESSION_KEY);







        if (savedSession) {







            const user = JSON.parse(savedSession);







            if (user && user.username) {







                currentMasterUser = user;







                showAuthenticatedUI(currentMasterUser);







                return true;







            }







        }







    } catch (e) {}







    showLoginModal();







    return false;







}







function showLoginModal() {







    const modal = document.getElementById("auth-login-modal");







    if (modal) modal.classList.remove("hidden");







    const uInput = document.getElementById("login-username");







    const pInput = document.getElementById("login-password");







    if (uInput && !uInput.value) uInput.value = "manish";







    if (pInput) {







        pInput.value = "";







        setTimeout(() => pInput.focus(), 150);







    }







}







function showAuthenticatedUI(user) {







    const modal = document.getElementById("auth-login-modal");







    if (modal) modal.classList.add("hidden");







    const badge = document.getElementById("user-profile-badge");







    if (badge) badge.classList.remove("hidden");







    const nameEl = document.getElementById("user-display-name");







    if (nameEl) nameEl.textContent = user.full_name || user.username || "Master";







    const avatarEl = document.getElementById("user-avatar-initial");







    if (avatarEl) {







        const initial = (user.full_name || user.username || "M").trim().charAt(0).toUpperCase();







        avatarEl.textContent = initial;







    }







    const mobileNameEl = document.getElementById("mobile-user-display-name");

    if (mobileNameEl) mobileNameEl.textContent = user.full_name || user.username || "Master";

    const mobileAvatarEl = document.getElementById("mobile-user-avatar");

    if (mobileAvatarEl) {

        const initial = (user.full_name || user.username || "M").trim().charAt(0).toUpperCase();

        mobileAvatarEl.textContent = initial;

    }



    const roleEl = document.getElementById("user-role-badge");







    if (roleEl) {







        const role = user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : "Master";







        roleEl.textContent = role;







    }







    refreshIcons();







}











function quickFillLogin(u, p) {



    const uInput = document.getElementById("login-username");



    const pInput = document.getElementById("login-password");



    if (uInput) uInput.value = u;



    if (pInput) pInput.value = p;



    handleMasterLogin();



}







async function handleMasterLogin(e) {







    if (e) e.preventDefault();







    const uInput = document.getElementById("login-username");







    const pInput = document.getElementById("login-password");







    const errAlert = document.getElementById("login-error-alert");







    const errText = document.getElementById("login-error-text");







    const submitBtn = document.getElementById("login-submit-btn");







    const username = (uInput ? uInput.value : "").trim();







    const password = (pInput ? pInput.value : "").trim();







    if (!username || !password) {







        if (errAlert) errAlert.classList.remove("hidden");







        if (errText) errText.textContent = "Please enter both User ID and Password.";







        return;







    }







    if (submitBtn) {







        submitBtn.disabled = true;







        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-1">⌛</span> Verifying...';







    }







    let authenticated = false;







    let userInfo = null;







    if (!isStaticMode) {







        try {







            const resp = await fetch(apiUrl("/api/auth/login"), {



                method: "POST",



                headers: { "Content-Type": "application/json" },



                credentials: "include",



                body: JSON.stringify({ username, password })



            });







            const data = await resp.json().catch(() => ({}));







            if (resp.ok && data.status === "success") {







                authenticated = true;







                userInfo = data.user;



                if (data.token) {



                    try {



                        localStorage.setItem("khodal_session_token", data.token);



                        sessionStorage.setItem("khodal_session_token", data.token);



                    } catch (e) {}



                }







            } else if (resp.status === 401) {







                if (errAlert) errAlert.classList.remove("hidden");







                if (errText) errText.textContent = data.detail || "Invalid User ID or Password.";







            } else {







                throw new Error(data.detail || "Server error");







            }







        } catch (err) {







            console.warn("Backend auth unavailable, trying client-side master user verification...", err);







        }







    }







    // Static mode or fallback verification







    if (!authenticated) {







        const users = getStaticUsers();







        const cleanUser = username.toLowerCase();







        let matched = users.find(u => (u.username || "").toLowerCase() === cleanUser);







        let isValid = false;







        if (matched) {







            if (matched.password && matched.password === password) {







                isValid = true;







            } else if (cleanUser === "manish" && password === "manish@7575") {







                isValid = true;







            } else if (cleanUser === "admin" && password === "admin@7575") {







                isValid = true;







            }







        } else {







            if (cleanUser === "manish" && password === "manish@7575") {







                isValid = true;







                matched = { id: 1, username: "manish", full_name: "Manish", role: "master", is_active: 1 };







            } else if (cleanUser === "admin" && password === "admin@7575") {







                isValid = true;







                matched = { id: 2, username: "admin", full_name: "Master Admin", role: "master", is_active: 1 };







            }







        }







        if (isValid && matched) {







            authenticated = true;







            userInfo = {







                id: matched.id,







                username: matched.username,







                full_name: matched.full_name || matched.username,







                role: matched.role || "master"







            };







            matched.last_login = new Date().toISOString();







            saveStaticUsers(users);







            try {







                localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(userInfo));







                sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(userInfo));







            } catch (e) {}







        } else {







            if (errAlert) errAlert.classList.remove("hidden");







            if (errText) errText.textContent = "Invalid User ID or Password. (Master IDs: manish or admin)";







        }







    }







    if (submitBtn) {







        submitBtn.disabled = false;







        submitBtn.innerHTML = '<i data-lucide="log-in" class="w-4 h-4"></i><span>Sign In to Office Hub</span>';







        refreshIcons();







    }







    if (authenticated && userInfo) {







        if (errAlert) errAlert.classList.add("hidden");







        currentMasterUser = userInfo;







        showAuthenticatedUI(userInfo);







        showToast(`Welcome back, ${userInfo.full_name || userInfo.username}!`, "success");







        await initApp();







    }







}







async function logoutMasterUser() {







    if (!confirm("Are you sure you want to log out of Khodal Office Hub?")) return;







    if (!isStaticMode) {







        try {







            await fetch(apiUrl("/api/auth/logout"), { method: "POST", credentials: "include" });







        } catch (e) {}







    }







    currentMasterUser = null;







    try {







        localStorage.removeItem(AUTH_SESSION_KEY);







        sessionStorage.removeItem(AUTH_SESSION_KEY);







    } catch (e) {}







    showToast("Logged out successfully.", "info");







    showLoginModal();







}







function togglePasswordVisibility(inputId, iconId) {







    const input = document.getElementById(inputId);







    const icon = document.getElementById(iconId);







    if (!input) return;







    if (input.type === "password") {







        input.type = "text";







        if (icon) icon.setAttribute("data-lucide", "eye-off");







    } else {







        input.type = "password";







        if (icon) icon.setAttribute("data-lucide", "eye");







    }







    refreshIcons();







}







// =========================================================================







// MASTER USERS MANAGEMENT (Stored on SQLite Database or Client Storage)







// =========================================================================







async function openMasterUsersModal() {



    closeMobileMenu();



    const modal = document.getElementById("modal-master-users");







    if (modal) modal.classList.remove("hidden");







    await loadMasterUsersList();







}







function closeMasterUsersModal() {







    const modal = document.getElementById("modal-master-users");







    if (modal) modal.classList.add("hidden");







}







async function loadMasterUsersList() {







    const tbody = document.getElementById("master-users-list-tbody");







    const countBadge = document.getElementById("master-users-count-badge");







    if (!tbody) return;







    if (isStaticMode) {







        const users = getStaticUsers();







        if (countBadge) countBadge.textContent = `${users.length} Active in Client DB`;







        renderMasterUsersList(users);







        return;







    }







    tbody.innerHTML = `<tr><td colspan="5" class="px-4 py-6 text-center text-slate-400">Loading master users from database...</td></tr>`;







    try {







        const resp = await fetch(apiUrl("/api/users"));







        const data = await resp.json();







        if (resp.ok && data.status === "success") {







            const users = data.users || [];







            if (countBadge) countBadge.textContent = `${users.length} Active in DB`;







            renderMasterUsersList(users);







        } else {







            const users = getStaticUsers();







            renderMasterUsersList(users);







        }







    } catch (e) {







        const users = getStaticUsers();







        renderMasterUsersList(users);







    }







}







function renderMasterUsersList(users) {







    const tbody = document.getElementById("master-users-list-tbody");







    if (!tbody) return;







    if (!users || users.length === 0) {







        tbody.innerHTML = `<tr><td colspan="5" class="px-4 py-6 text-center text-slate-400">No master users found in database.</td></tr>`;







        return;







    }







    const currentUsername = currentMasterUser ? (currentMasterUser.username || "").toLowerCase() : "";







    tbody.innerHTML = users.map(u => {







        const isCurrent = (u.username || "").toLowerCase() === currentUsername;







        const initial = (u.full_name || u.username || "M").trim().charAt(0).toUpperCase();







        const lastLogin = u.last_login ? formatDateDisplay(u.last_login.substring(0, 10)) + " " + u.last_login.substring(11, 16) : "Never logged in";







        const canDelete = users.length > 1 && !isCurrent;







        return `







            <tr class="hover:bg-slate-50/80 transition">







                <td class="px-4 py-3">







                    <div class="flex items-center gap-2.5">







                        <div class="w-7 h-7 rounded-full bg-brand-600 text-white font-bold text-xs flex items-center justify-center shadow-2xs">







                            ${initial}







                        </div>







                        <div>







                            <div class="font-semibold text-slate-800 text-xs">${escapeHtml(u.full_name || u.username)}</div>







                            ${isCurrent ? '<span class="text-[10px] text-brand-600 font-semibold">(Current Active)</span>' : ''}







                        </div>







                    </div>







                </td>







                <td class="px-4 py-3 font-mono text-xs text-slate-700">







                    ${escapeHtml(u.username)}







                </td>







                <td class="px-4 py-3">







                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">







                        ${escapeHtml(u.role ? u.role.toUpperCase() : "MASTER")}







                    </span>







                </td>







                <td class="px-4 py-3 text-[11px] text-slate-500">







                    ${lastLogin}







                </td>







                <td class="px-4 py-3 text-right">







                    ${canDelete ? `







                        <button onclick="handleDeleteMasterUser(${u.id}, '${escapeHtml(u.username)}')" 







                            class="px-2 py-1 text-[11px] font-medium text-rose-600 hover:text-white hover:bg-rose-600 border border-rose-200 hover:border-rose-600 rounded transition cursor-pointer">







                            Delete







                        </button>







                    ` : `







                        <span class="text-[11px] text-slate-400 italic">${isCurrent ? 'Current User' : 'Protected'}</span>







                    `}







                </td>







            </tr>







        `;







    }).join("");







    refreshIcons();







}







async function handleAddMasterUser(e) {







    if (e) e.preventDefault();







    const fullNameInput = document.getElementById("new-user-fullname");







    const usernameInput = document.getElementById("new-user-username");







    const passwordInput = document.getElementById("new-user-password");







    const submitBtn = document.getElementById("add-user-submit-btn");







    const full_name = (fullNameInput ? fullNameInput.value : "").trim();







    const username = (usernameInput ? usernameInput.value : "").trim();







    const password = (passwordInput ? passwordInput.value : "").trim();







    if (!username || !password) {







        showToast("Please provide both Username and Password.", "error");







        return;







    }







    if (isStaticMode) {







        const users = getStaticUsers();







        if (users.some(u => (u.username || "").toLowerCase() === username.toLowerCase())) {







            showToast(`Master user '${username}' already exists!`, "error");







            return;







        }







        const nextId = users.reduce((m, u) => Math.max(m, u.id || 0), 0) + 1;







        const newUser = {







            id: nextId,







            username: username,







            full_name: full_name || username,







            role: "master",







            password: password,







            is_active: 1,







            created_at: new Date().toISOString().replace("T", " ").substring(0, 19),







            last_login: null







        };







        users.push(newUser);







        saveStaticUsers(users);







        showToast(`Master User '${username}' added successfully!`, "success");







        if (fullNameInput) fullNameInput.value = "";







        if (usernameInput) usernameInput.value = "";







        if (passwordInput) passwordInput.value = "";







        await loadMasterUsersList();







        return;







    }







    if (submitBtn) {







        submitBtn.disabled = true;







        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-1">⌛</span> Saving to Database...';







    }







    try {







        const resp = await fetch(apiUrl("/api/users"), {







            method: "POST",







            headers: { "Content-Type": "application/json" },







            body: JSON.stringify({ full_name, username, password })







        });







        const data = await resp.json();







        if (resp.ok && data.status === "success") {







            showToast(`Master User '${username}' saved directly to database!`, "success");







            if (fullNameInput) fullNameInput.value = "";







            if (usernameInput) usernameInput.value = "";







            if (passwordInput) passwordInput.value = "";







            await loadMasterUsersList();







        } else {







            showToast(data.detail || "Failed to add master user", "error");







        }







    } catch (err) {







        showToast("Failed to connect to database: " + err.message, "error");







    } finally {







        if (submitBtn) {







            submitBtn.disabled = false;







            submitBtn.innerHTML = '<i data-lucide="plus" class="w-3.5 h-3.5"></i><span>Save User to Database</span>';







            refreshIcons();







        }







    }







}







async function handleDeleteMasterUser(userId, username) {







    if (!confirm(`Are you sure you want to permanently delete master user '${username}'?`)) return;







    if (isStaticMode) {







        let users = getStaticUsers();







        if (users.length <= 1) {







            showToast("Cannot delete the only master user.", "error");







            return;







        }







        users = users.filter(u => u.id !== userId && (u.username || "").toLowerCase() !== username.toLowerCase());







        saveStaticUsers(users);







        showToast(`Master user '${username}' deleted`, "info");







        await loadMasterUsersList();







        return;







    }







    try {







        const resp = await fetch(apiUrl(`/api/users/${userId}`), { method: "DELETE" });







        const data = await resp.json();







        if (resp.ok && data.status === "success") {







            showToast(data.message || `Master user '${username}' deleted`, "info");







            await loadMasterUsersList();







        } else {







            showToast(data.detail || "Failed to delete user", "error");







        }







    } catch (err) {







        showToast("Error deleting user: " + err.message, "error");







    }







}







// Initialize application after all components and stores are defined











function openLanDevicesModal() {
    closeMobileMenu();
    openModal("modal-cloud-db");

    const statusBox = document.getElementById("cloud-db-status-box");
    const lanUrlSpan = document.getElementById("lan-modal-url");
    const lanOpenLink = document.getElementById("lan-modal-open-link");
    const input = document.getElementById("custom-cloud-url-input");
    if (input) input.value = customCloudUrl || "";

    const effectiveLanUrl = lanShareUrl || (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" ? window.location.origin : `http://${window.location.hostname || "localhost"}:8000`);

    if (lanUrlSpan) {
        lanUrlSpan.textContent = effectiveLanUrl;
    }
    if (lanOpenLink) {
        lanOpenLink.href = effectiveLanUrl;
    }

    if (statusBox) {
        if (!isStaticMode) {
            statusBox.className = "p-3 rounded-xl border border-emerald-300 bg-emerald-50 text-xs text-emerald-900";
            statusBox.innerHTML = `
                <div class="flex items-center gap-2 font-bold text-emerald-800">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>🟢 Safe Place Active: Local Hard Drive SQLite Database</span>
                </div>
                <div class="text-[11px] text-emerald-700 mt-1 font-mono">
                    File: D:\\Khodal_info\\data\\khodal_office.db
                </div>
                <div class="text-[11px] text-emerald-800 mt-1">
                    All client records and uploaded Excel sheets are permanently stored on this computer. Clearing browser history on this PC or any phone will NEVER delete your data.
                </div>
            `;
        } else {
            statusBox.className = "p-3 rounded-xl border border-amber-300 bg-amber-50 text-xs text-amber-900";
            statusBox.innerHTML = `
                <div class="flex items-center gap-2 font-bold text-amber-900">
                    <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                    <span>⚠️ Static Mode / Browser Memory (${staticRecords ? staticRecords.length : 0} records)</span>
                </div>
                <div class="text-[11px] text-amber-800 mt-1">
                    To use the permanent hard drive database, run <strong>START_KHODAL_OFFICE.bat</strong> on your computer and open <strong>http://localhost:8000</strong>.
                </div>
            `;
        }
    }

    renderLanQrCode(effectiveLanUrl);
    refreshIcons();
}

function openCloudDbModal() {
    openLanDevicesModal();
}

function renderLanQrCode(url) {
    const qrContainer = document.getElementById("lan-qr-code");
    if (!qrContainer) return;
    qrContainer.innerHTML = "";
    if (typeof QRCode !== "undefined") {
        try {
            new QRCode(qrContainer, {
                text: url,
                width: 140,
                height: 140,
                colorDark: "#0f172a",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });
            return;
        } catch (e) {
            console.warn("QRCode error:", e);
        }
    }
    qrContainer.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(url)}" alt="Scan QR Code" class="w-[140px] h-[140px] rounded-lg border border-slate-200">`;
}

function copyLanModalUrl() {
    const effectiveLanUrl = lanShareUrl || (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" ? window.location.origin : `http://${window.location.hostname || "localhost"}:8000`);
    navigator.clipboard.writeText(effectiveLanUrl).then(() => {
        showToast(`Copied Wi-Fi URL: ${effectiveLanUrl}`, "success");
    }).catch(() => {
        showToast("Could not copy link automatically", "error");
    });
}







async function saveCustomCloudUrl() {



    const input = document.getElementById("custom-cloud-url-input");



    let val = (input ? input.value : "").trim();



    if (val && !val.startsWith("http://") && !val.startsWith("https://")) {



        val = "https://" + val;



    }



    if (val.endsWith("/")) {



        val = val.slice(0, -1);



    }



    customCloudUrl = val;



    try {



        localStorage.setItem(CUSTOM_CLOUD_URL_KEY, customCloudUrl);
        saveToIndexedDB("custom_cloud_url", customCloudUrl).catch(() => {});



    } catch (e) {}



    



    if (!customCloudUrl) {



        showToast("Cleared Cloud URL. Switching to default auto-detection...", "info");



        await initDataStore();



        closeModal("modal-cloud-db");



        return;



    }







    showToast("Connecting to cloud database server...", "info");



    const ok = await detectApiBase();



    if (ok) {



        isStaticMode = false;



        showToast("🟢 Connected to Cloud Database Server successfully!", "success");



        updateDatabaseStatusBadge();



        closeModal("modal-cloud-db");



        await syncOfflineRecordsToServer();



        await loadDailyProgress();



        await fetchRecords(1);



    } else {



        showToast("⚠️ Could not connect to that server. Please verify the URL.", "error");



    }



}











async function boot() {







    refreshIcons();







    setupDropzone();







    setupWindowDragAndDrop();







    setupKeyboardListeners();







    await initDataStore();







    const isAuthed = await checkAuthentication();







    if (isAuthed) {







        await initApp();







    }







}







if (document.readyState === "loading") {







    document.addEventListener("DOMContentLoaded", boot);







} else {







    boot();







}







window.addEventListener("load", () => {







    refreshIcons();







});











// =========================================================================

// RESPONSIVE MOBILE MENU CONTROLLERS & MODAL DISMISSAL

// =========================================================================

function toggleMobileMenu() {

    const menu = document.getElementById("mobile-nav-menu");

    const toggleBtn = document.getElementById("mobile-menu-toggle-btn");

    if (!menu) return;

    const isHidden = menu.classList.contains("hidden");

    if (isHidden) {

        menu.classList.remove("hidden");

        menu.classList.add("flex");

        if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "true");

    } else {

        menu.classList.add("hidden");

        menu.classList.remove("flex");

        if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "false");

    }

    refreshIcons();

}



function closeMobileMenu() {

    const menu = document.getElementById("mobile-nav-menu");

    const toggleBtn = document.getElementById("mobile-menu-toggle-btn");

    if (menu && !menu.classList.contains("hidden")) {

        menu.classList.add("hidden");

        menu.classList.remove("flex");

        if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "false");

    }

}



document.addEventListener("click", (e) => {

    const menu = document.getElementById("mobile-nav-menu");

    const toggleBtn = document.getElementById("mobile-menu-toggle-btn");

    if (!menu || menu.classList.contains("hidden")) return;

    if (!menu.contains(e.target) && (!toggleBtn || !toggleBtn.contains(e.target))) {

        closeMobileMenu();

    }

});



// Escape key to close mobile menu & modals

document.addEventListener("keydown", (e) => {

    if (e.key === "Escape") {

        closeMobileMenu();

        const openModals = [

            "modal-upload",

            "modal-record-form",

            "modal-view-record",

            "modal-files",

            "modal-master-users",

            "modal-cloud-db"

        ];

        openModals.forEach((id) => {

            closeModal(id);

        });

    }

});



// Setup modal backdrop click dismissal

window.addEventListener("DOMContentLoaded", () => {

    const modalIds = [

        "modal-upload",

        "modal-record-form",

        "modal-view-record",

        "modal-files",

        "modal-master-users",

        "modal-cloud-db"

    ];

    modalIds.forEach((id) => {

        const modal = document.getElementById(id);

        if (modal) {

            modal.addEventListener("click", (e) => {

                if (e.target === modal) {

                    closeModal(id);

                }

            });

        }

    });

    updateViewModeUI();

});

