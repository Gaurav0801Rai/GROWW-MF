# UI Design Specification: Groww‑Style FAQ Assistant (Final Version)

## Theme & Background
- **Background:** Dark starry night sky gradient (deep navy → purple) with scattered stars.
- **Foreground silhouette:** Faint forest treeline at the bottom horizon.
- **Rocket animation:** Small rocket icon at bottom‑right corner.
  - Animation: Launch upward every 2–3 seconds.
  - Trail: Glowing orange‑blue exhaust fading as rocket ascends.
  - Loop: Infinite, smooth splash effect.

## Layout Structure

### Sidebar (Left)
- Title: **groww‑factor**
- Subtitle: *“Intelligent helper for HDFC Mutual Fund queries”*
- Elements:
  - **+ New Chat** button (green accent, rounded corners).
  - **Chat history list:** “Chat 1”, “Chat 2”.
  - **HDFC Mutual Funds list:**
    - HDFC Mid‑Cap Opportunities  
    - HDFC Flexi Cap Fund  
    - HDFC Top 100 Fund  
    - HDFC ELSS Tax Saver  
    - HDFC Sensex ETF 100
  - **No light‑mode toggle** (dark theme only).

### Main Panel (Center)
- Heading: *“How can I help you today?”*
- Subtext: *“I provide strict, compliance‑aware factual answers directly from official fund documents.”*
- Example query buttons (rounded, hover glow):
  1. “What is the latest NAV for HDFC Mid‑Cap Opportunities Fund?”
  2. “What is the expense ratio for HDFC Mid‑Cap Opportunities Fund?”
  3. “Who is the fund manager for HDFC Flexi Cap Fund?”
- Input field at bottom:
  - Placeholder: *“Ask about HDFC mutual funds?”*
  - Send button: green square with white paper plane icon.

### Footer
- Disclaimer card: *“Facts‑only. No investment advice.”*
- Metadata: *“Powered by verified sources | Last updated: May 2024”*

## Color Palette
- Background: `#0b132b` (navy) → `#3a1c71` (purple gradient).
- Text: White (`#FFFFFF`).
- Accent: Teal/Green (`#00bfa5`).
- Buttons: Rounded corners, hover glow effect.

## Interaction Notes
- Rocket animation loops infinitely with ~3s interval.
- Sidebar updates dynamically with new chats and supported funds.
- Example queries are clickable shortcuts that auto‑populate the input field.
- Disclaimer remains visible across all screens.
- Responsive design optimized for **desktop web view** (not mobile).

