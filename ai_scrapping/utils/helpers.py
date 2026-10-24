"""
Helper Utilities for AI Scrapping Pipeline
Provides data sanitization, regex extractors, deduplication, and file handlers.
"""

import re
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

def clean_text(val: Optional[str]) -> str:
    """Removes irregular whitespace, non-printable characters, and strips edges."""
    if not val:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', str(val))
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_phone(phone: Optional[str]) -> str:
    """Normalizes phone number to standard US 10-digit / international format."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone.strip()

def extract_emails(text: Optional[str]) -> List[str]:
    """Finds and filters valid email addresses, dropping web framework / asset noise."""
    if not text:
        return []
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    candidates = re.findall(pattern, text)
    
    # Filter out common junk / placeholder domains
    junk_patterns = [
        r'google', r'gstatic', r'googleapis', r'schema\.org', r'w3\.org',
        r'sentry', r'example\.com', r'test\.com', r'yourdomain', r'domain\.com',
        r'sentry\.io', r'cloudflare', r'\.png$', r'\.jpg$', r'\.webp$', r'bootstrap'
    ]
    valid = []
    seen = set()
    for email in candidates:
        email_clean = email.lower().strip()
        if email_clean in seen:
            continue
        if any(re.search(jp, email_clean) for jp in junk_patterns):
            continue
        seen.add(email_clean)
        valid.append(email_clean)
    return valid

def extract_social_links(text: Optional[str]) -> Dict[str, str]:
    """Extracts social media profile links from text or HTML."""
    if not text:
        return {}
    socials = {}
    
    ig = re.findall(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)/?', text)
    if ig and ig[0] not in ['p', 'explore', 'reel', 'stories', 'accounts']:
        socials['instagram'] = f"https://www.instagram.com/{ig[0]}/"
        
    fb = re.findall(r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9._-]+)/?', text)
    if fb and fb[0] not in ['sharer', 'pages', 'groups', 'policies']:
        socials['facebook'] = f"https://www.facebook.com/{fb[0]}/"
        
    li = re.findall(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9._-]+)/?', text)
    if li:
        socials['linkedin'] = f"https://www.linkedin.com/in/{li[0]}/"
        
    return socials

def parse_address_components(address: str) -> Dict[str, str]:
    """Parses street, city, state, zip code from address strings."""
    res = {"street": "", "city": "", "state": "", "zip": ""}
    if not address:
        return res
    clean = re.sub(r',?\s*(United States|USA)$', '', address, flags=re.I).strip()
    parts = [p.strip() for p in clean.split(',') if p.strip()]
    
    # Check for State & Zip in last token
    if parts:
        last = parts[-1]
        m_state_zip = re.search(r'\b([A-Z]{2})\b(?:\s+(\d{5}(?:-\d{4})?))?', last)
        if m_state_zip:
            res["state"] = m_state_zip.group(1)
            res["zip"] = m_state_zip.group(2) or ""
            parts.pop()
    
    if parts:
        res["city"] = parts[-1]
        parts.pop()
        
    if parts:
        res["street"] = ", ".join(parts)
        
    return res

def save_json(filepath: Path, data: Any):
    """Safely saves data to JSON with UTF-8 encoding."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: Path) -> Any:
    """Loads JSON data or returns empty list/dict if not found."""
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def random_delay(min_sec: float = 1.0, max_sec: float = 2.5):
    """Polite randomised delay between external requests."""
    time.sleep(random.uniform(min_sec, max_sec))
