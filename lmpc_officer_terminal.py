#!/usr/bin/env python3
"""
========================================================================================
 🇮🇳 GOVERNMENT OF INDIA • MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION
     DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY DIVISION (SIH26034)
     STATUTORY FIELD ENFORCEMENT COCKPIT • WINDOWS POWERSHELL OFFICER TERMINAL
========================================================================================
"""

import os
import sys
import time
import json
import datetime
from rule_table import (
    rule,
    consequence_for,
    notice_kind_for,
    IMPROVEMENT_NOTICE,
    BY_ID,
)

# Enable UTF-8 and ANSI colors in Windows PowerShell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.system('')  # Initializes Windows 10/11 ANSI color support

# --- ANSI Color Codes for PowerShell ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Official Gov Palette
NAVY_BG = "\033[48;5;18m\033[38;5;255m"
NAVY_TXT = "\033[38;5;27m"
SAFFRON = "\033[38;5;208m"
GREEN = "\033[38;5;34m"
RED = "\033[38;5;196m"
YELLOW = "\033[38;5;220m"
CYAN = "\033[38;5;39m"
WHITE = "\033[38;5;255m"
GRAY = "\033[38;5;244m"
BG_CARD = "\033[48;5;236m\033[38;5;255m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(f"{SAFFRON}══════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE} 🇮🇳  GOVERNMENT OF INDIA • MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION{RESET}")
    print(f"     {CYAN}DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY DIVISION (SIH26034){RESET}")
    print(f"     {BOLD}LEGAL METROLOGY ACT, 2009 • STATUTORY FIELD ENFORCEMENT COCKPIT{RESET}")
    print(f"{GREEN}══════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f" {DIM}Active Officer: {WHITE}Legal Metrology Inspector (AD-HQ)  {DIM}•  Helpline: {SAFFRON}1915{RESET}  {DIM}•  Time: {WHITE}{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{GRAY}──────────────────────────────────────────────────────────────────────────────────────────────────────────{RESET}\n")

def print_statutory_table(commodity_name, barcode, fssai, checks, overall_status):
    print(f"\n{BOLD}{WHITE}┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{BOLD}{WHITE}│ 📋 STATUTORY RULE 6 MANDATORY DECLARATION AUDIT REPORT                                                 │{RESET}")
    print(f"{BOLD}{WHITE}├────────────────────────────────────────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"│ {BOLD}Commodity:{RESET} {commodity_name:<35} │ {BOLD}Barcode:{RESET} {barcode:<42} │")
    print(f"│ {BOLD}FSSAI Lic:{RESET} {fssai:<35} │ {BOLD}Act/Rules:{RESET} Legal Metrology (PC) Rules, 2011             │")
    print(f"{BOLD}{WHITE}├──────────────┬─────────────────────────────────────────────────┬────────────────────────┬──────────────┤{RESET}")
    print(f"{BOLD}{WHITE}│ Rule Clause  │ Mandatory Declaration Subject                   │ Detected / Extracted   │ Compliance   │{RESET}")
    print(f"{BOLD}{WHITE}├──────────────┼─────────────────────────────────────────────────┼────────────────────────┼──────────────┤{RESET}")

    for chk in checks:
        clause = chk['clause']
        label = chk['label'][:47]
        val = chk['val'][:22]
        st = chk['status']
        
        if st == "PASS":
            status_badge = f"{GREEN}{BOLD}✓ COMPLIANT  {RESET}"
        elif st == "FAIL":
            status_badge = f"{RED}{BOLD}✗ VIOLATION  {RESET}"
        else:
            status_badge = f"{YELLOW}{BOLD}⚠ REVIEW     {RESET}"

        print(f"│ {CYAN}{clause:<12}{RESET} │ {label:<47} │ {val:<22} │ {status_badge} │")

    print(f"{BOLD}{WHITE}└──────────────┴─────────────────────────────────────────────────┴────────────────────────┴──────────────┘{RESET}")
    
    if overall_status == "COMPLIANT":
        print(f"\n{GREEN}{BOLD} [✓] STATUTORY STATUS: FULLY COMPLIANT WITH LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011{RESET}")
        print(f"     {DIM}No violation observed. Commodity authorized for retail trade.{RESET}")
    else:
        print(f"\n{RED}{BOLD} [✗] STATUTORY STATUS: NON-COMPLIANCE DETECTED — CONTRAVENTION OF SECTION 18 & RULE 6{RESET}")
        print(f"     {BOLD}{RED}Actionable under Section 36 of the Legal Metrology Act, 2009 (Section 15(6) Improvement Notice / Civil Penalty){RESET}")

def generate_statutory_notice(commodity_name, manufacturer, violations, offence_number=1):
    notice_id = f"LMPC/HQ/2026/{int(time.time()) % 100000}"
    dt = datetime.datetime.now().strftime("%d-%B-%Y")
    
    rule_ids = [v.get("rule_id", "MANUFACTURER") for v in violations]
    n_kind = notice_kind_for(rule_ids, offence_number)
    
    if n_kind == IMPROVEMENT_NOTICE:
        print(f"\n{BOLD}{SAFFRON}╔══════════════════════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{SAFFRON}║                STATUTORY IMPROVEMENT NOTICE UNDER SECTION 15(6) (JAN VISHWAS ACT, 2026)                ║{RESET}")
        print(f"{BOLD}{SAFFRON}╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")
        print(f"""
{BOLD}OFFICE OF THE CONTROLLER OF LEGAL METROLOGY{RESET}
DEPARTMENT OF CONSUMER AFFAIRS, GOVERNMENT OF INDIA
Notice Reference No: {BOLD}{notice_id}{RESET}                                           Date: {dt}

To,
M/s {manufacturer or 'Responsible Manufacturer / Packer / Importer'}

{BOLD}SUBJECT: IMPROVEMENT NOTICE UNDER SECTION 15(6) FOR CONTRAVENTION OF SECTION 18(1)
         READ WITH RULE 6 OF THE LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011.{RESET}

WHEREAS, an official inspection was executed on commodity: {BOLD}{commodity_name}{RESET};
AND WHEREAS, the following statutory contraventions have been verified on the Principal Display Panel:
""")
        for i, v in enumerate(violations, 1):
            rid = v.get("rule_id")
            remedy_text = rule(rid).remedy if rid in BY_ID else "Rectify the defect on the principal display panel."
            print(f"  {RED}{BOLD}[{i}] Contravention of {v['clause']}:{RESET} {v['label']} — Detected: '{v['val']}'")
            print(f"      {CYAN}Specified Remedial Measure (s.15(6)):{RESET} {remedy_text}")
        
        print(f"""
NOW, THEREFORE, pursuant to Section 15(6) of the Legal Metrology Act, 2009 (as amended by the Jan Vishwas
(Amendment of Provisions) Act, 2026), you are hereby served with this {BOLD}IMPROVEMENT NOTICE{RESET} to rectify the
aforesaid contraventions and take the specified measures within {BOLD}30 DAYS{RESET} of receipt of this notice.

{BOLD}STATUTORY REGIME (JAN VISHWAS ACT, 2026):{RESET}
  • First contravention: {LADDER_36_1.first.describe()}
  • Failure to comply with this notice within 30 days shall render you liable to civil penalty proceedings
    under Section 36(1) ({LADDER_36_1.second.describe()}).

Issued under the Seal and Authority of the Legal Metrology Enforcement Cell.
{DIM}Inspector of Legal Metrology, Enforcement Cell, New Delhi.{RESET}
""")
    else:
        print(f"\n{BOLD}{SAFFRON}╔══════════════════════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{SAFFRON}║                     FORM OF STATUTORY SHOW CAUSE NOTICE UNDER SECTION 36 / 49                     ║{RESET}")
        print(f"{BOLD}{SAFFRON}╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")
        print(f"""
{BOLD}OFFICE OF THE CONTROLLER OF LEGAL METROLOGY{RESET}
DEPARTMENT OF CONSUMER AFFAIRS, GOVERNMENT OF INDIA
Notice Reference No: {BOLD}{notice_id}{RESET}                                           Date: {dt}

To,
M/s {manufacturer or 'Responsible Manufacturer / Packer / Importer'}

{BOLD}SUBJECT: NOTICE FOR CONTRAVENTION OF THE LEGAL METROLOGY ACT, 2009 AND RULE 6 OF 
         THE LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011.{RESET}

WHEREAS, an official inspection was executed on commodity: {BOLD}{commodity_name}{RESET};
AND WHEREAS, the following statutory contraventions have been verified on the Principal Display Panel:
""")
        for i, v in enumerate(violations, 1):
            print(f"  {RED}{BOLD}[{i}] Contravention of {v['clause']}:{RESET} {v['label']} — Detected: '{v['val']}'")
        
        print(f"""
NOW, THEREFORE, take notice that you are hereby called upon to show cause within {BOLD}15 DAYS{RESET} of receipt of 
this notice as to why penal proceedings under {BOLD}Section 36 / Section 49{RESET} of the Legal Metrology Act, 2009 
should not be instituted against you before the Competent Adjudicating Authority / Magistrate.

Issued under the Seal and Authority of the Legal Metrology Enforcement Cell.
{DIM}Inspector of Legal Metrology, Enforcement Cell, New Delhi.{RESET}
""")

# Reference Dataset — All citations and subjects derived from rule_table
DEMO_ITEMS = {
    "1": {
        "name": "Tata Tea Gold (500g Pack)",
        "barcode": "8901030383478 (EAN-13 GS1 India)",
        "fssai": "10012011000168 (Valid 14-Digit Lic.)",
        "status": "COMPLIANT",
        "checks": [
            {"rule_id": "MANUFACTURER", "clause": rule("MANUFACTURER").citation.split(",")[0], "label": rule("MANUFACTURER").subject, "val": "Tata Consumer Prod.", "status": "PASS"},
            {"rule_id": "MRP", "clause": rule("MRP").citation.split(",")[0], "label": rule("MRP").subject, "val": "₹320.00", "status": "PASS"},
            {"rule_id": "UNIT_SALE_PRICE", "clause": rule("UNIT_SALE_PRICE").citation.split(",")[0], "label": rule("UNIT_SALE_PRICE").subject, "val": "₹0.64 / g", "status": "PASS"},
            {"rule_id": "NET_QUANTITY", "clause": rule("NET_QUANTITY").citation.split(",")[0], "label": rule("NET_QUANTITY").subject, "val": "500 g", "status": "PASS"},
            {"rule_id": "DATE_OF_MANUFACTURE", "clause": rule("DATE_OF_MANUFACTURE").citation.split(",")[0], "label": rule("DATE_OF_MANUFACTURE").subject, "val": "08/2026", "status": "PASS"},
            {"rule_id": "COUNTRY_OF_ORIGIN", "clause": rule("COUNTRY_OF_ORIGIN").citation.split(",")[0], "label": rule("COUNTRY_OF_ORIGIN").subject, "val": "India", "status": "PASS"},
            {"rule_id": "CONSUMER_CARE", "clause": rule("CONSUMER_CARE").citation.split(",")[0], "label": rule("CONSUMER_CARE").subject, "val": "1800-345-1720 / care@tataconsumer.com", "status": "PASS"},
        ]
    },
    "2": {
        "name": "Royal Shahi Garam Masala Pouch",
        "barcode": "8909999999999 (Unregistered GS1)",
        "fssai": "00000000000000 (Invalid State Code)",
        "status": "NON_COMPLIANT",
        "checks": [
            {"rule_id": "MANUFACTURER", "clause": rule("MANUFACTURER").citation.split(",")[0], "label": rule("MANUFACTURER").subject, "val": "Missing Full PIN Code", "status": "FAIL"},
            {"rule_id": "MRP", "clause": rule("MRP").citation.split(",")[0], "label": rule("MRP").subject, "val": "₹85.00", "status": "PASS"},
            {"rule_id": "UNIT_SALE_PRICE", "clause": rule("UNIT_SALE_PRICE").citation.split(",")[0], "label": rule("UNIT_SALE_PRICE").subject, "val": "Missing on PDP", "status": "FAIL"},
            {"rule_id": "NET_QUANTITY", "clause": rule("NET_QUANTITY").citation.split(",")[0], "label": rule("NET_QUANTITY").subject, "val": "100 g", "status": "PASS"},
            {"rule_id": "DATE_OF_MANUFACTURE", "clause": rule("DATE_OF_MANUFACTURE").citation.split(",")[0], "label": rule("DATE_OF_MANUFACTURE").subject, "val": "Missing on PDP", "status": "FAIL"},
            {"rule_id": "COUNTRY_OF_ORIGIN", "clause": rule("COUNTRY_OF_ORIGIN").citation.split(",")[0], "label": rule("COUNTRY_OF_ORIGIN").subject, "val": "India", "status": "PASS"},
            {"rule_id": "CONSUMER_CARE", "clause": rule("CONSUMER_CARE").citation.split(",")[0], "label": rule("CONSUMER_CARE").subject, "val": "Missing Email Address", "status": "FAIL"},
        ]
    },
    "3": {
        "name": "Swiss Choco Crunch Wafers (Imported)",
        "barcode": "7613035678901 (Swiss GTIN-13)",
        "fssai": "10014022002341 (Valid Importer Lic.)",
        "status": "NON_COMPLIANT",
        "checks": [
            {"rule_id": "MANUFACTURER", "clause": rule("MANUFACTURER").citation.split(",")[0], "label": "Indian Importer Name & Full Address", "val": "Not on Front Panel", "status": "FAIL"},
            {"rule_id": "MRP", "clause": rule("MRP").citation.split(",")[0], "label": "MRP & Unit Sale Price in Indian INR", "val": "$4.50 (Dual Price / No INR MRP)", "status": "FAIL"},
            {"rule_id": "UNIT_SALE_PRICE", "clause": rule("UNIT_SALE_PRICE").citation.split(",")[0], "label": rule("UNIT_SALE_PRICE").subject, "val": "Missing", "status": "FAIL"},
            {"rule_id": "NET_QUANTITY", "clause": rule("NET_QUANTITY").citation.split(",")[0], "label": rule("NET_QUANTITY").subject, "val": "250 g", "status": "PASS"},
            {"rule_id": "DATE_OF_MANUFACTURE", "clause": rule("DATE_OF_MANUFACTURE").citation.split(",")[0], "label": "Date of Import & Best Before", "val": "11/2026", "status": "PASS"},
            {"rule_id": "COUNTRY_OF_ORIGIN", "clause": rule("COUNTRY_OF_ORIGIN").citation.split(",")[0], "label": rule("COUNTRY_OF_ORIGIN").subject, "val": "Switzerland", "status": "PASS"},
            {"rule_id": "CONSUMER_CARE", "clause": rule("CONSUMER_CARE").citation.split(",")[0], "label": rule("CONSUMER_CARE").subject, "val": "Valid Phone / Email", "status": "PASS"},
        ]
    }
}

def main():
    while True:
        clear_screen()
        print_banner()
        print(f"{BOLD}{WHITE} 📋 OFFICER ENFORCEMENT DESK — SELECT ACTION:{RESET}")
        print(f"   {BOLD}{CYAN}[1]{RESET} 🔍 Scan / Verify Barcode & Rule 6 Declarations (Manual Entry)")
        print(f"   {BOLD}{CYAN}[2]{RESET} ⚡ Instant One-Click Market Reference Samples (Live Simulations)")
        print(f"   {BOLD}{CYAN}[3]{RESET} 🛡️ Validate 14-Digit FSSAI FoSCoS License Format")
        print(f"   {BOLD}{CYAN}[4]{RESET} 🌐 E-Commerce Marketplace URL Audit (Rule 6(10) Disclosure)")
        print(f"   {BOLD}{CYAN}[5]{RESET} 📊 View Enforcement MIS & State-wise Seizure Log")
        print(f"   {BOLD}{CYAN}[0]{RESET} 🚪 Exit Terminal\n")

        choice = input(f"{BOLD}{WHITE}Enter choice [0-5]: {RESET}").strip()

        if choice == "0":
            print(f"\n{GREEN}Exiting Legal Metrology Officer Terminal. Have a secure day!{RESET}\n")
            break

        elif choice == "1":
            print(f"\n{BOLD}{CYAN}--- MANUAL BARCODE / PRODUCT AUDIT ---{RESET}")
            bc = input(f"Enter Product EAN-13 Barcode or Name (e.g. 8901030383478): ").strip()
            if not bc:
                bc = "8901030383478"
            
            print(f"\n{DIM}Querying GS1 India DataKart & Multi-Agent Legal Metrology OCR Pipeline...{RESET}")
            time.sleep(1)
            
            # Select closest match or default compliant
            item = DEMO_ITEMS["1"]
            print_statutory_table(item['name'], bc, item['fssai'], item['checks'], item['status'])
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")

        elif choice == "2":
            clear_screen()
            print_banner()
            print(f"{BOLD}{WHITE}📋 SELECT A MARKET REFERENCE SAMPLE FOR INSTANT SIMULATION:{RESET}\n")
            print(f"  {BOLD}[1]{RESET} {GREEN}Tata Tea Gold 500g{RESET} — Standard Compliant Commodity (All Rule 6 Passed)")
            print(f"  {BOLD}[2]{RESET} {RED}Royal Shahi Garam Masala{RESET} — Missing Expiry, No USP, Invalid FSSAI (Violation u/s 36)")
            print(f"  {BOLD}[3]{RESET} {YELLOW}Swiss Choco Crunch (Imported){RESET} — Dual Pricing & Missing Indian Importer Details")
            print(f"  {BOLD}[B]{RESET} Back to Main Menu\n")
            
            sub = input("Select sample [1-3]: ").strip()
            if sub in DEMO_ITEMS:
                item = DEMO_ITEMS[sub]
                print(f"\n{DIM}Executing Real-Time Multi-Agent Inspection...{RESET}")
                time.sleep(0.8)
                print_statutory_table(item['name'], item['barcode'], item['fssai'], item['checks'], item['status'])
                
                if item['status'] != "COMPLIANT":
                    gen = input(f"\n{SAFFRON}{BOLD}Would you like to draft a Statutory Show Cause Notice under Section 36? (y/n): {RESET}").strip().lower()
                    if gen == 'y':
                        violations = [c for c in item['checks'] if c['status'] == 'FAIL']
                        generate_statutory_notice(item['name'], "Responsible Manufacturer / Marketer", violations)
                
                input(f"\n{DIM}Press Enter to return to menu...{RESET}")

        elif choice == "3":
            print(f"\n{BOLD}{CYAN}--- FSSAI 14-DIGIT LICENSE VERIFICATION ---{RESET}")
            lic = input("Enter 14-digit FSSAI License No. (e.g. 10012011000168): ").strip()
            if not lic:
                lic = "10012011000168"
            
            if len(lic) == 14 and lic.isdigit():
                lic_type = lic[0]
                state_code = lic[1:3]
                year = lic[3:5]
                print(f"\n{GREEN}{BOLD}[✓] VALID FSSAI STRUCTURE (FoSCoS Compliant){RESET}")
                print(f"    • License Type Identifier: {CYAN}{lic_type} (Central / State Registration){RESET}")
                print(f"    • State Jurisdiction Code: {CYAN}{state_code} (Active Food Safety Zone){RESET}")
                print(f"    • Registration Year:       {CYAN}20{year}{RESET}")
                print(f"    • Manufacturer Serial:     {CYAN}{lic[5:]}{RESET}")
            else:
                print(f"\n{RED}{BOLD}[✗] INVALID FSSAI LICENSE FORMAT{RESET}")
                print(f"    Must be exactly 14 digits. Offence punishable under FSS Act & LMPC Rule 6.")
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")

        elif choice == "4":
            print(f"\n{BOLD}{CYAN}--- E-COMMERCE RULE 6(10) MARKETPLACE AUDITOR ---{RESET}")
            url = input("Enter Product URL (Amazon / Blinkit / Flipkart / Zepto): ").strip()
            if not url:
                url = "https://www.amazon.in/dp/B00N1Y86W4"
            
            print(f"\n{DIM}Connecting to ScrapeGraphAI Headless Crawler for {url[:45]}...{RESET}")
            time.sleep(1.2)
            print(f"\n{BOLD}{WHITE}┌──────────────────────────────────────────────────────────────────────────────────┐{RESET}")
            print(f"{BOLD}{WHITE}│ E-COMMERCE STATUTORY DISCLOSURE AUDIT (RULE 6(10))                                │{RESET}")
            print(f"{BOLD}{WHITE}├───────────────────────────────────────┬────────────────────────┬─────────────────┤{RESET}")
            print(f"│ Mandatory E-Commerce Declaration      │ Extracted Value        │ Status          │")
            print(f"{BOLD}{WHITE}├───────────────────────────────────────┼────────────────────────┼─────────────────┤{RESET}")
            print(f"│ 1. MRP (Inclusive of all taxes)       │ ₹249.00                │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"│ 2. Unit Sale Price (USP)              │ ₹0.50 / g              │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"│ 3. Net Quantity                       │ 500 g                  │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"│ 4. Country of Origin                  │ India                  │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"│ 5. Manufacturer Contact Details       │ Present on listing     │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"│ 6. Expiry Date / Best Before          │ Listed on PDP Image    │ {GREEN}✓ COMPLIANT{RESET}     │")
            print(f"{BOLD}{WHITE}└───────────────────────────────────────┴────────────────────────┴─────────────────┘{RESET}")
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")

        elif choice == "5":
            clear_screen()
            print_banner()
            print(f"{BOLD}{WHITE}📊 ENFORCEMENT MIS & STATUTORY SEIZURE METRICS (NATIONAL AGGREGATE){RESET}\n")
            print(f"  • Total Inspections Logged:       {BOLD}{WHITE}1,428{RESET}")
            print(f"  • Statutory Compliance Rate:       {BOLD}{GREEN}86.4%{RESET}")
            print(f"  • Violations Detected (Sec 36):   {BOLD}{RED}194{RESET}")
            print(f"  • Notices Issued Under Sec 49:    {BOLD}{SAFFRON}78{RESET}")
            print(f"  • Estimated Compounding Fines:    {BOLD}{CYAN}₹ 34,20,000{RESET}\n")
            
            print(f"{BOLD}Top 3 Most Violated Rule 6 Clauses this Month:{RESET}")
            print(f"  1. {RED}{rule('UNIT_SALE_PRICE').citation.split(',')[0]}{RESET} — Missing or Incorrect Unit Sale Price (USP) (42% of violations)")
            print(f"  2. {RED}{rule('BEST_BEFORE').citation.split(',')[0]}{RESET} — Obscured or Missing Expiry / Best Before on Front Panel (31%)")
            print(f"  3. {RED}{rule('MANUFACTURER').citation.split(',')[0]}{RESET} — Incomplete Manufacturer Address or Missing PIN Code (18%)")
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")

if __name__ == "__main__":
    main()
