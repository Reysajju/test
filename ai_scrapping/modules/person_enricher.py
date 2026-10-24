"""
Phase 3: Personal & Decision-Maker Discovery Engine
Leverages free public business registries and public profile sources to identify:
1. OpenCorporates (State Secretary of State corporate filings & registered officers)
2. Better Business Bureau (BBB) Principal Management public profiles
3. Public Executive Search (DuckDuckGo snippets for Owner, Founder, President)
4. Manta / Directory executive listings
"""

import re
import urllib.parse
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

from config import USER_AGENTS, REQUEST_TIMEOUT
from utils.helpers import clean_text, random_delay

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


class PersonEnricherEngine:
    """Finds authentic decision-maker names, titles, and public officer filings."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        })

    # ---------------------------------------------------------------------------
    # 1. OpenCorporates Public Registry (Free)
    # ---------------------------------------------------------------------------
    def search_opencorporates(self, business_name: str, state: str) -> List[Dict[str, str]]:
        """
        Queries OpenCorporates public search to identify registered corporate officers,
        managers, and owners filed with state authorities.
        """
        officers = []
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name).strip()
        encoded_query = urllib.parse.quote_plus(clean_name)
        url = f"https://opencorporates.com/companies?q={encoded_query}&utf8=%E2%9C%93"

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select("ul.companies li.company")

                for r in results[:2]:  # Check top 2 matching companies
                    comp_name_el = r.select_one("a.company_search_result")
                    jurisdiction_el = r.select_one(".jurisdiction")
                    jur_text = clean_text(jurisdiction_el.text) if jurisdiction_el else ""

                    # State check if available (e.g. us_me, us_ny)
                    if state and f"us_{state.lower()}" not in jur_text.lower() and "us" not in jur_text.lower():
                        continue

                    detail_url = f"https://opencorporates.com{comp_name_el.get('href', '')}" if comp_name_el else None
                    if detail_url:
                        # Inspect company filing page for officers
                        det_resp = self.session.get(detail_url, timeout=REQUEST_TIMEOUT)
                        if det_resp.status_code == 200:
                            det_soup = BeautifulSoup(det_resp.text, "html.parser")
                            officer_rows = det_soup.select("#officers dl.attributes dd.officer, dl.officers dd")
                            for off in officer_rows:
                                text = clean_text(off.text)
                                # Example: "WAYNE SMITH, president" or "JANE DOE, agent"
                                parts = text.split(",")
                                name = parts[0].strip()
                                role = parts[1].strip() if len(parts) > 1 else "Officer"
                                if name and len(name.split()) >= 2:
                                    officers.append({
                                        "name": name.title(),
                                        "role": role.title(),
                                        "source": "OpenCorporates Registry"
                                    })
        except Exception as e:
            print(f"[PERSON ENRICHER] OpenCorporates search notice: {e}")

        return officers

    # ---------------------------------------------------------------------------
    # 2. Better Business Bureau (BBB) Public Profiles
    # ---------------------------------------------------------------------------
    def search_bbb(self, business_name: str, city: str, state: str) -> List[Dict[str, str]]:
        """Searches BBB public index for principal management."""
        officers = []
        query = f'"{business_name}" "{city}" "{state}" site:bbb.org "Principal Management"'

        if _DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=2))
                    for r in results:
                        body = r.get("body", "")
                        # Look for "Mr. John Smith, Owner" or "Jane Doe (Manager)"
                        m = re.search(r'(?:Mr\.|Ms\.|Mrs\.)?\s*([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:,|-|\()\s*(Owner|President|CEO|Founder|Manager|Director)', body, re.I)
                        if m:
                            officers.append({
                                "name": m.group(1).strip().title(),
                                "role": m.group(2).strip().title(),
                                "source": "BBB Public Profile"
                            })
            except Exception:
                pass
        return officers

    # ---------------------------------------------------------------------------
    # 3. Public Web & LinkedIn Snippet Discovery (DuckDuckGo)
    # ---------------------------------------------------------------------------
    def search_public_executive_snippets(self, business_name: str, city: str, state: str) -> List[Dict[str, str]]:
        """
        Queries free public search index for owner / founder mentions across
        local newspapers, chamber of commerce lists, and LinkedIn snippets.
        """
        officers = []
        queries = [
            f'"{business_name}" "{city}" (owner OR founder OR proprietor)',
            f'"{business_name}" "{city}" site:linkedin.com/in'
        ]

        if not _DDGS_AVAILABLE:
            return officers

        try:
            with DDGS() as ddgs:
                for q in queries:
                    results = list(ddgs.text(q, max_results=3))
                    for r in results:
                        title = r.get("title", "")
                        body = r.get("body", "")
                        combined = f"{title} | {body}"

                        # Regex for Name + Role
                        patterns = [
                            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–|:]\s*(Owner|Founder|Co-Founder|Proprietor|President|CEO)\s*(?:at|of|-|,)?\s*' + re.escape(business_name),
                            r'(Owner|Founder|Proprietor|President)\s*(?:of|at|,)?\s*' + re.escape(business_name) + r'[:,\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
                            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:the\s+)?(owner|founder|proprietor)\s+of\s+' + re.escape(business_name)
                        ]

                        for pat in patterns:
                            match = re.search(pat, combined, re.I)
                            if match:
                                g = match.groups()
                                if len(g) == 2:
                                    if any(r in g[0].lower() for r in ["owner", "founder", "proprietor", "president"]):
                                        role, name = g[0], g[1]
                                    else:
                                        name, role = g[0], g[1]

                                    if len(name.split()) >= 2 and not any(w in name.lower() for w in ["barber", "salon", "shop", "street", "city"]):
                                        officers.append({
                                            "name": name.strip().title(),
                                            "role": role.strip().title(),
                                            "source": "Public Directory / Web Snippet"
                                        })
                                        break
        except Exception as e:
            print(f"[PERSON ENRICHER] Web snippet search notice: {e}")

        return officers

    # ---------------------------------------------------------------------------
    # 4. Master Personal Enricher
    # ---------------------------------------------------------------------------
    def enrich_decision_maker(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the personal data discovery workflow and attaches decision-maker clues."""
        name = lead.get("business_name", "")
        city = lead.get("city", "")
        state = lead.get("state", "")

        print(f"\n[PERSON ENRICHER] Searching decision-maker records for: '{name}' in {city}, {state}...")
        enriched = dict(lead)
        candidates = []

        # 1. State Corporate Filings
        oc_results = self.search_opencorporates(name, state)
        candidates.extend(oc_results)

        # 2. BBB Profiles
        bbb_results = self.search_bbb(name, city, state)
        candidates.extend(bbb_results)

        # 3. Web & Executive Snippets
        web_results = self.search_public_executive_snippets(name, city, state)
        candidates.extend(web_results)

        # Deduplicate candidates
        unique_officers = []
        seen = set()
        for c in candidates:
            k = c.get("name", "").lower()
            if k and k not in seen:
                seen.add(k)
                unique_officers.append(c)

        enriched["decision_maker_candidates"] = unique_officers
        if unique_officers:
            enriched["primary_owner_name"] = unique_officers[0]["name"]
            enriched["primary_owner_role"] = unique_officers[0]["role"]
            enriched["owner_source"] = unique_officers[0]["source"]
            print(f"[PERSON ENRICHER] Found Primary Decision Maker: {unique_officers[0]['name']} ({unique_officers[0]['role']}) via {unique_officers[0]['source']}")
        else:
            enriched["primary_owner_name"] = ""
            enriched["primary_owner_role"] = ""
            enriched["owner_source"] = ""
            print(f"[PERSON ENRICHER] No explicit corporate registry officer found on free sources.")

        return enriched
