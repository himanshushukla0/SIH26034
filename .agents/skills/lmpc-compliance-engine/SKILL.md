---
name: lmpc-compliance-engine
description: >-
  Expert guidance and verification logic for the Legal Metrology Act 2009 and Legal Metrology (Packaged Commodities) Rules, 2011 (LMPC) in India.
  Use when validating product labels, calculating Unit Sale Price (USP), checking Principal Display Panel (PDP) font size thresholds, checking mandatory declarations, or generating regulatory violation reports.
---

# LMPC Legal Metrology Compliance Engine

This skill provides regulatory rules, validation algorithms, and legal criteria for auditing packaged commodities and e-commerce listings under Indian Law.

## Mandatory Declarations Checklist (Rule 6)

Every pre-packaged commodity in India must carry these declarations on the Principal Display Panel (PDP):

1. **Manufacturer / Packer / Importer Name & Address** (Rule 6(1)(a)):
   - Complete street address, city, state, pin code.
   - For imported goods: Must declare both foreign manufacturer and Indian importer details.
2. **Country of Origin** (Rule 6(1)(aa) & 2020/2022 amendments):
   - Mandatory for all commodities, especially imports and e-commerce platform displays.
3. **Generic / Common Name of Commodity** (Rule 6(1)(b)):
   - Must be prominently stated so consumers know what is inside.
4. **Net Quantity** (Rule 6(1)(c), Rule 12 & Rule 13):
   - Weight: `g`, `kg` (not 'gms', 'kilos')
   - Volume: `ml`, `l`, `L` (not 'ltr', 'ml.')
   - Length/Area: `cm`, `m`, `sq. m`
   - Numbers: `N`, `U`, or `units`
   - Permissible Error tolerances based on Second Schedule.
5. **Month & Year of Manufacture / Packing / Import** (Rule 6(1)(d)):
   - Format: `MM/YYYY` or Month Name and Year.
6. **Best Before / Expiry Date** (Rule 6(1)(e)):
   - Mandatory for food, cosmetic items, and perishable products.
7. **Maximum Retail Price (MRP)** (Rule 6(1)(e)):
   - Format: `MRP ₹ XX.XX (inclusive of all taxes)` or `MRP Rs. XX (incl. of all taxes)`.
   - Cannot exceed MRP or tamper with price sticker.
8. **Unit Sale Price (USP)** (Mandatory from 2021 Amendment):
   - For packages with net quantity > 1 kg or 1 L: USP must be expressed per `kg` or per `l`.
   - For packages with net quantity < 1 kg or 1 L: USP must be expressed per `g` or per `ml`.
   - For length > 1 m: per `m`.
   - For items sold by number: per `piece` / `number`.
9. **Consumer Care & Grievance Details** (Rule 6(1)(f)):
   - Name/Designation of person, postal address, telephone number, and email address.

---

## Font Size vs Principal Display Panel (PDP) Area (Rule 7, Table 1)

| Area of Principal Display Panel ($A$ in $\text{cm}^2$) | Min Font Height (General) | Min Font Height (Blowing/Moulding/Perforating) |
| :--- | :--- | :--- |
| $A \le 50$ | $1.0\text{ mm}$ | $1.5\text{ mm}$ |
| $50 < A \le 100$ | $1.5\text{ mm}$ | $3.0\text{ mm}$ |
| $100 < A \le 500$ | $2.0\text{ mm}$ | $4.0\text{ mm}$ |
| $500 < A \le 2500$ | $4.0\text{ mm}$ | $6.0\text{ mm}$ |
| $A > 2500$ | $6.0\text{ mm}$ | $6.0\text{ mm}$ |

### Permissible Numerals for Net Quantity:
The numeral height for Net Quantity must be at least twice the minimum font height for other declarations in smaller packaging.

---

## Mathematical Formula for Unit Sale Price (USP)
$$\text{USP} = \frac{\text{MRP}}{\text{Net Quantity in Standard Base Units}}$$
Example:
- Pack of $450\text{ g}$ biscuits at $\text{MRP} = ₹90$
- Base Unit = Grams
- $\text{USP} = \frac{90}{450} = ₹0.20\text{ / g}$

---

## Violation Severity & Legal Penalty Mapping
- **Critical Violation (Red):** Missing MRP, Altered/Tampered MRP, Missing Net Quantity, Missing Expiry on perishables, Missing Country of Origin on imported products.
- **Major Violation (Orange):** Missing Unit Sale Price, Incomplete Consumer Care info, Missing Month/Year of packing, Non-standard units (e.g. using `gms` instead of `g`).
- **Minor Violation (Yellow):** Font height below prescribed threshold by $<10\%$, poor contrast ratio, non-prominent generic name placement.
