---
name: ecommerce-marketplace-auditor
description: >-
  Audits e-commerce listings (Amazon, Flipkart, Blinkit, Zepto, Swiggy Instamart) for Legal Metrology compliance.
  Use when crawling product listings, parsing JSON-LD product data, cross-verifying product images against text specifications, or detecting non-compliant online sellers.
---

# E-Commerce Marketplace Auditor for LMPC Compliance

Under the Consumer Protection (E-Commerce) Rules, 2020 and Legal Metrology (Packaged Commodities) Amendment Rules, all e-commerce entities in India must display all mandatory declarations on their digital product display pages.

## Audit Workflow

1. **Listing Data Ingestion:**
   - Extract schema.org `Product` JSON-LD from target URLs.
   - Extract DOM elements for "Important Information", "Manufacturer Details", "Technical Details", and "Ingredients/Specifications".
   - Collect all high-resolution product image URLs from the product image carousel.

2. **Cross-Modal Discrepancy Detection:**
   - **Step 1:** Run Vision OCR on the carousel packaging photos (especially back-of-pack images).
   - **Step 2:** Compare OCR extracted values against the webpage's textual specification table:
     - Is the MRP listed on the website equal to or lower than the packaging MRP? (Higher = Illegal overcharging).
     - Does the Country of Origin on the package match the listing?
     - Is Unit Sale Price (USP) visibly displayed on the search result & product page?
     - Are the Manufacturer / Packer / Importer details present in text before the consumer buys?

3. **Audit Scoring & Infraction Generation:**
   - Output structured compliance reports detailing:
     - Platform Name & Seller ID
     - Product SKU / ASIN / FSN
     - Identified Infractions with relevant sub-rules
     - Evidence screenshot & OCR crops
     - Pre-formatted Draft Notice to E-Commerce Entity / Seller.
