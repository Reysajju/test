"""
Google Maps Playwright Crawler Module
Directly extracts authentic local businesses from Google Maps:
1. Systematic scrolling of Google Maps results feed
2. Strict filter: Targets businesses with Phone + Active Reviews + NO Website
3. High performance: Blocks images/media/fonts for fast extraction
4. Returns authentic local business profiles (never blog posts or directory listicles)
"""

import time
import random
import urllib.parse
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

from utils.helpers import clean_text, normalize_phone, parse_address_components

class GoogleMapsCrawler:
    """Headless Playwright scraper tailored for Google Maps local business harvesting."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def crawl_google_maps(
        self,
        category: str,
        location: str,
        quota: int = 10,
        no_website_only: bool = True,
        min_reviews: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Crawls Google Maps for the specified category and location.
        Collects up to quota genuine businesses.
        """
        leads = []
        query = f"{category} in {location}"
        encoded_query = urllib.parse.quote_plus(query)
        target_url = f"https://www.google.com/maps/search/{encoded_query}?hl=en&gl=us"

        print(f"\n[MAPS CRAWLER] Launching Playwright Chromium...")
        print(f"[MAPS CRAWLER] Target Query: '{query}'")
        print(f"[MAPS CRAWLER] Quota: {quota if quota > 0 else 'All Available'} leads | Filter: {'Strictly No Website' if no_website_only else 'All Businesses'}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                locale="en-US",
                viewport={"width": 1366, "height": 900}
            )

            # Block heavy images, media, and fonts for maximum performance
            def route_interceptor(route):
                req = route.request
                if req.resource_type in ["image", "media", "font"]:
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", route_interceptor)
            page = context.new_page()

            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(2)

                # Handle Google consent dialog if presented
                try:
                    consent_btn = page.locator('button:has-text("Accept all"), button:has-text("I agree"), button:has-text("Reject all")').first
                    if consent_btn.is_visible(timeout=2000):
                        consent_btn.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Check if rate-limited or blocked
                if "sorry" in page.url or page.locator('iframe[src*="recaptcha"]').count() > 0:
                    print("[MAPS CRAWLER] Notice: Google presented verification. Pausing briefly...")
                    time.sleep(5)

                feed = page.locator('div[role="feed"]')
                try:
                    feed.wait_for(timeout=12000)
                except Exception:
                    print("[MAPS CRAWLER] No Google Maps results feed found for this query.")
                    browser.close()
                    return leads

                # Scroll results feed to load candidate cards
                print("[MAPS CRAWLER] Scrolling results feed to gather candidate business cards...")
                last_count = 0
                stale_scrolls = 0
                max_scrolls = 20 if quota <= 20 else min(50, quota // 2 + 5)

                for i in range(max_scrolls):
                    feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                    time.sleep(random.uniform(0.7, 1.2))

                    count = page.locator('div[role="feed"] a[href*="/maps/place/"]').count()
                    ended = page.locator('text=/you.?ve reached the end of the list/i').is_visible()
                    if ended:
                        print("[MAPS CRAWLER] Reached end of the Google Maps list.")
                        break

                    if count == last_count:
                        stale_scrolls += 1
                    else:
                        stale_scrolls = 0
                    last_count = count

                    if stale_scrolls >= 3:
                        break

                    if quota > 0 and count >= quota * 2:
                        break

                # Extract candidate links and card flags from feed
                candidates = page.evaluate("""
                    () => {
                        const out = [];
                        const links = document.querySelectorAll('div[role="feed"] a[href*="/maps/place/"]');
                        links.forEach(a => {
                            const card = a.closest('div.Nv2PK') || a.parentElement?.parentElement || a.parentElement;
                            const hasWebsite = !!(card && card.querySelector('a[data-value="Website"], a[aria-label*="website" i]'));
                            const label = (card && card.querySelector('span[role="img"]')) ? card.querySelector('span[role="img"]').getAttribute('aria-label') : '';
                            const m = label ? label.match(/([\\d,]+)\\s+review/i) : null;
                            const reviews = m ? parseInt(m[1].replace(/,/g, ''), 10) : null;
                            out.push({
                                href: a.href,
                                hasWebsite: hasWebsite,
                                reviews: reviews
                            });
                        });
                        return out;
                    }
                """)

                print(f"[MAPS CRAWLER] Identified {len(candidates)} candidate business cards.")

                # Filter candidates
                filtered_candidates = []
                seen_hrefs = set()
                for c in candidates:
                    href = c.get("href", "")
                    if href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)

                    # Strict qualification: website filter
                    if no_website_only and c.get("hasWebsite"):
                        continue
                    # Only discard if review count is explicitly known and less than min_reviews
                    if min_reviews > 0 and c.get("reviews") is not None and c.get("reviews") < min_reviews:
                        continue
                    filtered_candidates.append(c)

                print(f"[MAPS CRAWLER] {len(filtered_candidates)} candidates passed card qualification.")

                # Visit individual candidate listing pages to extract full details
                detail_page = context.new_page()
                target_count = quota if quota > 0 else len(filtered_candidates)

                for idx, cand in enumerate(filtered_candidates[:target_count], 1):
                    href = cand["href"]
                    try:
                        detail_page.goto(href, wait_until="domcontentloaded", timeout=12000)
                        detail_page.locator("h1").first.wait_for(timeout=6000)
                        time.sleep(random.uniform(0.4, 0.8))

                        # Evaluate listing DOM
                        data = detail_page.evaluate("""
                            () => {
                                const txt = (el) => el?.innerText?.replace(/\\s+/g, ' ').trim() || '';
                                const aria = (sel, prefix) => {
                                    const v = document.querySelector(sel)?.getAttribute('aria-label') || '';
                                    return v.replace(new RegExp(`^${prefix}:?\\\\s*`, 'i'), '').trim();
                                };

                                const name = txt(document.querySelector('h1.DUwDvf') || document.querySelector('h1'));
                                const category = txt(document.querySelector('button[jsaction*="category"]')) || 'Local Business';
                                const address = aria('[data-item-id="address"]', 'Address');
                                const phone = aria('[data-item-id^="phone"]', 'Phone');
                                const website = document.querySelector('[data-item-id="authority"]')?.getAttribute('href') || '';

                                const header = txt(document.querySelector('div.F7nice'));
                                let rating = (header.match(/^(\\d\\.\\d)/) || [])[1] || '';
                                let reviews = (header.match(/\\(([\\d,]+)\\)/) || [])[1] || '';

                                const days = /(mon|tue|wed|thu|fri|sat|sun)/i;
                                let hours = [...document.querySelectorAll('table tr')].map(txt).filter(r => days.test(r)).join('; ');
                                if (!hours) hours = aria('[data-item-id="oh"]', '') || '';

                                return { name, category, address, phone, website, rating, reviews, hours };
                            }
                        """)

                        name = clean_text(data.get("name"))
                        phone = normalize_phone(data.get("phone"))
                        address = clean_text(data.get("address"))

                        # A genuine lead MUST have a business name and phone number
                        if name and phone:
                            parsed_addr = parse_address_components(address)
                            city = parsed_addr.get("city") or location.split(",")[0].strip()
                            state = parsed_addr.get("state") or (location.split(",")[1].strip() if "," in location else "")

                            lead = {
                                "business_name": name,
                                "category": data.get("category") or category.title(),
                                "phone_raw": phone,
                                "email_raw": "",
                                "full_address": address,
                                "city": city,
                                "state": state,
                                "zip": parsed_addr.get("zip", ""),
                                "rating": data.get("rating", ""),
                                "reviews": data.get("reviews", "0"),
                                "source": "google_maps_playwright",
                                "source_url": href,
                                "has_website": bool(data.get("website")),
                            }
                            leads.append(lead)
                            print(f"  ★ [LEAD #{len(leads)}] {name} | Phone: {phone} | {city}, {state} ({lead['reviews']} reviews)")

                            if quota > 0 and len(leads) >= quota:
                                break
                    except Exception as e:
                        pass

                detail_page.close()

            except Exception as e:
                print(f"[MAPS CRAWLER] Error during crawl: {e}")
            finally:
                browser.close()

        print(f"\n[MAPS CRAWLER] Crawling finished! Successfully harvested {len(leads)} genuine local businesses.")
        return leads
