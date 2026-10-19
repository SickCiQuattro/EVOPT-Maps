---
name: EVOPT Maps
description: Noorda Line, a metro-signage design system for an electric-vehicle route planner where the trip is a line and each charging stop is a station.
colors:
  paper: "#ffffff"
  ink: "#111111"
  line-red: "#e30613"
  line-red-pressed: "#b8000f"
  map-ground: "#efefec"
  hairline: "#cfcfcf"
  muted-ink: "#555555"
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
    backgroundColor: "{colors.line-red}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    height: 48px
  button-primary-hover:
    backgroundColor: "{colors.line-red-pressed}"
    textColor: "{colors.paper}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: 40px
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: 40px
---

# Design System: EVOPT Maps

## Overview

**Creative North Star: "The Noorda Line"**

A route is a metro line and a charging stop is a station. The interface borrows the discipline of 1960s Milan metro signage and the transit-diagram tradition: white enamel ground, black rules, one saturated line colour, one grotesque. It is built for people judging a project in a couple of minutes, so everything that matters is printed: minutes, kilowatt-hours and battery before and after at each stop.

The world supplies type, palette, density and one signature move. Navigation and controls stay standard: tabs, text inputs, a select, range sliders, buttons.

**Key Characteristics:**
- White paper, black ink, one red that means route, primary action or the active thing.
- Flat: no shadows, no gradients as decoration, zero radius except the round station rings.
- The signature move is the trip line: a vertical red line with ringed stations, mirrored on the map.
- Every slider carries a live tabular readout.
- State changes are instant two-frame steps of 90 ms, no easing.

## Colors

A near-monochrome palette with a single signal colour.

### Primary
- **Line Red** (#e30613): the route line (map and diagram), the primary action, slider fill, the current tab and any active or hovered station. Pressed or hovered primary button is **Line Red Pressed** (#b8000f).

### Neutral
- **Paper** (#ffffff): panels, inputs, header.
- **Ink** (#111111): text, 3px structural rules, ring outlines, input borders.
- **Map Ground** (#efefec): behind the map tiles. Tiles are shown in grey.
- **Hairline** (#cfcfcf): slider tracks, list dividers.
- **Muted Ink** (#555555): helper text and secondary notes (7.5:1 on paper).

### Named Rules
**The One Signal Rule.** Red appears only on the route, the primary action, the slider fill, the active tab and the active station. If red is not one of those, it is wrong.

**The No Colour Alone Rule.** State is never only a colour: errors carry a black "!" badge and a heavy bar under the field, step status carries the words done, working or waiting.

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

Flat. Depth comes from 3px black rules between regions and from a white casing under the red route on the map. There are no shadows.

## Shapes

Rectangles with square corners. The only curve is the station ring: a circle with a 5px ink outline and white fill (24px for start and end, 32px with a number for charging stops). Charging stations on the map are small hollow squares.

## Components

### Buttons
- **Primary:** Line Red fill, white bold text, 48px high, full width, 0 radius. Hover goes to Line Red Pressed. Disabled is Hairline fill with Muted Ink text.
- **Secondary:** white, 2px ink border, 40px high. Hover inverts to ink.
- **Text:** underlined ink text for low-emphasis actions (Cancel).

### Inputs / Fields
- **Style:** 2px ink border, white, 40px high, 16px side padding. Select uses a drawn chevron.
- **Focus:** 3px ink outline offset 2px on every control.
- **Error:** a heavy 4px bar inside the bottom edge plus a "!" badge and message below.

### Sliders
Track 4px with Line Red fill; thumb is a station ring (24px). The label row shows a live 1.25rem tabular readout.

### Navigation
Header tabs, bold 15px. The active tab has a 4px Line Red underline that overlaps the header rule.

### Trip line (signature)
A vertical 8px Line Red bar with ringed stations. Start and end are 24px rings; charging stops are 32px numbered rings. Each stop prints arrival charge, minutes charging, charge after, kWh and power. Hover or focus turns the ring and its name red and highlights the same stop on the map.

### Vehicle roster
Five equal cells with a 3px ink border: name block, two specs, action. The selected cell has a Line Red name block and border.

## Do's and Don'ts

### Do:
- **Do** print the reasoning: each charging stop shows its minutes, kWh and charge before and after.
- **Do** keep every state change instant (two-frame, 90 ms, `steps(2, end)`).
- **Do** keep spacing on multiples of 8px.
- **Do** show the model's limits next to the result.

### Don't:
- **Don't** add shadows, gradients as decoration or rounded cards.
- **Don't** use red for anything that is not route, primary action, slider fill, active tab or active station.
- **Don't** use a modal for planning: status and errors live in the rail.
- **Don't** colour map tiles; they stay grey so the red line leads.
