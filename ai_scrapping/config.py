"""
Configuration Module for AI Scrapping Pipeline
Manages LLM providers, search endpoints, directories, and operational parameters.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
ENRICHED_DIR = DATA_DIR / "enriched"
POLISHED_DIR = DATA_DIR / "polished"

for d in [RAW_DIR, ENRICHED_DIR, POLISHED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# LLM & ScrapeGraphAI Settings
# ---------------------------------------------------------------------------
# Supported providers: "openrouter", "openai", "gemini", "groq", "ollama", "anthropic"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Default model strings according to provider
DEFAULT_MODELS = {
    "openrouter": OPENROUTER_MODEL,
    "openai": "openai/gpt-4o-mini",
    "gemini": "google_genai/gemini-1.5-flash",
    "groq": "groq/llama-3.3-70b-versatile",
    "ollama": "ollama/llama3.2",
    "anthropic": "anthropic/claude-3-5-haiku-latest",
}

SELECTED_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODELS.get(LLM_PROVIDER, OPENROUTER_MODEL))

def get_scrapegraph_config(provider: str = None, api_key: str = None, model: str = None):
    """Builds the configuration dict required by ScrapeGraphAI."""
    prov = (provider or LLM_PROVIDER).lower()

    if prov == "openrouter":
        key = api_key or OPENROUTER_API_KEY
        m = model or OPENROUTER_MODEL
        return {
            "llm": {
                "model": f"openai/{m}",
                "base_url": OPENROUTER_BASE_URL,
                "api_key": key,
                "model_tokens": 8192,
            },
            "verbose": False,
            "headless": True,
        }

    cfg = {
        "llm": {
            "model": model or SELECTED_MODEL,
        },
        "verbose": False,
        "headless": True,
    }
    if prov == "openai" and (api_key or OPENAI_API_KEY):
        cfg["llm"]["api_key"] = api_key or OPENAI_API_KEY
    elif prov == "gemini" and (api_key or GEMINI_API_KEY):
        cfg["llm"]["api_key"] = api_key or GEMINI_API_KEY
    elif prov == "groq" and (api_key or GROQ_API_KEY):
        cfg["llm"]["api_key"] = api_key or GROQ_API_KEY
    elif prov == "ollama":
        cfg["llm"]["base_url"] = OLLAMA_HOST
    return cfg

# ---------------------------------------------------------------------------
# Free Data Sources & Endpoints
# ---------------------------------------------------------------------------
FREE_SOURCES = {
    "yellowpages": "https://www.yellowpages.com/search?search_terms={category}&geo_location_terms={location}",
    "superpages": "https://www.superpages.com/search?search_terms={category}&geo_location_terms={location}",
    "manta": "https://www.manta.com/search?search_source=nav&search={category}&search_location={location}",
    "opencorporates_web": "https://opencorporates.com/companies?q={name}",
    "opencorporates_api": "https://api.opencorporates.com/v0.4/companies/search?q={name}",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ---------------------------------------------------------------------------
# Scraping & Validation Thresholds
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 15  # seconds
MAX_RESULTS_PER_SEARCH = 20
AI_SCAN_TIMEOUT = 12  # seconds per page
DEFAULT_SEARCH_RADIUS = 25  # miles
