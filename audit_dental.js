// audit_dental.js - Live Audit & Telemetry for Dental Clinic Scraper
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const sajjadDir = path.resolve('Sajjad data');
const masterCsv = path.join(sajjadDir, 'Dental_Clinics_US_CA_Master.csv');
const masterXlsx = path.join(sajjadDir, 'Dental_Clinics_US_CA_Master.xlsx');
const checkpointsDir = path.join(sajjadDir, 'zone_checkpoints');
const dedupFile = path.join(checkpointsDir, 'shared_dedup.json');

console.log('\n=================== 🦷 DENTAL CLINIC SCRAPER AUDIT ===================');

let totalLeads = 0;
let usaCount = 0;
let caCount = 0;
const byState = {};

if (fs.existsSync(masterCsv)) {
  const lines = fs.readFileSync(masterCsv, 'utf8').trim().split('\n');
  totalLeads = Math.max(0, lines.length - 1);

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split('","');
    if (cols.length >= 7) {
      const state = cols[5]?.replace(/"/g, '') || 'Other';
      const country = cols[6]?.replace(/"/g, '') || '';
      if (country === 'US') usaCount++;
      else if (country === 'CA') caCount++;
      byState[state] = (byState[state] || 0) + 1;
    }
  }
}

console.log(`📁 Target Directory:        ${sajjadDir}`);
console.log(`📊 Total Qualified Leads:   ${totalLeads} clinics without websites`);
console.log(`🇺🇸 USA Dental Clinics:      ${usaCount}`);
console.log(`🇨🇦 Canada Dental Clinics:   ${caCount}`);

if (fs.existsSync(masterXlsx)) {
  const stat = fs.statSync(masterXlsx);
  console.log(`📗 Master Excel (.xlsx):    ${masterXlsx} (${Math.round(stat.size / 1024)} KB, updated ${stat.mtime.toLocaleTimeString()})`);
} else {
  console.log(`📗 Master Excel (.xlsx):    Generating upon first aggregation cycle...`);
}

console.log('\n--- 🗺️ Top States & Provinces ---');
const topStates = Object.entries(byState).sort((a, b) => b[1] - a[1]).slice(0, 10);
if (topStates.length > 0) {
  for (const [st, count] of topStates) {
    console.log(`   • ${st.padEnd(8)}: ${count} clinics`);
  }
} else {
  console.log('   (Collecting initial leads across cities...)');
}

// Zone Worker Status
console.log('\n--- ⚡ Active Worker Processes ---');
const zones = ['eastern', 'central', 'mountain', 'pacific'];
for (const z of zones) {
  const zoneCsv = path.join(checkpointsDir, `zone_${z}.csv`);
  let zCount = 0;
  if (fs.existsSync(zoneCsv)) {
    const zLines = fs.readFileSync(zoneCsv, 'utf8').trim().split('\n');
    zCount = Math.max(0, zLines.length - 1);
  }

  const statePath = path.join(checkpointsDir, `state_${z}.json`);
  let progress = 'Init';
  if (fs.existsSync(statePath)) {
    try {
      const s = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      progress = `City ${s.cityIdx + 1}, Cat ${s.catIdx + 1}`;
    } catch {}
  }

  console.log(`   • [${z.toUpperCase().padEnd(8)}] Qualified: ${zCount.toString().padEnd(4)} | Progress: ${progress}`);
}

// Deduplication
if (fs.existsSync(dedupFile)) {
  try {
    const d = JSON.parse(fs.readFileSync(dedupFile, 'utf8'));
    console.log('\n--- 🛡️ Deduplication Engine ---');
    console.log(`   Unique Phone Numbers:    ${d.phones?.length || 0}`);
    console.log(`   Unique Physical Addrs:   ${d.addresses?.length || 0}`);
    console.log(`   Disqualified / Seen CIDs: ${d.ids?.length || 0}`);
  } catch {}
}

// Node process health
try {
  const tasklist = execSync('tasklist /FI "IMAGENAME eq node.exe" /FO CSV /NH', { encoding: 'utf8' });
  const nodeRows = tasklist.trim().split('\n').filter(r => r.includes('node.exe'));
  console.log(`\n⚙️ Active Node Processes:   ${nodeRows.length}`);
} catch {}

console.log('=======================================================================\n');
