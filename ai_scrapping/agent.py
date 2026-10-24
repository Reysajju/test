"""
AI Lead Mining Strategist & Autonomous Department Supervisor
Interactive workflow:
1. Verifies OpenRouter API Key and fetches live free models to select from.
2. Consults with the user in natural language, asking clarifying follow-up questions.
3. Automatically formalizes mission parameters.
4. Hands over the mission 100% autonomously to the Scraping Department.
"""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output across Windows CMD / PowerShell
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import BASE_DIR, OPENROUTER_API_KEY
from utils.openrouter_client import fetch_openrouter_free_models, ask_openrouter
from pipeline import run_pipeline

ENV_PATH = BASE_DIR / ".env"

def print_header(title: str):
    print("\n" + "=" * 74)
    print(f"  {title}")
    print("=" * 74)

def ensure_openrouter_key() -> str:
    """Verifies existing API key or prompts the user and saves it to .env."""
    load_dotenv(ENV_PATH)
    key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not key:
        print_header("🔑 OPENROUTER FREE API KEY SETUP")
        print("To run with 100% free models, please enter your OpenRouter API Key.")
        print("(You can generate a free key instantly at: https://openrouter.ai/keys)\n")
        user_key = input("Paste your OpenRouter API Key: ").strip()
        while not user_key:
            user_key = input("API Key cannot be empty. Please paste your OpenRouter key: ").strip()

        key = user_key
        # Append or update .env
        env_content = ""
        if ENV_PATH.exists():
            env_content = ENV_PATH.read_text(encoding="utf-8")
        if "OPENROUTER_API_KEY" in env_content:
            env_content = re.sub(r'OPENROUTER_API_KEY=.*', f'OPENROUTER_API_KEY={key}', env_content)
        else:
            env_content += f"\nOPENROUTER_API_KEY={key}\n"
        ENV_PATH.write_text(env_content, encoding="utf-8")
        print("✅ OpenRouter API Key saved successfully to .env!\n")

    return key

def select_free_model() -> str:
    """Fetches live free models from OpenRouter and lets the user pick."""
    print_header("🌐 FETCHING LIVE FREE MODELS FROM OPENROUTER")
    print("Connecting to OpenRouter models catalog...\n")

    free_models = fetch_openrouter_free_models()
    if not free_models:
        print("⚠️ Warning: Could not fetch live models. Falling back to default free model.")
        return "meta-llama/llama-3.3-70b-instruct:free"

    # Display top 10 free models
    display_count = min(10, len(free_models))
    for i in range(display_count):
        m = free_models[i]
        rec = " ⭐ (Recommended)" if i == 0 else ""
        print(f"  [{i + 1}] {m['id']}{rec}")
        print(f"      Ctx: {m.get('context_length', 8192)} tokens | {m.get('name')}")

    print("-" * 74)
    choice = input(f"\nSelect a model number [1-{display_count}] (Default: 1): ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < display_count:
            selected = free_models[idx]["id"]
        else:
            selected = free_models[0]["id"]
    except Exception:
        selected = free_models[0]["id"]

    print(f"\n🎯 Selected Active AI Model: {selected}\n")
    return selected

def extract_mission_json(text: str) -> dict:
    """Parses JSON specification emitted by the AI supervisor."""
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m2 = re.search(r'\{[^{}]*"category"[^{}]*\}', text, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(0))
        except Exception:
            pass
    return {}

def run_agent_loop():
    """Main interactive consultation and autonomous dispatch loop."""
    print("""
========================================================================
     🤖 ANTIGRAVITY AI LEAD STRATEGIST & AUTOMATED SCRAPER
========================================================================
  1. Connects to OpenRouter Free API
  2. Consults with you on what business data you need
  3. Formulates the high-ticket qualification criteria
  4. Hands over 100% autonomously to the Scraping Department
========================================================================
""")

    api_key = ensure_openrouter_key()
    selected_model = select_free_model()

    system_prompt = (
        "You are the Antigravity Lead Gen Director & B2B Data Mining Strategist.\n"
        "The system operates on an authentic Two-Stage Mass Lead Generation Pipeline:\n"
        "Stage 1 [Mass Scraping Engine]: Systematic Google Maps Playwright Crawler that crawls US counties "
        "targeting up to 10,000 authentic local businesses per state (Strictly: Must have Phone + Business Hours + Active Reviews, but NO website).\n"
        "Stage 2 [AI Department Handover]: Only when mass scraping is done (or using existing mass leads in leads.csv), "
        "the raw business records are handed over to ScrapeGraphAI & the AI enrichment department to find Owner names (State Secretary of State filings), "
        "verified emails, social profiles (Instagram/Facebook), and tailored high-ticket pitch hooks.\n\n"
        "Determine the user's desired operation:\n"
        "1. category: Target niche (e.g. 'hair salons', 'barber shops', 'dental clinics', 'roofing').\n"
        "2. location: Target state or city/state (e.g. 'Maine', 'Florida', 'Boston, MA', 'Dallas, TX').\n"
        "3. limit: 0 for MASS MODE (all leads up to state quota 10,000), or a specific number if testing.\n"
        "4. mode: 'mass-enrich' (handover existing 1,242+ Google Maps leads to AI), or 'mass-scrape' (run Google Maps crawler first then handover to AI).\n\n"
        "Rules:\n"
        "- First, listen to what they need.\n"
        "- If they want mass scraping, confirm that Stage 1 (Google Maps 10,000 per state) will harvest raw leads first, then automatically handover to AI.\n"
        "- Output a final JSON block formatted like:\n"
        "```json\n"
        '{\n'
        '  "ready_to_deploy": true,\n'
        '  "category": "<category>",\n'
        '  "location": "<location>",\n'
        '  "limit": 0,\n'
        '  "mode": "mass-enrich",\n'
        '  "pitch_focus": "<short description of sales pitch angle>"\n'
        '}\n'
        "```\n"
        "- Keep responses professional, direct, and concise."
    )

    conversation = [
        {"role": "system", "content": system_prompt}
    ]

    print_header("💬 CONSULTATION: WHAT BUSINESS LEADS DO YOU NEED?")
    print("Tell the AI what clients you are hunting for.")
    print("Example: 'I need dental clinics in Chicago with good reviews but no booking site, need owner details and emails.'\n")

    user_input = input("👤 You: ").strip()
    while not user_input:
        user_input = input("Please describe what data you need: ").strip()

    conversation.append({"role": "user", "content": user_input})

    # Consultation loop
    mission_spec = None
    for turn in range(4):  # At most 4 interactive turns to prevent endless loop
        print("\n🤖 AI Strategist is analyzing requirements...\n")
        ai_reply = ask_openrouter(conversation, selected_model, api_key)

        print(f"🤖 AI Strategist:\n{ai_reply}\n")
        conversation.append({"role": "assistant", "content": ai_reply})

        # Check if AI emitted deployment JSON
        mission_spec = extract_mission_json(ai_reply)
        if mission_spec.get("ready_to_deploy"):
            break

        followup_input = input("👤 You (or type 'start' to deploy now): ").strip()
        if not followup_input or followup_input.lower() in ["start", "deploy", "go", "yes", "proceed"]:
            # Prompt AI to finalize JSON now
            conversation.append({
                "role": "user",
                "content": "Everything looks good. Please finalize the parameters and output the deployment JSON block now."
            })
            final_reply = ask_openrouter(conversation, selected_model, api_key)
            print(f"\n🤖 AI Strategist:\n{final_reply}\n")
            mission_spec = extract_mission_json(final_reply)
            break
        else:
            conversation.append({"role": "user", "content": followup_input})

    # Default fallback if LLM failed to emit clean JSON
    if not mission_spec:
        mission_spec = {
            "category": "barber shops",
            "location": "Eastern US",
            "limit": 0,
            "mode": "mass-enrich",
            "pitch_focus": "Automated online client booking & mobile modernization"
        }

    category = mission_spec.get("category", "barber shops")
    location = mission_spec.get("location", "Eastern US")
    limit = int(mission_spec.get("limit", 0))
    mode = mission_spec.get("mode", "mass-enrich")
    pitch_focus = mission_spec.get("pitch_focus", "Digital modernization")

    no_website_only = bool(mission_spec.get("no_website_only", False))

    quota_display = "ALL LEADS (Mass Scale - Up to 10,000 per State)" if limit == 0 else f"{limit} leads"
    filter_display = "Strictly No Website (Pitching Websites)" if no_website_only else "All Active Businesses"

    print_header("📋 FINAL MISSION PARAMETERS LOCKED")
    print(f"  • Target Category:    {category}")
    print(f"  • Target Location:    {location}")
    print(f"  • Lead Quota:         {quota_display}")
    print(f"  • Website Filter:     {filter_display}")
    print(f"  • Scraping Engine:    {mode.upper()} mode")
    print(f"  • Pitch Focus:        {pitch_focus}")
    print(f"  • AI Model Deployed:  {selected_model}")
    print("=" * 74)
    print("\n🚀 100% AUTOMATED HANDOVER: DEPLOYING THE SCRAPING DEPARTMENT...\n")

    # Autonomous execution
    run_pipeline(
        mode=mode,
        category=category,
        location=location,
        limit=limit,
        llm_provider="openrouter",
        llm_model=selected_model,
        api_key=api_key,
        no_website_only=no_website_only
    )

if __name__ == "__main__":
    run_agent_loop()
