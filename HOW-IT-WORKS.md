# Maps Lead Scraper: How It Works and How to Make It Faster Locally

## 1. What the script does

It finds US businesses on Google Maps that look like **good website-design / marketing leads**: they have a phone number, opening hours and at least 2 reviews, but no website.

### Step-by-step flow

```
Start
  |
  v
Load counties (Census list, sorted east -> west)  <-- downloaded once, cached in counties.json
  |
  v
Load state.json (where we stopped, which places we already saw)
  |
  v
FOR each county (east to west)
  FOR each category (plumbers, salons, restaurants, ...)
      |
      1. Open  maps/search/"<category> in <County>, <ST>"
      2. Scroll the results panel until the list ends (~up to 120 results)
      3. Read each result card from the list:
           - has a "Website" button?  -> skip (not a lead)
           - review count < 2?         -> skip
           - place already seen?       -> skip
      4. For each remaining card, open the listing page and read the DOM:
           name, category, address, phone, website, hours, rating, reviews
      5. Qualify: phone + hours + address + NO website + reviews >= 2
      6. If qualified:
           - split address into city / state
           - add a row to leads.xlsx and save
           - append the same row to leads.csv
      7. Save state.json (so a crash or Ctrl+C never loses progress)
      8. Random pause, then next category
```

### Files it creates

| File | Purpose |
|---|---|
| `leads.xlsx` | Final spreadsheet, rewritten after every lead |
| `leads.csv` | Append-only backup of the same data (survives crashes and a locked xlsx) |
| `state.json` | Resume point + list of places already checked |
| `counties.json` | Cached county list sorted east to west |

### Why it is built this way

- **Two-stage filtering** (list card first, listing page second) avoids opening the large majority of listings, since most businesses have a website.
- **State file** makes it fully autonomous and resumable. You can stop and restart at any time.
- **CSV + XLSX** means that even if Excel has the file open (which locks it on Windows), no lead is lost.
- **Randomised delays** make traffic look less robotic and reduce CAPTCHAs.

---

## 2. Realistic expectations

The current script is **single worker, one search at a time**.

Rough, untested estimates (your results will vary):

- One search (scroll + collect): about 15 to 30 seconds
- One listing page opened: about 3 to 6 seconds
- A search with 20 to 40 candidate listings: about 2 to 4 minutes
- Full run (about 3,100 counties x 40 categories = about 124,000 searches): **months** on one worker

So the goal of optimisation is to **search fewer, smarter places** and **run in parallel**, not just to make each step faster.

---

## 3. How to make it more efficient when run locally

Ordered by impact. Do the first three before anything else.

### A. Cut the number of searches (biggest win)

1. **Start with a small category list.** Keep the 8 to 10 categories that most often have no website (plumbers, handymen, cleaning, landscaping, barbers, auto repair, towing, food trucks, pest control, painters). Run the full list later.
2. **Skip tiny counties at first.** Many rural counties have a few hundred businesses in total. Add a population filter and run the largest counties first, or run one broad query ("businesses") for small counties instead of 40 categories.
3. **Split huge counties by city.** A single "plumbers in Los Angeles County" search is capped at about 120 results, so it misses most of them. For big counties, search by city or ZIP instead. This finds more leads per hour than adding categories.
4. **Learn which categories pay off.** Log leads per category (the spreadsheet already has a Category column). After a few hundred counties, drop categories that produce almost nothing.

### B. Run several workers in parallel

A single Chromium tab is mostly waiting on the network. On a normal laptop or desktop you can run **3 to 4 workers** (separate processes, each with its own state file and output file) before CPU, RAM or Google rate limits hurt.

Simple sharding idea: give each worker a slice of the county list.

```js
// at the top of main(), after loading counties
const WORKER = Number(process.env.WORKER ?? 0);
const WORKERS = Number(process.env.WORKERS ?? 1);
const mine = counties.filter((_, i) => i % WORKERS === WORKER);
// use `mine` instead of `counties`, and give each worker its own
// state/xlsx/csv file names, e.g. `state-${WORKER}.json`, `leads-${WORKER}.csv`
```

Run:

```bash
WORKER=0 WORKERS=3 npm start
WORKER=1 WORKERS=3 npm start
WORKER=2 WORKERS=3 npm start
```

Merge the CSVs at the end and remove duplicates by Google Maps URL.

> Do not go above 4 workers on one IP. More parallelism gets you CAPTCHAs, not more leads.

### C. Block heavy resources in Chromium

Maps loads a lot of images, map tiles and fonts you never read. Blocking them cuts bandwidth and speeds up every page. Add this after creating the context:

```js
await ctx.route('**/*', (route) => {
  const type = route.request().resourceType();
  if (['image', 'media', 'font'].includes(type)) return route.abort();
  return route.continue();
});
```

Test it. Blocking images is usually safe, but if results stop loading, remove `image` from the list first.

### D. Replace fixed sleeps with real waits

Some `sleep()` calls can be replaced with `waitFor` on the element you need (for example the phone button or the hours table). You keep a small random delay for politeness, but stop waiting a full second when the page is already ready.

### E. Write the spreadsheet less often

`leads.xlsx` is fully rewritten after every lead. That is fine for hundreds of rows, but slow for tens of thousands. Because the CSV is already appended instantly:

- Keep the CSV write on every lead.
- Rewrite the XLSX every 25 leads, or every few minutes, and once on exit.

### F. Keep Chromium healthy on long runs

- Restart the browser every 200 to 300 searches to avoid memory growth.
- Use `HEADLESS=true` (default). It uses less CPU than a visible window.
- Close other heavy apps. Chromium plus Excel plus a browser with many tabs will slow everything.

### G. Make it truly autonomous

- Run it under **pm2** so it restarts after crashes or reboots:
  ```bash
  npm i -g pm2
  pm2 start scraper.js --name maps-leads
  pm2 save && pm2 startup
  ```
- Stop the machine from sleeping (power settings) and keep it on a stable wired connection.
- Because you work US-aligned night shifts, scheduling heavy runs at night in Karachi or during your own downtime avoids competing with your daytime work for bandwidth.

### H. Reduce CAPTCHAs and blocks

- Keep delays random, and keep a **per-worker** delay of at least 1 to 3 seconds between listings.
- A **residential** proxy (not datacenter) per worker helps a lot on long runs. Cheap datacenter IPs get flagged quickly.
- Set the browser locale and timezone to match the US (`locale: 'en-US'`, `timezoneId: 'America/Chicago'`) so the traffic looks consistent with the searches.
- When a CAPTCHA appears, the script already pauses for 5 minutes. If this happens often, lower worker count and raise delays.

---

## 4. Quality checks before you start calling or emailing leads

- **Spot-check 20 leads manually** on Google Maps. Confirm the phone is correct and that the business really has no website (some list a Facebook page instead, which this script treats as no website).
- **Remove duplicates** across workers by Maps URL or by phone number.
- **Check call and text rules** (do-not-call lists, state telemarketing rules). Cold-calling US consumers and small businesses has legal requirements.
- **Google's terms prohibit scraping.** The Places API is the compliant alternative, though paid.

---

## 5. Suggested rollout

1. Run one worker on 5 to 10 counties, headed (`HEADLESS=false`), and verify every column fills correctly.
2. Fix any selectors Google changed (inside `scrapeDetail()` and `collectCandidates()`).
3. Trim categories and add the resource blocking.
4. Add worker sharding and run 2 to 3 workers headless under pm2.
5. Review leads per category and per county weekly, and adjust.
