"""
SIH26034 — Agent 1: E-Commerce Marketplace Scraper Agent

Uses ScrapeGraphAI with Playwright to autonomously crawl e-commerce
product listings (Amazon, Flipkart, Blinkit, Zepto, Swiggy Instamart)
and extract product specifications, listed prices, and packaging images.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from scrapegraphai.graphs import SmartScraperGraph

from backend.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extraction prompt for ScrapeGraphAI
# ---------------------------------------------------------------------------

SCRAPER_PROMPT = """Extract the following product information from this e-commerce product page:

1. product_name: Full product title/name
2. brand: Brand name
3. listed_price: Current selling price in INR (number only)
4. mrp: Maximum Retail Price if shown separately (number only)
5. discount_percentage: Discount percentage if shown
6. net_quantity: Weight/volume/count as stated on the page (e.g., "500 g", "1 L")
7. manufacturer: Manufacturer or Packer name
8. manufacturer_address: Full address of manufacturer
9. country_of_origin: Country of origin
10. importer_details: Importer name and address (if imported product)
11. expiry_info: Expiry date or shelf life information
12. description: Product description text
13. ingredients: Ingredients list if available
14. product_images: List of ALL product image URLs (especially packaging/label images)
15. seller_name: Seller or retailer name
16. seller_rating: Seller rating if available
17. category: Product category (food, cosmetics, electronics, etc.)
18. fssai_license: FSSAI license number if displayed
19. customer_care: Customer care contact details if shown
20. unit_sale_price: Price per unit/gram/ml if displayed

Return all data as a structured JSON object. If a field is not found, set it to null."""


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORM_PATTERNS: dict[str, list[str]] = {
    "amazon": ["amazon.in", "amazon.co.in"],
    "flipkart": ["flipkart.com"],
    "blinkit": ["blinkit.com"],
    "zepto": ["zeptonow.com", "zepto.co.in"],
    "swiggy_instamart": ["swiggy.com/instamart"],
    "bigbasket": ["bigbasket.com", "bb.com"],
    "jiomart": ["jiomart.com"],
}


def detect_platform(url: str) -> str:
    """Detect the e-commerce platform from a URL."""
    domain = urlparse(url).netloc.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        if any(p in domain for p in patterns):
            return platform
    return "unknown"


class ScraperAgent:
    """
    Autonomously scrapes e-commerce product listings using ScrapeGraphAI
    and downloads packaging images for vision processing.
    """

    def __init__(self) -> None:
        self.download_dir = settings.UPLOAD_DIR / "scraped"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ScraperAgent initialized. Downloads → %s", self.download_dir)

    async def scrape_product(self, url: str) -> dict[str, Any]:
        """
        Scrape a product listing and download packaging images.

        Args:
            url: Full URL of the e-commerce product page.

        Returns:
            Dictionary containing:
                - platform: Detected platform name.
                - listing_data: Extracted product specifications.
                - downloaded_images: List of local paths to downloaded images.
        """
        platform = detect_platform(url)
        logger.info("Scraping %s product: %s", platform, url)

        # Configure ScrapeGraphAI with Gemini
        graph_config = {
            "llm": {
                "model": f"google_genai/{settings.GEMINI_MODEL}",
                "api_key": settings.GOOGLE_API_KEY,
                "temperature": 0.1,
            },
            "headless": True,
            "verbose": False,
        }

        try:
            # Run the AI-powered scraper
            scraper = SmartScraperGraph(
                prompt=SCRAPER_PROMPT,
                source=url,
                config=graph_config,
            )
            listing_data = scraper.run()

            if listing_data is None:
                listing_data = {}

            logger.info(
                "Scraped %d fields from %s listing.",
                len(listing_data),
                platform,
            )

            # Download product images for vision processing
            image_urls = listing_data.get("product_images") or []
            downloaded_images = await self._download_images(image_urls, platform)

            return {
                "platform": platform,
                "source_url": url,
                "listing_data": listing_data,
                "downloaded_images": downloaded_images,
            }

        except Exception as e:
            logger.error("Scraping failed for %s: %s", url, e)
            raise RuntimeError(f"Failed to scrape {platform} listing: {e}") from e

    async def _download_images(
        self,
        image_urls: list[str],
        platform: str,
        max_images: int = 5,
    ) -> list[str]:
        """
        Download product images for OCR processing.

        Args:
            image_urls: List of image URLs from the listing.
            platform: Platform name (for organizing downloads).
            max_images: Maximum number of images to download.

        Returns:
            List of local file paths to downloaded images.
        """
        downloaded: list[str] = []

        if not image_urls:
            logger.warning("No product images found in listing.")
            return downloaded

        # Prioritize back-of-pack / label images (larger, higher resolution)
        urls_to_download = image_urls[:max_images]

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for i, img_url in enumerate(urls_to_download):
                try:
                    # Clean up URL (remove resizing params for full resolution)
                    clean_url = self._get_full_res_url(img_url, platform)

                    response = await client.get(clean_url)
                    response.raise_for_status()

                    # Determine file extension
                    content_type = response.headers.get("content-type", "image/jpeg")
                    ext = ".jpg" if "jpeg" in content_type else ".png"

                    filename = f"{platform}_product_{i}{ext}"
                    filepath = self.download_dir / filename
                    filepath.write_bytes(response.content)
                    downloaded.append(str(filepath))

                    logger.debug("Downloaded image %d: %s", i, filename)

                except Exception as e:
                    logger.warning("Failed to download image %d: %s", i, e)
                    continue

        logger.info("Downloaded %d/%d product images.", len(downloaded), len(urls_to_download))
        return downloaded

    @staticmethod
    def _get_full_res_url(url: str, platform: str) -> str:
        """
        Attempt to get full-resolution image URL by removing
        platform-specific resize parameters.
        """
        if platform == "amazon":
            # Amazon: Replace ._SX300_ or ._SL500_ with ._SL1500_ for high-res
            url = re.sub(r"\._[A-Z]{2}\d+_", "._SL1500_", url)
        elif platform == "flipkart":
            # Flipkart: Replace /128/128/ dimensions with /832/832/
            url = re.sub(r"/\d+/\d+/", "/832/832/", url)
        return url


# Module-level singleton
scraper_agent = ScraperAgent()
