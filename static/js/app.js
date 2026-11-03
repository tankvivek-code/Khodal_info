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

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupDropzone();
    setupKeyboardListeners();
});

// =========================================================================
// HYBRID DATA STORE (Seamless GitHub Pages & Static Mode Support)
// =========================================================================
let isStaticMode = window.location.hostname.includes("github.io") || window.location.protocol === "file:";
let staticRecords = [];
const STORAGE_KEY = "khodal_records_store_v1";

async function initDataStore() {
    if (!isStaticMode) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 1200);
            const test = await fetch("/api/info", { signal: controller.signal });
            clearTimeout(timeoutId);
            if (!test.ok) isStaticMode = true;
        } catch (e) {
            isStaticMode = true;
        }
    }

    if (isStaticMode) {
        console.log("⚡ Khodal Office Hub running in Client-Side / GitHub Pages Mode");
        const cached = localStorage.getItem(STORAGE_KEY);
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    staticRecords = parsed;
                }
            } catch (e) {}
        }
        if (!staticRecords || staticRecords.length === 0) {
            if (window.KHODAL_RECORDS && Array.isArray(window.KHODAL_RECORDS) && window.KHODAL_RECORDS.length > 0) {
                staticRecords = window.KHODAL_RECORDS.slice();
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
                } catch (e) {}
            } else {
                try {
                    const res = await fetch("data/records.json?v=" + Date.now());
                    if (res.ok) {
                        staticRecords = await res.json();
                        try {
                            localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
                        } catch (e) {}
                    }
                } catch (err) {
                    console.warn("Could not load data/records.json", err);
                }
            }
        }
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
    if (window.lucide) {
        lucide.createIcons();
    }
}

// =========================================================================
// API & DATA LOADERS
// =========================================================================

async function fetchSystemInfo() {
    if (isStaticMode) {
        lanShareUrl = window.location.href;
        const displayEl = document.getElementById("lan-url-display");
        if (displayEl) {
            displayEl.textContent = window.location.hostname.includes("github.io") ? "Live on GitHub Pages" : "Client-Side Mode";
        }
        const shareBox = document.getElementById("lan-share-box");
        if (shareBox) shareBox.classList.remove("hidden");
        return;
    }
    try {
        const res = await fetch("/api/info");
        const data = await res.json();
        if (data && data.office_share_url) {
            lanShareUrl = data.office_share_url;
            const displayEl = document.getElementById("lan-url-display");
            if (displayEl) displayEl.textContent = data.office_share_url.replace("http://", "");
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
        let baki = 0;
        let fee = 0.0;

        records.forEach(r => {
            const st = (r.status || "").toLowerCase();
            if (st === "completed" || st === "complete" || st === "done") completed++;
            else inProcess++;

            if (r.is_baki === 1 || (r.remark || "").toUpperCase().includes("BAKI")) baki++;
            fee += Number(r.fee_amt || 0);
        });

        const completionRate = total > 0 ? Math.round((completed / total) * 1000) / 10 : 0.0;

        document.getElementById("stat-progress-total").textContent = total.toLocaleString();
        document.getElementById("stat-progress-completed").textContent = completed.toLocaleString();
        document.getElementById("stat-progress-inprocess").textContent = inProcess.toLocaleString();
        document.getElementById("stat-progress-baki").textContent = baki.toLocaleString();
        document.getElementById("stat-progress-fees").textContent = fee.toLocaleString();
        document.getElementById("stat-progress-rate").textContent = `${completionRate}%`;
        document.getElementById("stat-progress-date-pill").textContent = currentDateFilter || "All";

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

        const res = await fetch(`/api/progress?${queryStr.toString()}`);
        const data = await res.json();

        // Update Stat Cards
        document.getElementById("stat-progress-total").textContent = (data.total_applications || 0).toLocaleString();
        document.getElementById("stat-progress-completed").textContent = (data.completed || 0).toLocaleString();
        document.getElementById("stat-progress-inprocess").textContent = (data.in_process || 0).toLocaleString();
        document.getElementById("stat-progress-baki").textContent = (data.baki_pending || 0).toLocaleString();
        document.getElementById("stat-progress-fees").textContent = (data.total_fee || 0).toLocaleString();
        document.getElementById("stat-progress-rate").textContent = `${data.completion_rate || 0}%`;

        document.getElementById("stat-progress-date-pill").textContent = currentDateFilter || "All";

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
    const currentVal = select.value;
    select.innerHTML = '<option value="">All Dates (Overview)</option>';

    availableDates.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = `📅 ${d}`;
        select.appendChild(opt);
    });

    if (currentVal && availableDates.includes(currentVal)) {
        select.value = currentVal;
    }
}

function getSearchParams() {
    return {
        service_type: currentServiceTab,
        name: document.getElementById("search-name").value.trim(),
        mobile: document.getElementById("search-mobile").value.trim(),
        id_number: document.getElementById("search-id").value.trim(),
        date: currentDateFilter,
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
            filtered = filtered.filter(r => (r.record_date || "").startsWith(params.date));
        }
        if (params.name) {
            const q = params.name.toLowerCase();
            filtered = filtered.filter(r => (r.name || "").toLowerCase().includes(q));
        }
        if (params.mobile) {
            const mobClean = params.mobile.replace(/\D/g, "");
            filtered = filtered.filter(r => (r.mobile || "").includes(params.mobile) || (r.normalized_mobile || "").includes(mobClean));
        }
        if (params.id_number) {
            const q = params.id_number.toLowerCase();
            filtered = filtered.filter(r => (r.id_number || "").toLowerCase().includes(q));
        }
        if (params.status && params.status !== "all") {
            filtered = filtered.filter(r => (r.status || "").toLowerCase() === params.status.toLowerCase());
        }
        if (params.baki_only) {
            filtered = filtered.filter(r => r.is_baki === 1 || (r.remark || "").toUpperCase().includes("BAKI"));
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
        const res = await fetch(`/api/records?${queryStr.toString()}`);
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
                <th class="py-3 px-3 w-10 text-center">#</th>
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">SID Number</th>
                <th class="py-3 px-3">Name</th>
                <th class="py-3 px-3 text-center">Status</th>
                <th class="py-3 px-3 text-right">Total (₹)</th>
                <th class="py-3 px-3 text-right">Fee (₹)</th>
                <th class="py-3 px-3">Mobile / Others</th>
                <th class="py-3 px-3">Remarks</th>
                <th class="py-3 px-3 text-center w-28">Actions</th>
            </tr>
        `;
    } else if (serviceType === "aadhar_online") {
        trHtml = `
            <tr>
                <th class="py-3 px-3 w-10 text-center">#</th>
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Name</th>
                <th class="py-3 px-3">SRN Number</th>
                <th class="py-3 px-3">Mobile No</th>
                <th class="py-3 px-3">Remarks</th>
                <th class="py-3 px-3 text-center">Status</th>
                <th class="py-3 px-3 text-center w-28">Actions</th>
            </tr>
        `;
    } else if (serviceType === "pancard") {
        trHtml = `
            <tr>
                <th class="py-3 px-3 w-10 text-center">#</th>
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Name</th>
                <th class="py-3 px-3">PAN Change / New</th>
                <th class="py-3 px-3">Mobile Number</th>
                <th class="py-3 px-3">Remarks</th>
                <th class="py-3 px-3 text-center">Status</th>
                <th class="py-3 px-3 text-center w-28">Actions</th>
            </tr>
        `;
    } else if (serviceType === "aayushman") {
        trHtml = `
            <tr>
                <th class="py-3 px-3 w-10 text-center">#</th>
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Ration / Ayushman No</th>
                <th class="py-3 px-3">Name</th>
                <th class="py-3 px-3">Mobile No</th>
                <th class="py-3 px-3">Remarks</th>
                <th class="py-3 px-3 text-center">Status</th>
                <th class="py-3 px-3 text-center w-28">Actions</th>
            </tr>
        `;
    } else {
        // All Services
        trHtml = `
            <tr>
                <th class="py-3 px-3 w-10 text-center">#</th>
                <th class="py-3 px-3">Service</th>
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Name</th>
                <th class="py-3 px-3">SID / SRN / Card No</th>
                <th class="py-3 px-3">Mobile No</th>
                <th class="py-3 px-3 text-center">Status / Type</th>
                <th class="py-3 px-3 text-right">Fee</th>
                <th class="py-3 px-3">Remarks</th>
                <th class="py-3 px-3 text-center w-28">Actions</th>
            </tr>
        `;
    }
    thead.innerHTML = trHtml;
}

function renderRecordsTable(records, serviceType) {
    const tbody = document.getElementById("records-table-body");
    const emptyState = document.getElementById("table-empty-state");

    tbody.innerHTML = "";

    if (!records || records.length === 0) {
        emptyState.classList.remove("hidden");
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

        // Status Badge & Quick Toggle
        const statusBadge = renderStatusBadge(r);

        // Service Badge for All Services tab
        const svcBadge = renderServiceBadge(r.service_type);

        let rowHtml = "";

        if (serviceType === "ucaadhar") {
            rowHtml = `
                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>
                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(r.record_date)}</td>
                <td class="py-3 px-3 font-mono text-xs font-semibold text-brand-700 max-w-[200px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>
                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[190px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>
                <td class="py-3 px-3 text-center">${statusBadge}</td>
                <td class="py-3 px-3 text-xs text-right font-mono text-slate-600">${r.total_amt > 0 ? '₹' + r.total_amt : '-'}</td>
                <td class="py-3 px-3 text-xs text-right font-mono font-bold text-emerald-700">${r.fee_amt > 0 ? '₹' + r.fee_amt : '-'}</td>
                <td class="py-3 px-3">
                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">
                        ${r.mobile ? `<span>${hlMobile}</span>` : `<span class="text-slate-400 font-normal">-</span>`}
                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}
                    </div>
                </td>
                <td class="py-3 px-3 text-xs text-slate-600 max-w-[160px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>
                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>
            `;
        } else if (serviceType === "aadhar_online") {
            rowHtml = `
                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>
                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(r.record_date)}</td>
                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>
                <td class="py-3 px-3 font-mono text-xs font-bold text-indigo-700 max-w-[170px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>
                <td class="py-3 px-3">
                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">
                        <span>${hlMobile}</span>
                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}
                    </div>
                </td>
                <td class="py-3 px-3 text-xs text-slate-700 max-w-[180px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>
                <td class="py-3 px-3 text-center">${statusBadge}</td>
                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>
            `;
        } else if (serviceType === "pancard") {
            rowHtml = `
                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>
                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(r.record_date)}</td>
                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>
                <td class="py-3 px-3 text-xs font-bold ${(r.pan_type || '').includes('NEW') ? 'text-blue-700' : 'text-amber-700'}">${escapeHtml(r.pan_type || '-')}</td>
                <td class="py-3 px-3">
                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">
                        <span>${hlMobile}</span>
                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}
                    </div>
                </td>
                <td class="py-3 px-3 text-xs text-slate-600">${renderRemarkWithBaki(r.remark)}</td>
                <td class="py-3 px-3 text-center">${statusBadge}</td>
                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>
            `;
        } else if (serviceType === "aayushman") {
            rowHtml = `
                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>
                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(r.record_date)}</td>
                <td class="py-3 px-3 font-mono text-xs font-bold text-purple-700 max-w-[170px] truncate" title="${escapeHtml(r.id_number)}">${hlId}</td>
                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[200px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>
                <td class="py-3 px-3">
                    <div class="flex items-center gap-1.5 font-mono text-xs font-semibold text-slate-800">
                        <span>${hlMobile}</span>
                        ${waUrl ? `<a href="${waUrl}" target="_blank" class="p-0.5 rounded text-emerald-600 hover:bg-emerald-50"><i data-lucide="message-circle" class="w-3.5 h-3.5"></i></a>` : ""}
                    </div>
                </td>
                <td class="py-3 px-3 text-xs text-slate-600 max-w-[180px] truncate" title="${escapeHtml(r.remark)}">${renderRemarkWithBaki(r.remark)}</td>
                <td class="py-3 px-3 text-center">${statusBadge}</td>
                <td class="py-3 px-3 text-center">${renderActions(r, waUrl, callUrl)}</td>
            `;
        } else {
            // All Services
            rowHtml = `
                <td class="py-3 px-3 text-center text-xs font-mono text-slate-400 font-medium">${globalIdx}</td>
                <td class="py-3 px-3">${svcBadge}</td>
                <td class="py-3 px-3 text-xs font-mono font-medium text-slate-700 whitespace-nowrap">${escapeHtml(r.record_date)}</td>
                <td class="py-3 px-3 text-sm font-semibold text-slate-900 truncate max-w-[180px] cursor-pointer hover:text-brand-600" onclick="viewRecordDetails(${r.id})">${hlName}</td>
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

    refreshIcons();
}

function renderStatusBadge(r) {
    const isComp = (r.status || "").toLowerCase().includes("complete") || (r.status || "").toLowerCase().includes("ok");
    const label = r.status || (r.pan_type ? r.pan_type : "InProcess");

    if (isComp) {
        return `<button onclick="toggleRecordStatus(${r.id}, 'InProcess')" title="Click to mark InProcess" class="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 hover:bg-emerald-200 transition">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Completed
        </button>`;
    } else {
        return `<button onclick="toggleRecordStatus(${r.id}, 'Completed')" title="Click to mark Completed" class="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 hover:bg-amber-200 transition">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> ${escapeHtml(label)}
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
            <button onclick="copyRecordCard(${r.id})" title="Copy Summary" class="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100">
                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
            </button>
            <button onclick="viewRecordDetails(${r.id})" title="View Details" class="p-1 rounded text-brand-600 hover:text-brand-800 hover:bg-brand-50">
                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
            </button>
            <button onclick="openEditRecordModal(${r.id})" title="Edit" class="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100">
                <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
            </button>
            <button onclick="deleteRecordAction(${r.id})" title="Delete" class="p-1 rounded text-rose-500 hover:text-rose-700 hover:bg-rose-50">
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

function onDateSelectorChange(val) {
    currentDateFilter = val;
    loadDailyProgress();
    fetchRecords(1);
}

function setTodayDate() {
    const today = new Date().toISOString().split("T")[0];
    currentDateFilter = today;
    document.getElementById("quick-date-selector").value = today;
    loadDailyProgress();
    fetchRecords(1);
}

function resetDateFilter() {
    currentDateFilter = "";
    document.getElementById("quick-date-selector").value = "";
    loadDailyProgress();
    fetchRecords(1);
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
    document.getElementById("filter-status").value = "all";
    currentStatusFilter = "all";
    isBakiOnly = false;
    currentDateFilter = "";
    document.getElementById("quick-date-selector").value = "";

    const badge = document.getElementById("baki-active-badge");
    badge.textContent = "pending";
    badge.classList.remove("bg-rose-600", "text-white");

    toggleClearButton("search-name", "clear-name");
    toggleClearButton("search-mobile", "clear-mobile");
    toggleClearButton("search-id", "clear-id");

    loadDailyProgress();
    fetchRecords(1);
    showToast("Filters reset", "info");
}

// =========================================================================
// STATUS TOGGLE & CRUD
// =========================================================================

async function toggleRecordStatus(recordId, newStatus) {
    if (isStaticMode) {
        const rec = staticRecords.find(r => r.id === recordId);
        if (rec) {
            rec.status = newStatus;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
            showToast(`Status updated to ${newStatus}`, "success");
            await loadDailyProgress();
            await fetchRecords(currentPage);
        }
        return;
    }

    try {
        const res = await fetch(`/api/records/${recordId}/status`, {
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
    document.getElementById("view-date").textContent = record.record_date || "-";
    document.getElementById("view-id-num").textContent = record.id_number || "-";
    document.getElementById("view-mobile").textContent = record.mobile || "-";
    document.getElementById("view-status").textContent = record.status || (record.pan_type || "InProcess");
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
    text += `📅 Date: ${r.record_date || '-'}\n`;
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

function openAddRecordModal() {
    document.getElementById("record-form-title").textContent = "New Office Entry";
    document.getElementById("form-record-id").value = "";
    document.getElementById("record-form").reset();
    document.getElementById("form-date").value = currentDateFilter || new Date().toISOString().split("T")[0];
    document.getElementById("form-service-type").value = currentServiceTab !== "all" ? currentServiceTab : "ucaadhar";
    openModal("modal-record-form");
}

function openEditRecordModal(recordId) {
    const r = currentRecords.find(item => item.id === recordId);
    if (!r) return;

    document.getElementById("record-form-title").textContent = "Edit Office Entry";
    document.getElementById("form-record-id").value = r.id;
    document.getElementById("form-service-type").value = r.service_type || "ucaadhar";
    document.getElementById("form-date").value = r.record_date || "";
    document.getElementById("form-name").value = r.name || "";
    document.getElementById("form-mobile").value = r.mobile || "";
    document.getElementById("form-id-number").value = r.id_number || "";
    document.getElementById("form-status").value = r.status || "Completed";
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

    const payload = {
        service_type: document.getElementById("form-service-type").value,
        record_date: document.getElementById("form-date").value,
        name: document.getElementById("form-name").value.trim(),
        mobile: document.getElementById("form-mobile").value.trim(),
        id_number: document.getElementById("form-id-number").value.trim(),
        status: document.getElementById("form-status").value,
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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
        showToast(isEdit ? "Record updated" : "Entry added successfully", "success");
        closeModal("modal-record-form");
        await loadDailyProgress();
        await fetchRecords(currentPage);
        return;
    }

    try {
        const url = isEdit ? `/api/records/${recordId}` : "/api/records";
        const method = isEdit ? "PUT" : "POST";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
        showToast("Record deleted", "info");
        await loadDailyProgress();
        await fetchRecords(currentPage);
        return;
    }

    try {
        const res = await fetch(`/api/records/${recordId}`, { method: "DELETE" });
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
                const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
                const jsonRows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
                let imported = 0;
                let lastDate = new Date().toISOString().split("T")[0];

                jsonRows.forEach(row => {
                    if (!row || row.length === 0) return;
                    row.forEach(cell => {
                        const c = String(cell).trim();
                        if (/^\d{4}-\d{2}-\d{2}$/.test(c) || /^\d{2}\/\d{2}\/\d{4}$/.test(c)) {
                            lastDate = c;
                        }
                    });

                    const name = String(row[1] || row[0] || "").trim();
                    if (name && !name.toLowerCase().includes("name") && !name.toLowerCase().includes("total") && !name.toLowerCase().includes("sr no")) {
                        const nextId = staticRecords.reduce((max, r) => Math.max(max, r.id || 0), 0) + 1;
                        const mob = String(row[3] || row[4] || "").replace(/\.0$/, "").trim();
                        const idNum = String(row[2] || "").trim();
                        const remark = String(row[5] || row[6] || "").trim();
                        staticRecords.unshift({
                            id: nextId,
                            service_type: svcType !== "auto" ? svcType : "ucaadhar",
                            record_date: lastDate,
                            name: name,
                            mobile: mob,
                            normalized_mobile: mob.replace(/\D/g, "").slice(-10),
                            id_number: idNum,
                            pan_type: "",
                            status: "InProcess",
                            fee_amt: parseFloat(row[4]) || 0.0,
                            total_amt: parseFloat(row[4]) || 0.0,
                            remark: remark,
                            is_baki: remark.toUpperCase().includes("BAKI") ? 1 : 0
                        });
                        imported++;
                    }
                });

                localStorage.setItem(STORAGE_KEY, JSON.stringify(staticRecords));
                showToast(`Successfully imported ${imported} records!`, "success");
                closeModal("modal-upload");
                selectedUploadFile = null;
                document.getElementById("file-input").value = "";
                document.getElementById("selected-file-name").classList.add("hidden");
                await loadDailyProgress();
                await fetchRecords(1);
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

    try {
        const res = await fetch("/api/upload", {
            method: "POST",
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
}

async function openFilesModal() {
    openModal("modal-files");
    const container = document.getElementById("files-list-container");
    container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Loading files...</div>';

    if (isStaticMode) {
        container.innerHTML = `
            <div class="space-y-2">
                <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center justify-between">
                    <span>📁 <strong>Demo 1: UC Aadhaar</strong> (380 preloaded records)</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-emerald-200 font-bold">Active</span>
                </div>
                <div class="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800 flex items-center justify-between">
                    <span>📁 <strong>Demo 2: Aadhaar Online</strong> (147 preloaded records)</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-blue-200 font-bold">Active</span>
                </div>
                <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-center justify-between">
                    <span>📁 <strong>Demo 3: PAN Card</strong> (41 preloaded records)</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-amber-200 font-bold">Active</span>
                </div>
                <div class="p-3 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-800 flex items-center justify-between">
                    <span>📁 <strong>Demo 4: Ayushman Card</strong> (49 preloaded records)</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-purple-200 font-bold">Active</span>
                </div>
            </div>
        `;
        return;
    }

    try {
        const res = await fetch("/api/files");
        const files = await res.json();

        if (!files || files.length === 0) {
            container.innerHTML = `<div class="text-center py-8 text-xs text-slate-500">No Excel or CSV files uploaded yet.</div>`;
            return;
        }

        container.innerHTML = "";
        files.forEach(f => {
            const card = document.createElement("div");
            card.className = "flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200 hover:border-brand-300 transition";

            card.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                        <i data-lucide="file-spreadsheet" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h4 class="text-xs font-bold text-slate-900 truncate max-w-xs">${escapeHtml(f.filename)}</h4>
                        <div class="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                            <span class="font-bold text-brand-700 uppercase">${escapeHtml(f.service_type || 'General')}</span>
                            <span>•</span>
                            <span class="font-semibold text-slate-700">${f.row_count.toLocaleString()} rows</span>
                            <span>•</span>
                            <span>${(f.file_size / 1024).toFixed(1)} KB</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/api/files/${f.id}/download" download class="p-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition">
                        <i data-lucide="download" class="w-3.5 h-3.5"></i>
                        <span class="hidden sm:inline">Download</span>
                    </a>
                    <button onclick="confirmDeleteFile(${f.id}, '${escapeHtml(f.filename)}')" class="p-2 bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200 rounded-lg text-xs font-semibold transition">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
        refreshIcons();
    } catch (err) {
        container.innerHTML = '<div class="text-rose-500 text-xs py-4">Failed to load files</div>';
    }
}

async function confirmDeleteFile(fileId, filename) {
    if (!confirm(`Delete '${filename}' and all its imported records?`)) return;

    try {
        const res = await fetch(`/api/files/${fileId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete file");

        showToast(`Deleted ${filename}`, "info");
        await loadDailyProgress();
        await openFilesModal();
        await fetchRecords(1);
    } catch (err) {
        showToast(err.message, "error");
    }
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
            records = records.filter(r => (r.record_date || "").startsWith(params.date));
        }

        if (format === "excel" && window.XLSX) {
            const wsData = records.map((r, i) => ({
                "Sr No": i + 1,
                "Service": (r.service_type || "").toUpperCase(),
                "Date": r.record_date || "",
                "Name": r.name || "",
                "ID Number": r.id_number || "",
                "Mobile No": r.mobile || "",
                "Status": r.status || "",
                "Amount": r.fee_amt || 0,
                "Remarks": r.remark || ""
            }));
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.json_to_sheet(wsData);
            XLSX.utils.book_append_sheet(wb, ws, "Records");
            XLSX.writeFile(wb, `Khodal_${params.service_type || "ALL"}_Export.xlsx`);
            showToast("Excel exported successfully!", "success");
            return;
        }

        // CSV export
        let csv = "Sr No,Service,Date,Name,ID Number,Mobile No,Status,Amount,Remarks\n";
        records.forEach((r, idx) => {
            const row = [
                idx + 1,
                `"${(r.service_type || '').toUpperCase()}"`,
                `"${r.record_date || ''}"`,
                `"${(r.name || '').replace(/"/g, '""')}"`,
                `"${r.id_number || ''}"`,
                `"${r.mobile || ''}"`,
                `"${r.status || ''}"`,
                r.fee_amt || 0,
                `"${(r.remark || '').replace(/"/g, '""')}"`
            ];
            csv += row.join(",") + "\n";
        });
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
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

    const endpoint = format === "excel" ? "/api/export" : "/api/export/csv";
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
    openModal("modal-upload");
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
