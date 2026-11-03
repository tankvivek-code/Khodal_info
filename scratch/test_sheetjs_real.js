const XLSX = require('xlsx');
const fs = require('fs');

const files = [
    'uploads/UC_Aadhaar_Daily.csv',
    'uploads/Aadhaar_Online_Daily.csv',
    'uploads/PAN_Card_Daily.csv',
    'uploads/Ayushman_Card_Daily.csv',
    'uploads/Khodal_Office_Master.xlsx'
];

files.forEach(f => {
    if (!fs.existsSync(f)) {
        console.log("File not found:", f);
        return;
    }
    const buf = fs.readFileSync(f);
    const wb = XLSX.read(buf, { type: 'buffer' });
    console.log(`\n========================================`);
    console.log(`File: ${f} | Sheets: ${wb.SheetNames.join(', ')}`);
    
    let totalParsed = 0;
    wb.SheetNames.forEach(sName => {
        const sheet = wb.Sheets[sName];
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });
        console.log(`  Sheet: ${sName} -> Raw rows: ${rows.length}`);
        if (rows.length > 0) {
            console.log(`    Header: ${JSON.stringify(rows[0])}`);
            if (rows.length > 1) {
                console.log(`    Row 1: ${JSON.stringify(rows[1])}`);
            }
        }
    });
});

