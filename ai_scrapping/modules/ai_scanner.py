"""
Phase 2: AI Multi-Page Deep Scanner (ScrapeGraphAI + Fallback Headless Engine)
Takes raw leads, locates public online footprints (Facebook, Instagram, Yelp, directories),
and scans pages for several seconds using AI to unearth:
- Potential mobile & direct phone numbers
- Verified business / inbox emails
- Social media profiles (Instagram, Facebook, LinkedIn)
- Business offerings and context clues
"""

import re
import time
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

from config import get_scrapegraph_config, LLM_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, AI_SCAN_TIMEOUT
from utils.helpers import clean_text, extract_emails, extract_social_links, normalize_phone, random_delay

# Try loading ScrapeGraphAI & Custom B2B Graph
_SCRAPEGRAPH_AVAILABLE = False
try:
    from scrapegraphai.graphs import SmartScraperGraph, B2BLeadGraph
    _SCRAPEGRAPH_AVAILABLE = True
except ImportError:
    try:
        from scrapegraphai.graphs import SmartScraperGraph
        _SCRAPEGRAPH_AVAILABLE = True
        B2BLeadGraph = None
    except ImportError:
        _SCRAPEGRAPH_AVAILABLE = False
        B2BLeadGraph = None

# Prefer ddgs directly to avoid rename warnings
_DDGS_AVAILABLE = False
try:
    from ddgs import DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDGS_AVAILABLE = True
    except ImportError:
        _DDGS_AVAILABLE = False


class AIScannerEngine:
    """Multi-page deep scanner powered by ScrapeGraphAI with resilient fallback."""

    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        import os
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        })
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openrouter")).lower()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "") or OPENAI_API_KEY or GEMINI_API_KEY or GROQ_API_KEY
        self.model = model or os.getenv("OPENROUTER_MODEL", "")
        self.can_use_ai = _SCRAPEGRAPH_AVAILABLE and (bool(self.api_key) or self.provider == "ollama")

    def find_web_footprint(self, name: str, city: str, state: str, max_links: int = 4) -> List[str]:
        """Discovers public pages for the business using free search queries."""
        links = []
        query = f'"{name}" "{city}" "{state}"'

        if _DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_links + 2))
                    for r in results:
                        href = r.get("href") or r.get("link", "")
                        # Filter out major search aggregate portals and foreign ccTLDs
                        junk_domains = ["google.com", "bing.com", "yahoo.com", "duckduckgo.com", ".pk", ".in", ".ru", ".cn", ".br", ".de"]
                        if href and not any(d in href for d in junk_domains):
                            links.append(href)
                            if len(links) >= max_links:
                                break
            except Exception as e:
                print(f"[AI SCANNER] DuckDuckGo search fallback: {e}")

        # Fallback query directly via DuckDuckGo HTML endpoint if library fails
        if not links:
            try:
                resp = self.session.get(
                    f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}",
                    timeout=8
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.select("a.result__url"):
                        href = a.get("href", "").strip()
                        if href.startswith("http"):
                            links.append(href)
                            if len(links) >= max_links:
                                break
            except Exception:
                pass

        return links

    def scan_page_with_ai(self, url: str) -> Optional[Dict[str, Any]]:
        """Invokes ScrapeGraphAI SmartScraperGraph on a target page."""
        if not self.can_use_ai:
            return None

        prompt = (
            "Extract business contact details from this page: "
            "1. All direct/owner email addresses. "
            "2. Direct phone numbers. "
            "3. Social media profiles (Instagram, Facebook, LinkedIn, TikTok). "
            "4. A 1-sentence summary of what they offer."
        )

        try:
            print(f"[AI SCANNER] Running ScrapeGraphAI ({self.model or 'Default'}) on: {url[:60]}...")
            config = get_scrapegraph_config(provider=self.provider, api_key=self.api_key, model=self.model)
            if B2BLeadGraph:
                graph = B2BLeadGraph(source=url, config=config)
            else:
                graph = SmartScraperGraph(prompt=prompt, source=url, config=config)
            res = graph.run()
            if isinstance(res, dict):
                return res
        except Exception as e:
            print(f"[AI SCANNER] ScrapeGraphAI run notice: {e}")

        return None

    def scan_page_fast_heuristics(self, url: str) -> Dict[str, Any]:
        """Scans page content for contact clues using DOM parsing and regex."""
        out = {"emails": [], "phones": [], "socials": {}, "text_snippet": ""}
        try:
            resp = self.session.get(url, timeout=AI_SCAN_TIMEOUT)
            if resp.status_code == 200:
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                # Remove script and style noise
                for s in soup(["script", "style", "noscript"]):
                    s.extract()
                text = soup.get_text(separator=" ")

                out["emails"] = extract_emails(html + " " + text)
                out["socials"] = extract_social_links(html)

                # Look for phone patterns
                phone_matches = re.findall(r'\(?\b[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', text)
                out["phones"] = [normalize_phone(p) for p in phone_matches if normalize_phone(p)][:3]
                out["text_snippet"] = clean_text(text[:300])
        except Exception:
            pass

        return out

    def enrich_lead(self, raw_lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a raw business lead and executes multi-page scanning for several seconds
        to harvest emails, phone numbers, and social channels.
        """
        name = raw_lead.get("business_name", "")
        city = raw_lead.get("city", "")
        state = raw_lead.get("state", "")

        enriched = dict(raw_lead)
        enriched["found_emails"] = []
        enriched["found_phones"] = []
        enriched["found_socials"] = {}
        enriched["scanned_urls"] = []
        enriched["ai_insights"] = ""

        # Include raw phone
        if raw_lead.get("phone_raw"):
            enriched["found_phones"].append(raw_lead["phone_raw"])
        if raw_lead.get("email_raw"):
            enriched["found_emails"].append(raw_lead["email_raw"])

        # 1. Discover online footprint links
        print(f"\n[AI SCANNER] Hunting online clues for: '{name}' in {city}, {state}...")
        footprint_urls = self.find_web_footprint(name, city, state, max_links=3)
        enriched["scanned_urls"] = footprint_urls

        # 2. Multi-page scan
        for url in footprint_urls:
            print(f"[AI SCANNER] Scanning page: {url[:70]}")
            # Try AI extraction first if enabled
            ai_data = self.scan_page_with_ai(url)
            if ai_data:
                # Merge AI results
                if isinstance(ai_data.get("emails"), list):
                    enriched["found_emails"].extend(ai_data["emails"])
                elif isinstance(ai_data.get("email"), str) and ai_data["email"]:
                    enriched["found_emails"].append(ai_data["email"])

                if isinstance(ai_data.get("phones"), list):
                    enriched["found_phones"].extend(ai_data["phones"])
                elif isinstance(ai_data.get("phone"), str) and ai_data["phone"]:
                    enriched["found_phones"].append(ai_data["phone"])

                if isinstance(ai_data.get("social_media_links"), dict):
                    enriched["found_socials"].update(ai_data["social_media_links"])
                elif isinstance(ai_data.get("socials"), dict):
                    enriched["found_socials"].update(ai_data["socials"])

                if ai_data.get("description"):
                    enriched["ai_insights"] = clean_text(str(ai_data["description"]))

            # Always run heuristic extractor as complementary safety net
            h_data = self.scan_page_fast_heuristics(url)
            enriched["found_emails"].extend(h_data["emails"])
            enriched["found_phones"].extend(h_data["phones"])
            enriched["found_socials"].update(h_data["socials"])
            if not enriched["ai_insights"] and h_data["text_snippet"]:
                enriched["ai_insights"] = h_data["text_snippet"]

            # Small polite pause
            time.sleep(1.0)

        # Clean and deduplicate findings
        enriched["found_emails"] = list(dict.fromkeys(extract_emails(" ".join(enriched["found_emails"]))))
        enriched["found_phones"] = list(dict.fromkeys([normalize_phone(p) for p in enriched["found_phones"] if normalize_phone(p)]))

        print(f"[AI SCANNER] Clues Harvested -> Emails: {len(enriched['found_emails'])}, Phones: {len(enriched['found_phones'])}, Socials: {list(enriched['found_socials'].keys())}")
        return enriched
