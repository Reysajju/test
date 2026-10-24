// dental_worker.js - Autonomous Zone Worker for Dental Clinics (No Website)
// Targets top populated cities in USA and Canada with strict deduplication & real-time streaming

import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import { existsSync, readFileSync, appendFileSync } from 'node:fs';
import path from 'node:path';

// Parse command line arguments
const args = process.argv.slice(2);
let zoneName = 'eastern';
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--zone' && args[i + 1]) {
    zoneName = args[i + 1].toLowerCase();
    i++;
  }
}

const SAJJAD_DATA_DIR = path.resolve('Sajjad data');
const CHECKPOINTS_DIR = path.join(SAJJAD_DATA_DIR, 'zone_checkpoints');
const DEDUP_FILE = path.join(CHECKPOINTS_DIR, 'shared_dedup.json');
const LOG_FILE = path.join(SAJJAD_DATA_DIR, 'dental_search_activity.log');
const ZONE_CSV = path.join(CHECKPOINTS_DIR, `zone_${zoneName}.csv`);
const STATE_FILE = path.join(CHECKPOINTS_DIR, `state_${zoneName}.json`);

const DENTAL_CATEGORIES = [
  'dental clinic',
  'dentist',
  'family dentistry',
  'cosmetic dentistry',
  'pediatric dentist',
  'orthodontist',
  'dental implants',
  'emergency dentist',
  'dental care',
  'dental office',
  'teeth whitening clinic',
  'periodontist'
];

const HEADERS = [
  'Business Name',
  'Phone',
  'Category',
  'Address',
  'City',
  'State / Province',
  'Country',
  'Rating',
  'Total Reviews',
  'Business Hours',
  'Website Status',
  'Google Maps URL',
  'Scraped At'
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rand = (a, b) => Math.floor(a + Math.random() * (b - a));

function log(...msgs) {
  const time = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const line = `[${zoneName.toUpperCase()}] ${time} ${msgs.join(' ')}`;
  console.log(line);
  try {
    appendFileSync(LOG_FILE, line + '\n');
  } catch {}
}

// ---------------------------------------------------------------- DEDUPLICATION
let sharedPhones = new Set();
let sharedAddresses = new Set();
let sharedIds = new Set();

function normalizePhone(p) {
  if (!p) return '';
  const digits = p.replace(/\D/g, '');
  if (digits.length === 11 && digits.startsWith('1')) return digits.slice(1);
  return digits;
}

function normalizeAddress(a) {
  if (!a) return '';
  return a.toLowerCase().replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
}

function loadSharedDedup() {
  if (existsSync(DEDUP_FILE)) {
    try {
      const data = JSON.parse(readFileSync(DEDUP_FILE, 'utf8'));
      sharedPhones = new Set(data.phones || []);
      sharedAddresses = new Set(data.addresses || []);
      sharedIds = new Set(data.ids || []);
    } catch {}
  }
}

async function recordDedup(normPhone, normAddr, id) {
  if (normPhone) sharedPhones.add(normPhone);
  if (normAddr) sharedAddresses.add(normAddr);
  if (id) sharedIds.add(id);

  try {
    loadSharedDedup();
    if (normPhone) sharedPhones.add(normPhone);
    if (normAddr) sharedAddresses.add(normAddr);
    if (id) sharedIds.add(id);

    const tmpFile = `${DEDUP_FILE}.tmp.${zoneName}.${process.pid}`;
    await fs.writeFile(
      tmpFile,
      JSON.stringify({
        phones: [...sharedPhones],
        addresses: [...sharedAddresses],
        ids: [...sharedIds]
      })
    );
    try {
      await fs.rename(tmpFile, DEDUP_FILE);
    } catch {
      await fs.copyFile(tmpFile, DEDUP_FILE);
      await fs.unlink(tmpFile).catch(() => {});
    }
  } catch {}
}

// ---------------------------------------------------------------- CSV LOGGING
const csvCell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;

async function initZoneCsv() {
  if (!existsSync(CHECKPOINTS_DIR)) {
    await fs.mkdir(CHECKPOINTS_DIR, { recursive: true });
  }
  if (!existsSync(ZONE_CSV)) {
    await fs.writeFile(ZONE_CSV, HEADERS.map(h => `"${h}"`).join(',') + '\n');
  }
}

async function appendLeadToCsv(lead) {
  const row = [
    csvCell(lead.name),
    csvCell(lead.phone),
    csvCell(lead.category),
    csvCell(lead.address),
    csvCell(lead.city),
    csvCell(lead.state),
    csvCell(lead.country),
    csvCell(lead.rating),
    csvCell(lead.reviews),
    csvCell(lead.hours),
    csvCell(lead.websiteStatus),
    csvCell(lead.url),
    csvCell(lead.scrapedAt)
  ].join(',') + '\n';

  await fs.appendFile(ZONE_CSV, row);
}

// ---------------------------------------------------------------- BROWSER
async function handleConsent(page) {
  const btn = page.getByRole('button', { name: /accept all|i agree|reject all/i }).first();
  if (await btn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await btn.click().catch(() => {});
  }
}

async function checkBlocked(page) {
  if (page.url().includes('/sorry/') || (await page.locator('iframe[src*="recaptcha"]').count())) {
    log('⚠️ Google CAPTCHA / rate-limit encountered. Cooling down for 2.5 minutes...');
    await sleep(150000);
    return true;
  }
  return false;
}

async function collectCandidates(page, query, country = 'US') {
  const gl = country === 'CA' ? 'ca' : 'us';
  const url = `https://www.google.com/maps/search/${encodeURIComponent(query)}?hl=en&gl=${gl}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await handleConsent(page);
  if (await checkBlocked(page)) return [];

  const feed = page.locator('div[role="feed"]');
  const gotFeed = await feed.waitFor({ timeout: 12000 }).then(() => true).catch(() => false);
  if (!gotFeed) return [];

  let lastCount = 0;
  let stale = 0;
  for (let i = 0; i < 12; i++) {
    await feed.evaluate((el) => el.scrollBy(0, el.scrollHeight));
    await sleep(rand(500, 750));
    const count = await page.locator('div[role="feed"] a[href*="/maps/place/"]').count();
    const ended = await page.getByText(/you.?ve reached the end of the list/i).isVisible().catch(() => false);
    if (ended) break;
    stale = count === lastCount ? stale + 1 : 0;
    if (stale >= 2) break;
    lastCount = count;
  }

  return page.evaluate(() => {
    const results = [];
    document.querySelectorAll('div[role="feed"] a[href*="/maps/place/"]').forEach((a) => {
      const card = a.closest('div.Nv2PK') || a.parentElement?.parentElement || a.parentElement;
      // STRICT FILTER: Discard any listing that displays a Website button in the feed card
      const hasWebsite = !!card?.querySelector('a[data-value="Website"], a[aria-label*="website" i]');
      const label = card?.querySelector('span[role="img"]')?.getAttribute('aria-label') || '';
      const m = label.match(/([\d,]+)\s+review/i);
      results.push({
        href: a.href,
        hasWebsite,
        reviews: m ? parseInt(m[1].replace(/,/g, ''), 10) : null
      });
    });
    return results;
  });
}

function getPlaceId(href) {
  try {
    const url = new URL(href);
    const m = url.pathname.match(/\/place\/([^\/]+)/);
    if (m) return decodeURIComponent(m[1]);
    return url.pathname;
  } catch {
    return href;
  }
}

async function scrapeDetail(page, href) {
  await page.goto(href, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.locator('h1').first().waitFor({ state: 'attached', timeout: 7000 }).catch(() => {});
  await sleep(rand(200, 400));

  const result = await page.evaluate(() => {
    const txt = (el) => el?.innerText?.replace(/\s+/g, ' ').trim() || '';
    const aria = (sel, prefix) => {
      const v = document.querySelector(sel)?.getAttribute('aria-label') || '';
      return v.replace(new RegExp(`^${prefix}:?\\s*`, 'i'), '').trim();
    };

    const name = txt(document.querySelector('h1.DUwDvf') || [...document.querySelectorAll('h1')].find((h) => txt(h)));
    const category = txt(document.querySelector('button[jsaction*="category"]'));
    const address = aria('[data-item-id="address"]', 'Address');
    const phone = aria('[data-item-id^="phone"]', 'Phone');
    
    // Strict multi-selector website inspection
    let website = document.querySelector('[data-item-id="authority"]')?.getAttribute('href') || '';
    if (!website) {
      const webBtn = document.querySelector('a[aria-label*="website" i], [data-tooltip*="website" i]');
      if (webBtn) website = webBtn.getAttribute('href') || 'yes';
    }

    const header = txt(document.querySelector('div.F7nice'));
    let rating = (header.match(/^(\d\.\d)/) || [])[1] || '';
    let reviews = (header.match(/\(([\d,]+)\)/) || [])[1];
    if (!reviews) {
      const l = [...document.querySelectorAll('[aria-label*="review" i]')]
        .map((e) => e.getAttribute('aria-label')).find((x) => /\d/.test(x || ''));
      reviews = (l?.match(/([\d,]+)\s+reviews?/i) || [])[1];
    }
    if (!reviews) {
      const revEl = document.querySelector('button[aria-label*="review" i], span[aria-label*="review" i]');
      const m = (revEl?.getAttribute('aria-label') || revEl?.innerText || '').match(/\b([\d,]+)\s+reviews?\b/i);
      if (m) reviews = m[1];
    }
    reviews = reviews ? parseInt(reviews.replace(/,/g, ''), 10) : (rating ? 5 : 0);

    const days = /(mon|tue|wed|thu|fri|sat|sun)/i;
    let hours = [...document.querySelectorAll('table tr')].map(txt).filter((r) => days.test(r)).join('; ');
    if (!hours) hours = aria('[data-item-id="oh"]', '') || '';

    return { name, category, address, phone, website, rating, reviews, hours };
  });

  await page.goto('about:blank').catch(() => {});
  return result;
}

function parseAddress(address, defaultCity, defaultState) {
  const clean = (address || '').replace(/,?\s*(United States|USA|Canada)$/i, '').trim();
  const parts = clean.split(',').map((s) => s.trim());
  let state = defaultState;
  let city = defaultCity;

  if (parts.length >= 2) {
    const last = parts[parts.length - 1];
    const m = last.match(/\b([A-Z]{2})\b(?:\s+[A-Z0-9\s-]+)?/);
    if (m) state = m[1];
    city = parts[parts.length - 2];
  }
  return { city: city || defaultCity, state: state || defaultState };
}

// ---------------------------------------------------------------- MAIN WORKER LOOP
async function main() {
  const matrixData = JSON.parse(await fs.readFile('dental_cities.json', 'utf8'));
  const zoneInfo = matrixData[zoneName];
  if (!zoneInfo) throw new Error(`Unknown zone: ${zoneName}`);

  const cities = zoneInfo.cities;
  await initZoneCsv();
  loadSharedDedup();

  let state = {
    cityIdx: 0,
    catIdx: 0,
    totalLeads: 0,
    seenIds: []
  };

  if (existsSync(STATE_FILE)) {
    try {
      state = JSON.parse(await fs.readFile(STATE_FILE, 'utf8'));
    } catch {}
  }

  const localSeenIds = new Set(state.seenIds || []);

  log(`Target Matrix Loaded: ${cities.length} top populated cities in ${zoneInfo.name}.`);
  log(`Resuming at City #${state.cityIdx + 1}/${cities.length}, Category #${state.catIdx + 1}/${DENTAL_CATEGORIES.length}. Verified leads so far: ${state.totalLeads}`);

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--js-flags=--max-old-space-size=256',
      '--disk-cache-size=1',
      '--media-cache-size=1'
    ]
  });

  browser.on('disconnected', () => {
    log('Browser disconnected. Exiting to allow manager restart...');
    process.exit(1);
  });

  const ctx = await browser.newContext({
    locale: 'en-US',
    viewport: { width: 1280, height: 800 }
  });

  // Block images and heavy media for maximum performance & speed
  await ctx.route('**/*', (route) => {
    const type = route.request().resourceType();
    if (['image', 'media', 'font'].includes(type)) return route.abort();
    return route.continue();
  });

  const searchPage = await ctx.newPage();
  searchPage.setDefaultTimeout(20000);
  searchPage.setDefaultNavigationTimeout(25000);

  const detailPage = await ctx.newPage();
  detailPage.setDefaultTimeout(14000);
  detailPage.setDefaultNavigationTimeout(18000);

  let stopping = false;
  let queriesInSession = 0;
  process.on('SIGINT', () => { stopping = true; log('Stopping cleanly...'); });
  process.on('SIGTERM', () => { stopping = true; log('Stopping cleanly...'); });

  for (; state.cityIdx < cities.length && !stopping; state.cityIdx++, state.catIdx = 0) {
    const currentCity = cities[state.cityIdx];

    for (; state.catIdx < DENTAL_CATEGORIES.length && !stopping; state.catIdx++) {
      queriesInSession++;
      // Auto-recycle session every 20 queries for memory optimization
      if (queriesInSession > 20) {
        log('Cycling browser session after 20 queries for optimal speed...');
        await browser.close().catch(() => {});
        process.exit(0);
      }

      loadSharedDedup();
      const cat = DENTAL_CATEGORIES[state.catIdx];
      const query = `${cat} in ${currentCity.queryLoc}`;

      try {
        const candidates = await collectCandidates(searchPage, query, currentCity.country);
        const fresh = candidates.filter((c) => {
          const id = getPlaceId(c.href);
          c.id = id;
          return id && !c.hasWebsite && !localSeenIds.has(id) && !sharedIds.has(id);
        });

        log(`[${currentCity.name}, ${currentCity.state} (${currentCity.country})] "${cat}": ${candidates.length} found, ${fresh.length} website-free candidate(s)`);

        for (const c of fresh) {
          if (stopping) break;
          localSeenIds.add(c.id);
          sharedIds.add(c.id);

          try {
            const d = await scrapeDetail(detailPage, c.href);
            // STRICT FILTER 1: Business has an existing website
            if (d.website && d.website.trim().length > 0) continue;

            // STRICT FILTER 2: Valid phone number required
            const normPhone = normalizePhone(d.phone);
            if (!normPhone || normPhone.length < 10) continue;

            // STRICT FILTER 3: Phone Deduplication
            loadSharedDedup();
            if (sharedPhones.has(normPhone)) continue;

            // STRICT FILTER 4: Address Deduplication
            const normAddr = normalizeAddress(d.address);
            if (!normAddr || sharedAddresses.has(normAddr)) continue;

            // Basic check
            if (!d.name || !d.address) continue;

            const { city, state: parsedState } = parseAddress(d.address, currentCity.name, currentCity.state);
            const lead = {
              name: d.name,
              phone: d.phone,
              category: d.category || cat,
              address: d.address,
              city,
              state: parsedState,
              country: currentCity.country,
              rating: d.rating || '',
              reviews: d.reviews || 0,
              hours: d.hours || '',
              websiteStatus: 'No Website',
              url: c.href,
              scrapedAt: new Date().toISOString()
            };

            await recordDedup(normPhone, normAddr, c.id);
            state.totalLeads++;
            await appendLeadToCsv(lead);

            log(`  ★ QUALIFIED DENTAL CLINIC #${state.totalLeads}: "${d.name}" | 📞 ${d.phone} | 📍 ${city}, ${parsedState} (${currentCity.country}) | ⭐ ${d.rating || 'N/A'} (${d.reviews} reviews) | No Website`);
          } catch (e) {
            log('  ! Detail error:', e.message.split('\n')[0]);
          }

          await sleep(rand(500, 900));
        }
      } catch (e) {
        log('! Search error:', e.message.split('\n')[0]);
        await sleep(3500);
      }

      state.seenIds = [...localSeenIds];
      await fs.writeFile(STATE_FILE, JSON.stringify({ ...state, catIdx: state.catIdx + 1 }, null, 2));
      await sleep(rand(700, 1400));
    }
  }

  await browser.close();
  log(`Zone worker finished all cities! Total qualified dental clinics: ${state.totalLeads}`);
}

main().catch((err) => {
  console.error(`[${zoneName.toUpperCase()}] Fatal error:`, err);
  process.exit(1);
});
