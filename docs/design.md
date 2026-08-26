# Design Specification — The Lenny Growth Assistant (`design.md`)

## 1. UI/UX Principles

The user interface of **The Lenny Growth Assistant** is crafted around four core principles:

1. **Information Density with High Legibility**: Designed for Product Managers and Growth Leaders who need to scan executive summaries, extract actionable frameworks, and inspect source citations quickly.
2. **Side-by-Side Artifact Workspaces**: Rather than dumping complex code, HTML dashboards, or multi-page essays into a narrow chat stream, the UI dynamically opens a dedicated **Artifact Viewer** panel on the right.
3. **Transparent Grounding & Provenance**: Every transcript-backed answer clearly displays source badges (Episode title, guest name, timestamp URL). Hovering or clicking source tags reveals exact excerpts.
4. **Instant Feedback & Mode Clarity**: Clear visual indicators communicate whether the system is operating in **Cloud Gemini** mode or **Local Ollama** mode, alongside live knowledge sync status indicators.

---

## 2. Information Architecture & Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  HEADER / TOP BAR                                                                           │
│  [Logo: Lenny Growth Assistant]   [Status: Knowledge Synced]  [Model Switcher: Cloud/Ollama]│
├──────────────────────────────┬────────────────────────────────┬─────────────────────────────┤
│  LEFT SIDEBAR                │  MAIN CHAT STREAM              │  RIGHT ARTIFACT PANEL       │
│                              │                                │  (Opens dynamically)        │
│  [+ New Conversation]        │  [Assistant Greeting]          │                             │
│                              │                                │  ┌───────────────────────┐  │
│  RECENT SESSIONS             │  [User Message]                │  │ Artifact Title        │  │
│  - PM Growth Framework       │                                │  │ [HTML / Markdown]     │  │
│  - Shreyas Doshi LNO         │  [Assistant Response]          │  │                       │  │
│  - Pricing Strategy          │   ├─ Grounded Text             │  │ Interactive Card /    │  │
│                              │   ├─ Citation Source Cards     │  │ Growth Matrix         │  │
│  KNOWLEDGE BASE STATUS       │   └─ [View Artifact Button] ───┼─►│                       │  │
│  - 50+ Episodes Ingested     │                                │  └───────────────────────┘  │
│  - pgvector 3072-dim Ready   │  [Input Box: Ask question...]  │                             │
└──────────────────────────────┴────────────────────────────────┴─────────────────────────────┘
```

---

## 3. Key Interaction States

### A. Conversation & Message States
- **Idle State**: Displays quick-start prompt chips (*"Explain Shreyas Doshi's LNO Framework"*, *"Draft a Ship 30 essay on activation loops"*, *"Create a Growth Matrix artifact"*).
- **Streaming / Thinking State**: Shows smooth word-by-word token streaming with a pulse animation indicating active Pi Agent execution and tool calls.
- **Source Citation Hover State**: Hovering over a `[Episode: Guest - Title]` tag displays a rich tooltip with the exact transcript excerpt and a direct link to the GitHub transcript line.

### B. Artifact Panel States
- **Closed State**: Main chat occupies 100% of the content width.
- **Open State**: Dynamic 50/50 split layout. The left column retains conversation context; the right panel renders full HTML/CSS components, interactive calculators, or Markdown essays with tabs to switch between Rendered View and Code View.

### C. Model Switcher States
- **Cloud Mode Active**: Highlights Gemini 3.6 Flash badge with cloud icon.
- **Ollama Mode Active**: Highlights Local Ollama badge (`llama3.1:8b`) with privacy/hardware icon.
- **Offline / Unavailable Warning**: Disables unsupported options with an informative popover if local Ollama or cloud API key is unreachable.

---

## 4. Responsive Behavior & Adaptive Layouts

- **Desktop Screens (≥ 1280px)**: Full three-column layout (Sidebar + Chat Stream + Artifact Panel).
- **Tablet Screens (768px – 1279px)**: Collapsible sidebar (accessible via hamburger menu); Artifact Panel slides overlay or toggles full screen.
- **Mobile Screens (< 768px)**: Single column view. Toggling between Chat View and Artifact View is handled via tab bar controls at the top.

---

## 5. Accessibility Considerations (a11y)

- **Color Contrast**: Dark mode palette uses high-contrast typography (pure white `#FFFFFF` and muted gray `#94A3B8` on deep slate `#0F172A`), meeting WCAG AA standards.
- **Keyboard Navigation**: Full tab navigation support for prompt buttons, input fields, model selectors, and sidebar session items.
- **Semantic HTML**: Structural tags (`<header>`, `<nav>`, `<main>`, `<aside>`, `<article>`) ensure screen reader compatibility.
- **Unique Element Identifiers**: Interactive UI elements possess unique `id` tags (`#send-message-btn`, `#provider-select`, `#artifact-container`) for testing and accessibility hooks.

---

## 6. Design Decisions & Trade-Off Rationale

| Design Decision | Alternative Considered | Rationale |
|-----------------|------------------------|-----------|
| **Dedicated Side Panel for Artifacts** | Inline code blocks in chat | Inline HTML/Markdown code blocks clutter conversation history. A side panel enables side-by-side interaction and dashboard rendering. |
| **Dark Theme Aesthetics** | Generic light theme | Dark mode reduces eye strain for long reading sessions and gives a modern, premium AI IDE feel. |
| **Vanilla CSS + Glassmorphism** | Heavy UI Framework (Tailwind/Bootstrap) | Vanilla CSS guarantees zero bundle bloat, instant page loads via Nginx, and complete design control over glassmorphism overlays and CSS grid transitions. |
