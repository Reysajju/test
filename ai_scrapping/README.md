# 🚀 AI Scrapping: Authentic Business Lead Mining & High-Ticket Enrichment Pipeline

An intelligent, multi-stage data mining pipeline engineered to bridge the gap between high-volume discovery and deep, authenticated decision-maker intelligence for high-ticket client acquisition.

---

## 🏛️ Architecture & How It Works

```
Raw Business Lead (Google Maps / YellowPages / B2B Crawler)
                 │
                 ▼
  [Phase 1: Multi-Directory Aggregator]
  - Google Maps Ingestion (leads.csv)
  - YellowPages & Superpages Public Directories
  - Deduplication on Phone & Address
                 │
                 ▼
  [Phase 2: ScrapeGraphAI & Multi-Page Footprint Scanner]
  - Discovers online footprint (Facebook, Instagram, Yelp, Directories)
  - Scans multiple web pages for contact signals
  - Extracts direct phones, verified emails, social profiles
                 │
                 ▼
  [Phase 3: Decision-Maker & Corporate Registry Engine]
  - OpenCorporates (State Secretary of State filings & officers)
  - Better Business Bureau (BBB) Principal Management
  - Public Executive Snippets (Owner, Founder, President)
                 │
                 ▼
  [Phase 4: AI Polisher & Lead Synthesis]
  - Authenticity Scoring (0 - 100%)
  - High-Ticket Pitch Hook generation tailored to their specific gaps
                 │
                 ▼
  [Phase 5: Master Deliverable]
  - Styled Excel Workbook (.xlsx) with frozen panes & column formatting
  - Production CSV Backup (.csv)
```

---

## 🌐 Free Data Sources Integrated

| Source | Role | Data Extracted |
| :--- | :--- | :--- |
| **Google Maps / B2B Crawler** | Base Lead Discovery | Business Name, Category, Reviews, Rating, Map URL, Physical Address. |
| **YellowPages.com** | Public Directory Lookup | Secondary phone lines, street addresses, localities, business tenure. |
| **OpenCorporates** | Official State SOS Filings | Registered corporate officers, LLC managing members, President, CEO. |
| **BBB.org Public Profiles** | Business Credibility Index | Principal Management names and direct titles. |
| **DuckDuckGo Deep Index** | Multi-Page Footprint Discovery | Instagram, Facebook, LinkedIn profiles, local news mentions, owner snippets. |

---

## ⚡ Quick Start

### 1. Launch the Autonomous AI Lead Strategist Agent
Run the interactive AI supervisor that asks what data you need, fetches OpenRouter's live free models, asks clarifying questions, and autonomously deploys the scraping department:
```bash
python agent.py
```
*(Or in Windows CMD, simply run: `run_agent.bat`)*

### 2. Manual Pipeline Commands (Alternative)

#### Mode A: Enrich Existing B2B Leads
```bash
python pipeline.py --mode ingest --limit 5
```

#### Mode B: Live Discovery on Free Directories
```bash
python pipeline.py --mode discover --category "dental clinics" --location "Chicago, IL" --limit 10
```

#### Mode C: Full End-to-End
```bash
python pipeline.py --mode full --limit 10
```

---

## 📊 Output Deliverables

Outputs are automatically organized into `data/`:
- `data/raw/`: Raw extracted base leads (`raw_leads_<timestamp>.json`).
- `data/enriched/`: Multi-page scan and corporate registry data (`enriched_leads_<timestamp>.json`).
- `data/polished/`: Final polished files:
  - `polished_leads_<timestamp>.xlsx` (Formatted Excel sheet)
  - `polished_leads_<timestamp>.csv` (Clean CSV file)
  - `polished_leads_<timestamp>.json` (Full JSON records)

### Excel Columns Included:
1. `Business Name`
2. `Category`
3. `Owner / Decision Maker`
4. `Role / Title`
5. `Confidence (%)`
6. `Direct Phone`
7. `Verified Email`
8. `Instagram Profile`
9. `Facebook Page`
10. `LinkedIn Profile`
11. `City`, `State`, `Full Address`
12. `Rating` & `Reviews`
13. `Has Website?`
14. `High-Ticket Pitch Hook` (Personalized cold outreach angle)
15. `Sources Scanned`
16. `Scraped Date`
