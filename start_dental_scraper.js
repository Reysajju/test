// start_dental_scraper.js - Multi-Zone Master Orchestrator for Dental Clinic Lead Mining
// Runs 4 concurrent workers (Eastern, Central, Mountain, Pacific) with self-healing Watchdog
// and continuous real-time Excel & CSV aggregation into "Sajjad data"

import { spawn, execSync } from 'node:child_process';
import fs from 'node:fs/promises';
import { existsSync, createWriteStream, readFileSync } from 'node:fs';
import path from 'node:path';
import ExcelJS from 'exceljs';

const ZONES = ['eastern', 'central', 'mountain', 'pacific'];
const SAJJAD_DATA_DIR = path.resolve('Sajjad data');
const CHECKPOINTS_DIR = path.join(SAJJAD_DATA_DIR, 'zone_checkpoints');
const MASTER_CSV = path.join(SAJJAD_DATA_DIR, 'Dental_Clinics_US_CA_Master.csv');
const MASTER_XLSX = path.join(SAJJAD_DATA_DIR, 'Dental_Clinics_US_CA_Master.xlsx');
const USA_DIR = path.join(SAJJAD_DATA_DIR, 'by_country_and_state', 'USA');
const CANADA_DIR = path.join(SAJJAD_DATA_DIR, 'by_country_and_state', 'Canada');

const HEADERS = [
  { header: 'Business Name', key: 'name', width: 34 },
  { header: 'Phone Number', key: 'phone', width: 18 },
  { header: 'Category', key: 'category', width: 24 },
  { header: 'Address', key: 'address', width: 44 },
  { header: 'City', key: 'city', width: 20 },
  { header: 'State / Province', key: 'state', width: 16 },
  { header: 'Country', key: 'country', width: 10 },
  { header: 'Rating', key: 'rating', width: 10 },
  { header: 'Total Reviews', key: 'reviews', width: 14 },
  { header: 'Business Hours', key: 'hours', width: 45 },
  { header: 'Website Status', key: 'websiteStatus', width: 16 },
  { header: 'Google Maps Link', key: 'url', width: 48 },
  { header: 'Scraped At', key: 'scrapedAt', width: 22 }
];

const workers = new Map();
let stopping = false;
let isAggregating = false;

// ---------------------------------------------------------------- WORKER LIFECYCLE
function launchWorker(zone) {
  if (stopping) return;
  if (workers.has(zone)) {
    const existing = workers.get(zone);
    if (existing && existing.process && !existing.process.killed) return;
  }

  const logFile = path.join(CHECKPOINTS_DIR, `${zone}_worker.log`);
  const logStream = createWriteStream(logFile, { flags: 'a' });

  console.log(`[ORCHESTRATOR] 🚀 Starting worker for ${zone.toUpperCase()} zone...`);
  const child = spawn(process.execPath, ['--max-old-space-size=512', 'dental_worker.js', '--zone', zone], {
    cwd: process.cwd(),
    env: { ...process.env, NODE_ENV: 'production' },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  const workerInfo = { process: child, startedAt: Date.now(), lastActivity: Date.now() };
  workers.set(zone, workerInfo);

  child.stdout.on('data', (d) => {
    workerInfo.lastActivity = Date.now();
    const text = d.toString();
    logStream.write(text);
    if (text.includes('★') || text.includes('candidate(s)') || text.includes('Target Matrix')) {
      process.stdout.write(text);
    }
  });

  child.stderr.on('data', (d) => {
    workerInfo.lastActivity = Date.now();
    const text = d.toString();
    logStream.write(`[ERR] ${text}`);
    if (!text.includes('DevTools') && !text.includes('Fontconfig')) {
      process.stderr.write(`[${zone.toUpperCase()} ERR] ${text}`);
    }
  });

  child.on('exit', (code, signal) => {
    logStream.end();
    const current = workers.get(zone);
    const isCurrent = current && current.process.pid === child.pid;
    if (isCurrent) workers.delete(zone);

    try {
      if (child.pid) {
        if (process.platform === 'win32') {
          import('node:child_process').then(cp => {
            cp.exec(`taskkill /pid ${child.pid} /T /F`, () => {});
          });
        } else {
          child.kill('SIGKILL');
        }
      }
    } catch {}

    if (!stopping && isCurrent) {
      console.log(`[ORCHESTRATOR] 🔄 Worker ${zone.toUpperCase()} exited (code: ${code}). Auto-restarting in 4s...`);
      setTimeout(() => launchWorker(zone), 4000);
    }
  });
}

// ---------------------------------------------------------------- WATCHDOG
setInterval(() => {
  if (stopping) return;
  const now = Date.now();
  for (const [zone, item] of workers.entries()) {
    const idleMs = now - (item.lastActivity || item.startedAt);
    if (idleMs > 150000) { // 2.5 minutes inactivity
      console.log(`\n[WATCHDOG] ⚠️ Worker ${zone.toUpperCase()} idle for ${Math.round(idleMs / 1000)}s. Force-restarting...`);
      try {
        if (process.platform === 'win32') {
          execSync(`taskkill /pid ${item.process.pid} /T /F`, { stdio: 'ignore' });
        } else {
          item.process.kill('SIGKILL');
        }
      } catch {
        try { item.process.kill('SIGKILL'); } catch {}
      }
    }
  }
}, 30000);

// ---------------------------------------------------------------- MASTER AGGREGATION
function parseCsvLine(line) {
  const result = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(cur);
      cur = '';
    } else {
      cur += char;
    }
  }
  result.push(cur);
  return result;
}

async function aggregateData() {
  if (isAggregating) return;
  isAggregating = true;

  try {
    const allLeadsMap = new Map();
    let totalRead = 0;

    for (const z of ZONES) {
      const csvPath = path.join(CHECKPOINTS_DIR, `zone_${z}.csv`);
      if (existsSync(csvPath)) {
        try {
          const lines = readFileSync(csvPath, 'utf8').split('\n');
          for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            const cols = parseCsvLine(line);
            if (cols.length >= 7) {
              const lead = {
                name: cols[0],
                phone: cols[1],
                category: cols[2],
                address: cols[3],
                city: cols[4],
                state: cols[5],
                country: cols[6],
                rating: cols[7] || '',
                reviews: cols[8] || '',
                hours: cols[9] || '',
                websiteStatus: cols[10] || 'No Website',
                url: cols[11] || '',
                scrapedAt: cols[12] || ''
              };
              const key = lead.phone.replace(/\D/g, '') || lead.address.toLowerCase().trim();
              if (key && !allLeadsMap.has(key)) {
                allLeadsMap.set(key, lead);
                totalRead++;
              }
            }
          }
        } catch {}
      }
    }

    if (totalRead === 0) {
      isAggregating = false;
      return;
    }

    const allLeads = Array.from(allLeadsMap.values());
    const usaLeads = allLeads.filter(l => l.country === 'US');
    const canadaLeads = allLeads.filter(l => l.country === 'CA');

    // 1. Write Master CSV
    const csvHeaderRow = HEADERS.map(h => `"${h.header}"`).join(',') + '\n';
    const csvRows = allLeads.map(l => [
      `"${(l.name || '').replace(/"/g, '""')}"`,
      `"${(l.phone || '').replace(/"/g, '""')}"`,
      `"${(l.category || '').replace(/"/g, '""')}"`,
      `"${(l.address || '').replace(/"/g, '""')}"`,
      `"${(l.city || '').replace(/"/g, '""')}"`,
      `"${(l.state || '').replace(/"/g, '""')}"`,
      `"${(l.country || '').replace(/"/g, '""')}"`,
      `"${(l.rating || '').replace(/"/g, '""')}"`,
      `"${(l.reviews || '').replace(/"/g, '""')}"`,
      `"${(l.hours || '').replace(/"/g, '""')}"`,
      `"${(l.websiteStatus || '').replace(/"/g, '""')}"`,
      `"${(l.url || '').replace(/"/g, '""')}"`,
      `"${(l.scrapedAt || '').replace(/"/g, '""')}"`
    ].join(',')).join('\n') + '\n';

    await fs.writeFile(MASTER_CSV, csvHeaderRow + csvRows, 'utf8');

    // 2. Build Master Excel Workbook with Multiple Worksheets
    const wb = new ExcelJS.Workbook();
    wb.creator = 'Sajjad Dental Scraper';

    // Worksheet 1: All Leads
    const wsAll = wb.addWorksheet('All Dental Leads');
    wsAll.columns = HEADERS;
    wsAll.getRow(1).font = { bold: true };
    wsAll.views = [{ state: 'frozen', ySplit: 1 }];
    allLeads.forEach(lead => wsAll.addRow(lead));

    // Worksheet 2: USA Clinics
    const wsUSA = wb.addWorksheet('USA Clinics');
    wsUSA.columns = HEADERS;
    wsUSA.getRow(1).font = { bold: true };
    wsUSA.views = [{ state: 'frozen', ySplit: 1 }];
    usaLeads.forEach(lead => wsUSA.addRow(lead));

    // Worksheet 3: Canada Clinics
    const wsCA = wb.addWorksheet('Canada Clinics');
    wsCA.columns = HEADERS;
    wsCA.getRow(1).font = { bold: true };
    wsCA.views = [{ state: 'frozen', ySplit: 1 }];
    canadaLeads.forEach(lead => wsCA.addRow(lead));

    // Worksheet 4: Summary by City
    const cityMap = {};
    for (const lead of allLeads) {
      const cityKey = `${lead.city || 'Unknown'}, ${lead.state || 'N/A'} (${lead.country})`;
      cityMap[cityKey] = (cityMap[cityKey] || 0) + 1;
    }
    const wsSummary = wb.addWorksheet('City & State Summary');
    wsSummary.columns = [
      { header: 'City & State / Province', key: 'location', width: 35 },
      { header: 'Total Verified Leads', key: 'count', width: 22 },
      { header: 'Status', key: 'status', width: 20 }
    ];
    wsSummary.getRow(1).font = { bold: true };
    for (const [loc, count] of Object.entries(cityMap).sort((a, b) => b[1] - a[1])) {
      wsSummary.addRow({ location: loc, count, status: 'No Website Verified' });
    }

    const tmpMasterXlsx = `${MASTER_XLSX}.tmp`;
    await wb.xlsx.writeFile(tmpMasterXlsx);
    try {
      await fs.rename(tmpMasterXlsx, MASTER_XLSX);
    } catch {
      await fs.copyFile(tmpMasterXlsx, MASTER_XLSX);
      await fs.unlink(tmpMasterXlsx).catch(() => {});
    }

    // 3. Update State & Province Individual Workbooks
    const byState = {};
    for (const lead of allLeads) {
      const st = lead.state || 'Other';
      if (!byState[st]) byState[st] = { country: lead.country, leads: [] };
      byState[st].leads.push(lead);
    }

    for (const [st, item] of Object.entries(byState)) {
      const targetDir = item.country === 'CA' ? CANADA_DIR : USA_DIR;
      if (!existsSync(targetDir)) await fs.mkdir(targetDir, { recursive: true });
      const stateFile = path.join(targetDir, `${st}.xlsx`);
      const stateWb = new ExcelJS.Workbook();
      const ws = stateWb.addWorksheet(`${st} Clinics`);
      ws.columns = HEADERS;
      ws.getRow(1).font = { bold: true };
      ws.views = [{ state: 'frozen', ySplit: 1 }];
      item.leads.forEach(l => ws.addRow(l));
      await stateWb.xlsx.writeFile(stateFile);
    }

  } catch (err) {
    // Non-fatal aggregation error (e.g. file lock momentary delay)
  } finally {
    isAggregating = false;
  }
}

// Run aggregation every 25 seconds
setInterval(aggregateData, 25000);

// Periodic console status update every 60 seconds
setInterval(() => {
  if (existsSync(MASTER_CSV)) {
    try {
      const lines = readFileSync(MASTER_CSV, 'utf8').trim().split('\n');
      const total = Math.max(0, lines.length - 1);
      console.log(`\n=================== 📊 LIVE MASTER PROGRESS ===================`);
      console.log(`  Total Qualified Dental Clinics (No Website): ${total}`);
      console.log(`  Target Folder: "Sajjad data" in Root`);
      console.log(`  Master Excel:  "Sajjad data/Dental_Clinics_US_CA_Master.xlsx"`);
      console.log(`  Active Workers: Eastern, Central, Mountain, Pacific (4 Parallel)`);
      console.log(`=================================================================\n`);
    } catch {}
  }
}, 60000);

// ---------------------------------------------------------------- GRACEFUL SHUTDOWN
function shutdown() {
  if (stopping) return;
  stopping = true;
  console.log('\n[ORCHESTRATOR] Stopping all zone workers cleanly...');
  for (const [zone, item] of workers.entries()) {
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${item.process.pid} /T /F`, { stdio: 'ignore' });
      } else {
        item.process.kill('SIGKILL');
      }
    } catch {}
  }
  aggregateData().then(() => {
    console.log('[ORCHESTRATOR] Final aggregation complete. Exited.');
    process.exit(0);
  });
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

// Maximum runtime limiter (ideal for CI/CD and cloud jobs)
const maxRunMinutes = parseInt(process.env.MAX_RUN_MINUTES || '0', 10);
if (maxRunMinutes > 0) {
  console.log(`[ORCHESTRATOR] ⏱️ Maximum run duration set to ${maxRunMinutes} minutes.`);
  setTimeout(() => {
    console.log(`[ORCHESTRATOR] ⏱️ Time limit of ${maxRunMinutes}m reached. Initiating clean exit...`);
    shutdown();
  }, maxRunMinutes * 60 * 1000);
}

// ---------------------------------------------------------------- MAIN START
async function start() {
  console.log('=======================================================================');
  console.log('  🦷 AUTONOMOUS DENTAL CLINIC LEAD SCRAPER (NO WEBSITE ONLY)');
  console.log('  📍 Target: Top Populated Cities in USA & Canada');
  console.log('  📁 Output: "Sajjad data" in Project Root');
  console.log('  ⚡ Architecture: 4 Parallel Time-Zone Workers + Auto Watchdog');
  console.log('=======================================================================\n');

  // Launch all 4 zone workers concurrently
  for (const z of ZONES) {
    launchWorker(z);
  }
}

start().catch(console.error);
