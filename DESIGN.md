---
name: EVOPT Maps
description: Fjord, a calm map-first interface for an electric-vehicle route planner. Soft floating cards over a full-bleed map, warm-grey neutrals and one green that means energy, route and the primary action.
colors:
  canvas-light: "#f4f5f3"
  surface-light: "#ffffff"
  raised-light: "#f0f2ef"
  ink-light: "#101413"
  ink-2-light: "#5d6662"
  rule-strong-light: "#c6ccc8"
  accent-light: "#18c68f"
  accent-ink-light: "#067a58"
  on-accent-light: "#06201a"
  route-light: "#0a9f73"
  danger-light: "#b3261e"
  canvas-dark: "#0f1312"
  surface-dark: "#171b1a"
  raised-dark: "#232827"
  ink-dark: "#e7ece9"
  ink-2-dark: "#a2aca7"
  rule-strong-dark: "#3a413e"
  accent-dark: "#43e0b1"
  on-accent-dark: "#06201a"
  route-dark: "#43e0b1"
  danger-dark: "#ff8a80"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 2.75rem
    fontWeight: 650
    lineHeight: 1
    letterSpacing: -0.035em
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 1.25rem
    fontWeight: 650
    lineHeight: 1.25
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 0.8125rem
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 12px
  md: 14px
  lg: 20px
  pill: 999px
spacing:
  unit: 4px
  field: 14px
  panel: 20px
components:
  button-primary:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.on-accent-light}"
    rounded: "{rounded.md}"
    height: 48px
  input:
    backgroundColor: "{colors.raised-light}"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.sm}"
    height: 44px
  panel:
    backgroundColor: "{colors.surface-light}"
    rounded: "{rounded.lg}"
    padding: 20px
---

# Design System: EVOPT Maps

## Overview

**Creative North Star: "Fjord"**

The map is the page. The planner floats above it as a few soft cards, so the route is always in view and nothing frames it. The mood is a modern in-car display: quiet neutrals, generous radii, one fresh green for everything about energy. Chrome stays out of the way and the numbers carry the screen: minutes, kilowatt-hours and battery before and after each stop.

**Key Characteristics:**
- Map-first: full-bleed map, cards float over the left 432 px and never cover the route (the map pads itself around them).
- One accent, green, for the route, the charge bar and the primary action. Everything else is neutral.
- Light and dark themes from the same tokens; dark follows the system with a header toggle.
- Soft depth: elevation is a single soft shadow, declared once; there are no borders on cards.
- Short transitions (150 to 200 ms, exponential ease-out) that only confirm state.

## Colors

Warm-grey neutrals shared with telai.camossi, plus one green.

- **Accent** (#18c68f light, #43e0b1 dark): primary button, slider fill, focus tint. Text on it is **On Accent** (#06201a).
- **Accent Ink** (#067a58 light): green used as text or link colour on light surfaces (5.3:1 on white).
- **Route** (#0a9f73 light, #43e0b1 dark): the route line, the stop rings, the charge gauge. It sits on a casing the colour of the page, so it holds against any tile.
- **Canvas / Surface / Raised**: page, cards, fields and chips (#f4f5f3, #ffffff, #f0f2ef; dark #0f1312, #171b1a, #232827).
- **Ink / Ink 2**: text and secondary text (18.6:1 and 5.9:1 on white; 14.6:1 and 7.5:1 on the dark surface).
- **Danger** (#b3261e, #ff8a80): errors only, always with a "!" badge and a message.

**The One Accent Rule.** Green means energy or action: route, charge, primary button, the current choice. Never use it for decoration.

**The No Colour Alone Rule.** State is also a word or a shape: step status says done, working or waiting; errors carry a badge; the active stop is filled and numbered.

## Typography

**Geist** (variable, self-hosted in `web/vendor/fonts`, SIL OFL) for everything. Hierarchy is weight and size: 650 for headings with slight negative tracking, 500 for labels, 400 for body, tabular figures for every number. No second typeface.

## Layout

Wide screens: header, then the map fills the viewport and a 432 px rail of cards floats over it (16 px inset, 12 px between cards). The rail ignores pointer events between cards so the map can be dragged. Below 900 px the cards and the map stack in one column. Content pages (Vehicles, Algorithms, Model) are a single 920 px column.

## Elevation & Depth

One soft two-layer shadow for floating cards, a lighter one for resting cards and the active tab. Cards over the map use a translucent surface with a background blur so the map reads through; stacked content cards are opaque.

## Shapes

12 px fields, 14 px primary button, 20 px cards, pill for the tabs and the map chip, circles for stops. Map markers: a ringed number for charging stops, a dark dot for start and end, small hollow circles for stations.

## Components

- **Primary button:** green fill, On Accent text, 48 px.
- **Fields:** filled Raised background, no border until focus, then a green ring.
- **Sliders:** 4 px track filled green, 20 px white thumb with a soft shadow, live tabular readout.
- **Trip line:** a vertical 3 px route-coloured line, ringed numbers for stops, a charge gauge per stop showing the battery before and after.
- **Tabs:** a pill group, the current one raised on Surface.
- **Data table:** rows on a Surface card with hairline separators, right-aligned tabular numbers, best row in 600.

## Do's and Don'ts

### Do:
- **Do** print the reasoning: each stop shows its minutes, kWh and battery before and after.
- **Do** keep the route visible: pad the map around the rail.
- **Do** keep transitions between 150 and 200 ms and respect reduced motion.
- **Do** show the model's limits next to the result.

### Don't:
- **Don't** use green for anything but route, charge and the primary action.
- **Don't** add borders to floating cards or stack shadows on shadows.
- **Don't** use a modal for planning: status and errors live in the rail.
- **Don't** colour map tiles; they stay grey (dark mode inverts them) so the route leads.
