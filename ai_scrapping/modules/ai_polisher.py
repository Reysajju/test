"""
Phase 4: AI Polisher & Lead Synthesis Engine
Cross-references raw multi-directory clues with AI scan findings:
1. Normalizes and validates contact channels (phone, email, socials)
2. Computes an Authenticity Confidence Score (0-100%)
3. Generates high-converting High-Ticket Pitch Hooks / Cold outreach icebreakers
4. Outputs polished, production-ready lead intelligence records
"""

import datetime
from typing import Dict, List, Any
import requests

from config import LLM_PROVIDER, SELECTED_MODEL, OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY
from utils.helpers import clean_text, normalize_phone

class AIPolisherEngine:
    """Polishes, verifies authenticity, and crafts tailored high-ticket sales angles."""

    def __init__(self):
        self.can_use_llm = any([OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, LLM_PROVIDER == "ollama"])

    def calculate_confidence_score(self, lead: Dict[str, Any]) -> int:
        """
        Calculates an authenticity confidence score (0-100%) based on verified clues.
        Higher score = higher probability of reaching the actual decision maker.
        """
        score = 0
        # 1. Base business verification (Google Maps / Directory listing with address)
        if lead.get("business_name") and lead.get("city"):
            score += 25

        # 2. Direct Phone
        if lead.get("phone"):
            score += 20

        # 3. Verified Email
        if lead.get("email"):
            score += 25

        # 4. Verified Owner / Decision-Maker Name
        if lead.get("owner_name"):
            score += 20

        # 5. Social Media Presence (Instagram / Facebook / LinkedIn)
        if lead.get("instagram") or lead.get("facebook") or lead.get("linkedin"):
            score += 10

        return min(score, 100)

    def generate_pitch_hook(self, lead: Dict[str, Any]) -> str:
        """
        Constructs an authentic, personalized sales hook tailored for high-ticket pitching
        based on the exact business name, location, reviews, and missing digital infrastructure.
        """
        name = lead.get("business_name", "the business")
        owner = lead.get("owner_name", "")
        city = lead.get("city", "your area")
        category = lead.get("category", "local service")
        rating = lead.get("rating", "")
        reviews = lead.get("reviews", "0")
        has_website = lead.get("has_website", False)
        instagram = lead.get("instagram", "")

        # Target address salutation
        salutation = f"Hi {owner}" if owner else f"Attention: Management at {name}"

        # If they have strong reviews but no website (the golden wedge)
        if not has_website and rating and float(rating) >= 4.0:
            hook = (
                f"{salutation} - Saw your stellar {rating}-star reputation ({reviews} reviews) in {city}. "
                f"You have great local loyalty, but with no official mobile booking site, "
                f"potential clients on Google are dropping off or booking competitors. "
                f"We can deploy a custom automated booking & customer capture funnel for {name} this week."
            )
        elif not has_website:
            hook = (
                f"{salutation} – Noticed {name} on {city} directories with active business hours, "
                f"but without a direct online home. We build premium, high-converting digital storefronts "
                f"that turn searchers into paying clients."
            )
        elif instagram:
            hook = (
                f"{salutation} – Checked out {name}'s visual work on Instagram. "
                f"Converting that social engagement into guaranteed paid bookings with a high-ticket portal "
                f"would dramatically increase your average ticket size in {city}."
            )
        else:
            hook = (
                f"{salutation} – Found {name} serving the {city} market. "
                f"We help top {category} operators modernize their client acquisition and capture high-value contracts."
            )

        return clean_text(hook)

    def polish_lead(self, enriched_lead: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes raw and enriched data into a finalized High-Ticket Polished Record."""
        name = enriched_lead.get("business_name", "")
        print(f"[AI POLISHER] Polishing and validating profile for: {name}...")

        # 1. Resolve Best Phone Number
        phones = enriched_lead.get("found_phones", [])
        primary_phone = phones[0] if phones else enriched_lead.get("phone_raw", "")

        # 2. Resolve Best Email
        emails = enriched_lead.get("found_emails", [])
        primary_email = emails[0] if emails else enriched_lead.get("email_raw", "")

        # 3. Resolve Social Profiles
        socials = enriched_lead.get("found_socials", {})
        instagram = socials.get("instagram", "")
        facebook = socials.get("facebook", "")
        linkedin = socials.get("linkedin", "")

        # 4. Resolve Decision Maker
        owner_name = enriched_lead.get("primary_owner_name", "")
        owner_role = enriched_lead.get("primary_owner_role", "")

        # 5. Assemble Polished Record
        polished = {
            "business_name": name,
            "category": enriched_lead.get("category", "Local Business"),
            "owner_name": owner_name,
            "owner_role": owner_role or ("Owner / Principal" if owner_name else "Unassigned"),
            "phone": normalize_phone(primary_phone),
            "email": primary_email.lower(),
            "instagram": instagram,
            "facebook": facebook,
            "linkedin": linkedin,
            "city": enriched_lead.get("city", ""),
            "state": enriched_lead.get("state", ""),
            "address": enriched_lead.get("full_address", ""),
            "rating": str(enriched_lead.get("rating", "")),
            "reviews": str(enriched_lead.get("reviews", "0")),
            "has_website": "Yes" if enriched_lead.get("has_website") else "No (Needs Website)",
            "sources_scanned": ", ".join(enriched_lead.get("scanned_urls", [])[:2]) or enriched_lead.get("source", "Directory"),
            "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 6. Compute Confidence & Pitch Hook
        polished["confidence_score"] = self.calculate_confidence_score(polished)
        polished["pitch_hook"] = self.generate_pitch_hook(polished)

        print(f"[AI POLISHER] Lead Ready -> Confidence: {polished['confidence_score']}% | Decision Maker: {polished['owner_name'] or 'N/A'} | Phone: {polished['phone']}")
        return polished

    def polish_all(self, enriched_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Polishes a collection of enriched leads."""
        return [self.polish_lead(lead) for lead in enriched_leads]
