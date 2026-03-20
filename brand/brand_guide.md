# LEANCYCL Brand Style Guide

> **Tagline:** Agile Insights
> **Author:** Jonathan Cavner

---

## 1. Brand Overview

**LEANCYCL** is an agile software development consulting newsletter. The name fuses *lean* methodology with the *cycle* of continuous improvement — captured visually in the forward-leaning motorcycle rider icon.

**Brand personality:** Practical. Direct. Forward-moving. No fluff, just signal.

---

## 2. Logo

### Primary Logo
The primary logo consists of the motorcycle-rider icon above the "LEANCYCL" wordmark on a deep navy background.

| Asset | Path | Dimensions |
|-------|------|------------|
| Primary logo (PNG) | `brand/logo.png` | 60 × 60 px (standard); scale up proportionally |

### Clear Space
Maintain clear space equal to the height of the "L" in LEANCYCL on all four sides of the logo.

### Minimum Size
- **Digital:** 60 × 60 px
- **Print:** 0.75 in × 0.75 in

### Logo Usage — Do
- Use on dark backgrounds (`#1b3d4a` or similar deep navy/teal)
- Scale proportionally
- Use the full lockup (icon + wordmark) when space allows

### Logo Usage — Don't
- Don't recolor the logo
- Don't stretch or skew
- Don't place on busy photographic backgrounds
- Don't use the wordmark without the icon in primary placements
- Don't add drop shadows or effects

---

## 3. Color Palette

### Primary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Deep Navy | `#1b3d4a` | 27, 61, 74 | Backgrounds, headers, footers |
| Medium Teal | `#4e8fa2` | 78, 143, 162 | Accents, wordmark, links, borders |
| White | `#ffffff` | 255, 255, 255 | Body text on dark bg, icon strokes |

### Secondary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Button Blue | `#3a7a8e` | 58, 122, 142 | CTA buttons, interactive elements |
| Dark Teal | `#2a6478` | 42, 100, 120 | Body text on light backgrounds |
| Ice Blue | `#e6f4f7` | 230, 244, 247 | Callout/highlight backgrounds |

### Color Relationships
- **Dark on light:** `#2a6478` on `#e6f4f7` — callout blocks
- **Light on dark:** `#ffffff` on `#1b3d4a` — headers, footers
- **Accent on dark:** `#4e8fa2` on `#1b3d4a` — wordmark, decorative elements

---

## 4. Typography

The logo wordmark uses a bold, condensed sans-serif with a slight arc. For email and web applications, use system-safe equivalents:

| Role | Font | Weight | Notes |
|------|------|--------|-------|
| Headlines | Arial | Bold (700) | All-caps for section headers |
| Body | Georgia | Regular (400) | Readable at small sizes in email |
| Labels / Meta | Arial | Regular (400) | Captions, timestamps, fine print |

### Type Scale (Email)
- **Newsletter title:** 24–28px, bold, all-caps
- **Section headings:** 18–20px, bold
- **Body text:** 15–16px, regular, 1.6 line-height
- **Footer / fine print:** 12px, regular

---

## 5. Voice & Tone

| Do | Don't |
|----|-------|
| Write directly and concisely | Use buzzword-heavy filler |
| Use active voice | Bury the lead |
| Ground advice in real-world agile practice | Over-explain basic concepts |
| Reference engineering tradeoffs honestly | Oversell or hype |

**Example headline (good):** "Why Your Sprint Reviews Are Failing (And How to Fix Them)"
**Example headline (avoid):** "Unlock Synergistic Agile Value With These Transformative Insights"

---

## 6. Newsletter Application

### Email Structure
```
┌─────────────────────────────────┐
│  HEADER  bg: #1b3d4a            │
│  [logo] LEANCYCL  Agile Insights│
├─────────────────────────────────┤
│  BODY  bg: #ffffff              │
│  Headline (bold, 22px)          │
│  Body text (#2a6478 or #333)    │
│                                 │
│  ┌───────────────────────────┐  │
│  │ CALLOUT  bg: #e6f4f7      │  │
│  │ border-left: #4e8fa2      │  │
│  │ text: #2a6478             │  │
│  └───────────────────────────┘  │
│                                 │
│  [CTA BUTTON  bg: #3a7a8e]      │
├─────────────────────────────────┤
│  FOOTER  bg: #1b3d4a            │
│  Address · Unsubscribe          │
└─────────────────────────────────┘
```

### Button Style
- Background: `#3a7a8e`
- Text: `#ffffff`, bold
- Padding: 12px 24px
- Border-radius: 4px
- Hover: `#1b3d4a` with `#4e8fa2` border
