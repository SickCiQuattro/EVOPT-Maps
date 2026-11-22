---
name: EVOPT Maps
description: Noorda Line, a metro-signage design system for an electric-vehicle route planner where the trip is a line and each charging stop is a station.
colors:
  canvas-light: "#f5f6f3"
  surface-light: "#ffffff"
  ink: "#16191a"
  ink-2-light: "#5b625f"
  rule-light: "#d9dcd7"
  rule-strong-light: "#868d88"
  line-blue-light: "#0057b8"
  line-blue-pressed-light: "#00468f"
  on-line-blue-light: "#ffffff"
  map-ground-light: "#f4f4f4"
  casing-light: "#ffffff"
  canvas-dark: "#0f1110"
  surface-dark: "#1c1f1d"
  chalk: "#e6e9e4"
  ink-2-dark: "#a7aea8"
  rule-dark: "#2e322f"
  rule-strong-dark: "#6c746e"
  line-blue-dark: "#6aa6ff"
  line-blue-pressed-dark: "#94bfff"
  on-line-blue-dark: "#0f1110"
  map-ground-dark: "#1f1f1f"
  casing-dark: "#0f1110"
typography:
  display:
    fontFamily: "Helvetica Neue, Helvetica, Arimo, Arial, sans-serif"
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.1
  headline:
    fontFamily: "Helvetica Neue, Helvetica, Arimo, Arial, sans-serif"
    fontSize: 1.5rem
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Helvetica Neue, Helvetica, Arimo, Arial, sans-serif"
    fontSize: 1.25rem
    fontWeight: 700
    lineHeight: 1.5
  body:
    fontFamily: "Helvetica Neue, Helvetica, Arimo, Arial, sans-serif"
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Helvetica Neue, Helvetica, Arimo, Arial, sans-serif"
    fontSize: 0.8125rem
    fontWeight: 700
    lineHeight: 1.4
rounded:
  none: 0px
  station: 50%
spacing:
  unit: 8px
  field: 16px
  panel: 24px
components:
  button-primary:
    backgroundColor: "{colors.line-blue-light}"
    textColor: "{colors.on-line-blue-light}"
    rounded: "{rounded.none}"
    height: 48px
  button-primary-hover:
    backgroundColor: "{colors.line-blue-pressed-light}"
    textColor: "{colors.on-line-blue-light}"
  button-secondary:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: 40px
  input:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: 40px
---

# Design System: EVOPT Maps

## Overview

**Creative North Star: "The Noorda Line"**

A route is a metro line and a charging stop is a station. The interface borrows the discipline of 1960s Milan metro signage and the transit-diagram tradition: enamel ground, dark rules, one saturated line colour (Milan M4 blue), one grotesque. It is built for people judging a project in a couple of minutes, so everything that matters is printed: minutes, kilowatt-hours and battery before and after at each stop.

The world supplies type, palette, density and one signature move. Navigation and controls stay standard: tabs, text inputs, a select, range sliders, buttons.

**Key Characteristics:**
- Warm-grey paper and ink (the telai.camossi neutrals), light and dark, one blue that means route, primary action or the active thing.
- Flat: no shadows, no gradients as decoration, zero radius except the round station rings.
- The signature move is the trip line: a vertical blue line with ringed stations, mirrored on the map.
- Every slider carries a live tabular readout.
- State changes are instant two-frame steps of 90 ms, no easing.

## Colors

A near-monochrome palette with a single signal colour.

### Primary
- **Line Blue** (#0057b8 light, #6aa6ff dark): the route line (map and diagram), the primary action, slider fill, the current tab and any active or hovered station. Pressed or hovered primary button is **Line Blue Pressed** (#00468f light, #94bfff dark).

### Neutral
- **Surface** (#ffffff light, #1c1f1d dark): panels, inputs, header. The page itself sits on **Canvas** (#f5f6f3, #0f1110).
- **Ink** (#16191a light, Chalk #e6e9e4 dark): text, 3px structural rules, ring outlines, input borders.
- **Map Ground** (#f4f4f4, #1f1f1f): behind the map tiles. Tiles stay neutral grey; dark mode inverts them with a CSS filter.
- **Rule** (#d9dcd7, #2e322f): list dividers; **Rule Strong** (#868d88, #6c746e): unfilled slider tracks.
- **Ink 2** (#5b625f, #a7aea8): helper text and secondary notes (5.8:1 on canvas in light, 8.4:1 in dark).

### Dark theme
Follows the system setting, with a header toggle that stores the choice. Same structure, different tokens: the accent lightens to #6aa6ff (7.7:1 on the dark canvas), text on it flips to the canvas colour, and the route casing becomes the canvas colour so the line stays separated from dark motorways (the route is 3:1 or better against the tiles only thanks to the casing).

### Named Rules
**The One Signal Rule.** Blue appears only on the route, the primary action, the slider fill, the active tab and the active station. If blue is not one of those, it is wrong.

**The No Colour Alone Rule.** State is never only a colour: errors carry an ink "!" badge and a heavy bar under the field, step status carries the words done, working or waiting.

## Typography

**Display, body and label font:** Helvetica Neue (with Helvetica, Arimo, Arial). One family throughout.

**Character:** neutral, signage-like, tabular. Figures use `font-variant-numeric: tabular-nums` so readouts do not jitter.

### Hierarchy
- **Display** (700, 2rem, 1.1): the trip's total time and page titles.
- **Headline** (700, 1.5rem, 1.2): panel titles ("Plan a trip", "Trip").
- **Title** (700, 1.25rem): slider readouts and the stats values.
- **Body** (400, 1rem, 1.5): prose, inputs. Prose measure 65ch.
- **Label** (700, 0.8125rem, 1.4): field labels. Helper text is 0.8125rem regular.

### Named Rules
**The One Family Rule.** No second typeface. Hierarchy comes from size and weight.

## Layout

An app shell: a 56px header with a 3px black rule, a 392px left rail and a map that fills the rest. The rail holds, from top, planning status or an error, the collapsible settings, then the result. Once a trip is planned the settings fold to a two-line summary so the result sits in the first viewport. Under 900px the layout stacks: settings, status or error, map, result.

Spacing sits on an 8px grid: 16px between fields, 24px panel padding, 40px control height, 48px primary action. The only sub-grid values are 4px label-to-input gaps and 2 to 5px borders.

## Elevation & Depth

Flat. Depth comes from 3px black rules between regions and from a canvas-coloured casing under the blue route on the map. There are no shadows.

## Shapes

Rectangles with square corners. The only curve is the station ring: a circle with a 5px ink outline and white fill (24px for start and end, 32px with a number for charging stops). Charging stations on the map are small hollow squares.

## Components

### Buttons
- **Primary:** Line Blue fill, bold text in the on-accent colour (white in light, canvas in dark), 48px high, full width, 0 radius. Hover goes to Line Blue Pressed. Disabled is Rule fill with Ink 2 text.
- **Secondary:** white, 2px ink border, 40px high. Hover inverts to ink.
- **Text:** underlined ink text for low-emphasis actions (Cancel).

### Inputs / Fields
- **Style:** 2px ink border, white, 40px high, 16px side padding. Select uses a drawn chevron.
- **Focus:** 3px ink outline offset 2px on every control.
- **Error:** a heavy 4px bar inside the bottom edge plus a "!" badge and message below.

### Sliders
Track 4px with Line Blue fill; thumb is a station ring (24px). The label row shows a live 1.25rem tabular readout.

### Navigation
Header tabs, bold 16px. The active tab has a 4px Line Blue underline that overlaps the header rule.

### Trip line (signature)
A vertical 8px Line Blue bar with ringed stations. Start and end are 24px rings; charging stops are 32px numbered rings. Each stop prints arrival charge, minutes charging, charge after, kWh and power. Hover or focus turns the ring and its name blue and highlights the same stop on the map.

### Data table
Used for the algorithm comparison. Full width inside the 960px page column, a 3px ink rule under the header row, 1px hairlines between rows, 16px cell padding, numeric columns right-aligned with tabular figures. The best row is bold; the selected algorithm carries a Line Blue "selected" word. Wrapped in a horizontal scroller on narrow screens.

### Advanced disclosure
A native details element with a hairline above, a bold summary and a drawn chevron. It keeps the algorithm, leg-energy and comparison options out of the way until wanted.

### Vehicle roster
Five equal cells with a 3px ink border: name block, two specs, action. The selected cell has a Line Blue name block and border.

## Do's and Don'ts

### Do:
- **Do** print the reasoning: each charging stop shows its minutes, kWh and charge before and after.
- **Do** keep every state change instant (two-frame, 90 ms, `steps(2, end)`).
- **Do** keep spacing on multiples of 8px.
- **Do** show the model's limits next to the result.

### Don't:
- **Don't** add shadows, gradients as decoration or rounded cards.
- **Don't** use blue for anything that is not route, primary action, slider fill, active tab or active station.
- **Don't** use a modal for planning: status and errors live in the rail.
- **Don't** colour map tiles; they stay grey so the blue line leads.
