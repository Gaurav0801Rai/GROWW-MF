# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview
Build a **facts-only FAQ assistant** for mutual fund schemes using **Groww** as the reference product context. The assistant should answer **objective, verifiable questions** about mutual funds by retrieving information exclusively from **official public sources** such as AMC websites, AMFI, and SEBI.

The system must **not provide investment advice**, opinions, or recommendations. Every response must include a **single clear source link** and adhere to strict clarity and compliance constraints.

---

## Objective
Design and implement a lightweight Retrieval-Augmented Generation (RAG)-based assistant that:
- Answers **factual queries** about mutual fund schemes
- Uses a **curated corpus of official documents**
- Provides **concise, source-backed responses**

---

## Target Users
- Retail investors comparing mutual fund schemes  
- Customer support and content teams handling repetitive MF queries  

---

## Scope of Work

### 1. Corpus Definition
- **Asset Management Company (AMC):** HDFC Mutual Fund (via Groww)
- **Selected Schemes (5 URLs):**
  - [HDFC Mid-Cap Opportunities Fund Direct Growth](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth)
  - [HDFC Top 100 Fund Direct Growth](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth)
  - [HDFC Small Cap Fund Direct Growth](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth)
  - [HDFC Gold ETF Fund of Fund Direct Plan Growth](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth)
  - [HDFC Defence Fund Direct Growth](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)

---

### 2. FAQ Assistant Requirements

The assistant must:
- Answer **facts-only queries**, such as:
  - Expense ratio of a scheme
  - Exit load details
  - Minimum SIP amount
  - ELSS lock-in period
  - Riskometer classification
  - Benchmark index
  - Fund management details (fund managers, tenure, and education)
  - Process to download statements or capital gains reports

- Ensure:
  - Each response is **≤ 3 sentences**
  - Each response includes **exactly one citation link**
  - Include a footer:  
    `Last updated from sources: <date>`

---

### 3. Refusal Handling
The assistant must **refuse non-factual or advisory queries**, such as:
- “Should I invest in this fund?”
- “Which fund is better?”

Refusal response should:
- Be polite and clear
- Reinforce **facts-only limitation**
- Provide a **relevant educational link** (e.g., AMFI/SEBI resource)

---

### 4. User Interface (Minimal)
Provide a simple UI with:
- Welcome message  
- 3 example questions  
- Disclaimer note:  
  **“Facts-only. No investment advice.”**

---

## Constraints

### Data & Sources
- Use **only official public sources** (AMC, AMFI, SEBI)
- Do **not** use third-party blogs or aggregators

### Privacy & Security
- Do **not** collect or process:
  - PAN, Aadhaar
  - Account numbers
  - OTPs
  - Emails or phone numbers

### Content Restrictions
- No investment advice or recommendations
- No performance comparisons or return calculations
- If performance-related queries arise, **link to official factsheet only**

### Transparency
- Keep answers short, factual, and verifiable
- Always include a source link and last updated date

---

## Expected Deliverables

1. **README**
   - Setup instructions  
   - Selected AMC and schemes  
   - Architecture overview (RAG approach)  
   - Known limitations  

2. **Disclaimer Snippet**
   - “Facts-only. No investment advice.”  

3. **Multiple Chat thread support**
   - RAG-based chatbot that can handle multiple threads or conversations simultaneously
---

## Success Criteria
- Accurate retrieval of factual mutual fund data  
- Strict adherence to **facts-only responses**  
- Consistent inclusion of **valid source citations**  
- Clear refusal of advisory queries  
- Clean, minimal, and usable interface  

---

## Summary
The goal is to build a **trustworthy, transparent, and compliant mutual fund FAQ assistant** that prioritizes **accuracy over intelligence**, ensuring users receive only **verified, source-backed financial information** without any advisory bias.