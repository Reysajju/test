"""
Master Pipeline: AI Scrapping for High-Ticket Business Lead Generation
Coordinates:
  Phase 1: Multi-Directory Raw Discovery (Google Maps, YellowPages, Directory Ingest)
  Phase 2: AI Multi-Page Deep Scanner (ScrapeGraphAI + Multi-URL footprint hunting)
  Phase 3: Decision-Maker & Personal Intelligence (OpenCorporates, SOS Registries, BBB, Web)
  Phase 4: AI Polisher & Lead Synthesis (Authenticity scoring, custom pitch hooks)
  Phase 5: Structured Export to Styled Excel (.xlsx) & CSV
"""

import sys
import argparse
import datetime
from pathlib import Path

# Ensure UTF-8 output across Windows PowerShell / CMD consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from config import RAW_DIR, ENRICHED_DIR, POLISHED_DIR
from modules.raw_discovery import RawDiscoveryEngine
from modules.ai_scanner import AIScannerEngine
from modules.person_enricher import PersonEnricherEngine
from modules.ai_polisher import AIPolisherEngine
from utils.helpers import save_json
from utils.export import export_leads

def print_banner():
    print("""
========================================================================
    🚀 AI BUSINESS LEAD MINING & ENRICHMENT PIPELINE
    Stage 1: Multi-Directory Discovery (Google Maps / YellowPages)
    Stage 2: ScrapeGraphAI Multi-Page Deep Scanner
    Stage 3: Decision-Maker & Secretary of State Corporate Filings
    Stage 4: AI Synthesis & High-Ticket Pitch Hook Generation
========================================================================
""")

def run_pipeline(
    mode: str = "ingest",
    category: str = "barber shops",
    location: str = "Machias, ME",
    csv_file: Path = None,
    limit: int = 5,
    llm_provider: str = None,
    llm_model: str = None,
    api_key: str = None,
    no_website_only: bool = False
):
    # Check if user requested the interactive AI Consultant Agent
    if mode == "agent":
        from agent import run_agent_loop
        run_agent_loop()
        return

    print_banner()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    discovery_engine = RawDiscoveryEngine()
    scanner_engine = AIScannerEngine(provider=llm_provider, api_key=api_key, model=llm_model)
    person_engine = PersonEnricherEngine()
    polisher_engine = AIPolisherEngine()

    raw_leads = []

    # -------------------------------------------------------------------------
    # PHASE 1: RAW DISCOVERY
    # -------------------------------------------------------------------------
    print(f"\n[PHASE 1] Starting Raw Lead Discovery (Mode: {mode.upper()})...")

    if mode == "mass-scrape":
        print("\n[MASS CRAWLER] Launching Playwright Google Maps Mass Harvester...")
        print("[MASS CRAWLER] Target: Up to 10,000 real businesses per state (No Website + Has Phone + Active Reviews)")
        print("[MASS CRAWLER] Running crawler across US county grids...\n")
        try:
            import subprocess
            crawler_script = ROOT_DIR.parent / "scraper.js"
            if crawler_script.exists():
                subprocess.run(["node", str(crawler_script)], cwd=str(ROOT_DIR.parent))
        except KeyboardInterrupt:
            print("\n[MASS CRAWLER] Crawling paused. Automatically handing over harvested leads to AI Department...")
        except Exception as e:
            print(f"[MASS CRAWLER] Crawler process notice: {e}")

        # Ingest the mass leads
        csv_file = ROOT_DIR.parent / "leads.csv"
        raw_leads = discovery_engine.ingest_b2b_csv(csv_file, limit=limit)

    elif mode in ["ingest", "mass-enrich"] and csv_file and csv_file.exists():
        raw_leads = discovery_engine.ingest_b2b_csv(csv_file, limit=limit)
    elif mode == "discover":
        raw_leads = discovery_engine.aggregate(category, location, max_results=limit, no_website_only=no_website_only)
    else:
        # Default: Ingest existing B2B if available, otherwise query Google Maps
        if csv_file and csv_file.exists():
            raw_leads = discovery_engine.ingest_b2b_csv(csv_file, limit=limit)
        if not raw_leads:
            raw_leads = discovery_engine.aggregate(category, location, max_results=limit, no_website_only=no_website_only)

    if not raw_leads:
        print("[PIPELINE] No raw leads found to process. Exiting.")
        return

    raw_output_path = RAW_DIR / f"raw_leads_{timestamp}.json"
    save_json(raw_output_path, raw_leads)
    print(f"[PHASE 1 COMPLETE] {len(raw_leads)} base leads secured -> {raw_output_path}")

    # -------------------------------------------------------------------------
    # PHASE 2, 3 & 4: AI SCANNING, REGISTRIES, & INCREMENTAL POLISHING
    # -------------------------------------------------------------------------
    export_base_path = POLISHED_DIR / f"polished_leads_{timestamp}"
    polished_leads = []
    print(f"\n[PHASE 2, 3 & 4] Commencing AI Deep Scanning, Corporate Registries & Continuous Polishing...")

    for idx, lead in enumerate(raw_leads, 1):
        print(f"\n--- Processing Lead #{idx}/{len(raw_leads)}: {lead.get('business_name')} ({lead.get('city')}, {lead.get('state')}) ---")
        
        # Step 2: Multi-Page AI Deep Scan (Emails, Secondary Phones, Socials)
        ai_scanned = scanner_engine.enrich_lead(lead)

        # Step 3: Decision Maker Discovery (OpenCorporates, BBB, Executive Snippets)
        person_enriched = person_engine.enrich_decision_maker(ai_scanned)

        # Step 4: Polish, Score Authenticity, and Craft Pitch Hook
        polished_lead = polisher_engine.polish_lead(person_enriched)
        polished_leads.append(polished_lead)

        # CONTINUOUS STREAMING EXPORT: Saves progress every 5 leads so data is never lost
        if idx % 5 == 0 or idx == len(raw_leads):
            export_leads(polished_leads, export_base_path)
            save_json(POLISHED_DIR / f"polished_leads_{timestamp}.json", polished_leads)

    # -------------------------------------------------------------------------
    # SUMMARY AUDIT
    # -------------------------------------------------------------------------
    with_phone = sum(1 for l in polished_leads if l.get("phone"))
    with_email = sum(1 for l in polished_leads if l.get("email"))
    with_owner = sum(1 for l in polished_leads if l.get("owner_name"))
    with_social = sum(1 for l in polished_leads if l.get("instagram") or l.get("facebook") or l.get("linkedin"))
    high_confidence = sum(1 for l in polished_leads if l.get("confidence_score", 0) >= 70)

    print("\n" + "=" * 72)
    print("                    🎯 HIGH-TICKET LEAD EXTRACTION REPORT")
    print("=" * 72)
    print(f"Total Leads Processed:              {len(polished_leads)}")
    print(f"Direct Phone Verified:              {with_phone}/{len(polished_leads)} ({round(with_phone/len(polished_leads)*100)}%)")
    print(f"Verified Email Addresses Found:     {with_email}/{len(polished_leads)} ({round(with_email/len(polished_leads)*100)}%)")
    print(f"Decision Makers / Owners Found:     {with_owner}/{len(polished_leads)} ({round(with_owner/len(polished_leads)*100)}%)")
    print(f"Active Social Profiles Attached:    {with_social}/{len(polished_leads)} ({round(with_social/len(polished_leads)*100)}%)")
    print(f"High-Ticket Qualified (>=70% Conf): {high_confidence}/{len(polished_leads)} ({round(high_confidence/len(polished_leads)*100)}%)")
    print("-" * 72)
    print(f"Master Excel Workbook: {export_base_path.with_suffix('.xlsx')}")
    print(f"Master CSV File:       {export_base_path.with_suffix('.csv')}")
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI Business Data Mining & High-Ticket Enrichment Pipeline")
    parser.add_argument(
        "--mode",
        choices=["ingest", "discover", "full", "agent", "mass-scrape", "mass-enrich"],
        default="mass-enrich",
        help="mass-enrich: enrich all Google Maps leads; mass-scrape: run Google Maps crawler then handover to AI; agent: interactive AI supervisor"
    )
    parser.add_argument("--category", default="barber shops", help="Business category for discovery")
    parser.add_argument("--location", default="Machias, ME", help="City and State for discovery")
    parser.add_argument("--csv", default=str(ROOT_DIR.parent / "leads.csv"), help="Path to existing CSV of leads")
    parser.add_argument("--limit", type=int, default=0, help="Number of leads to process (0 = all leads / mass mode)")
    parser.add_argument("--provider", default="openrouter", help="LLM provider: openrouter, openai, gemini, groq, ollama")
    parser.add_argument("--model", default=None, help="LLM Model identifier")
    parser.add_argument("--api-key", default=None, help="API Key for selected provider")

    args = parser.parse_args()
    run_pipeline(
        mode=args.mode,
        category=args.category,
        location=args.location,
        csv_file=Path(args.csv),
        limit=args.limit,
        llm_provider=args.provider,
        llm_model=args.model,
        api_key=args.api_key
    )

if __name__ == "__main__":
    main()
