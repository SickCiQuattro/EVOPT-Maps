# Energy model, elevation and calibration

How the planner estimates the energy of a trip, how elevation enters, and how the vehicles were calibrated.

## Energy per road segment

For each road segment, at the segment speed:

```text
energy = (Crr·m·g + ½·ρ·CdA·v²) · distance / efficiency     rolling resistance and air drag
       + m·g·rise / efficiency                              climb (a descent recovers 60% instead)
       + aux(temperature) · time                            base load, plus climate control for the vehicles that use it
       + cold · distance · max(0, 18 - temperature)         cold penalty per km, calibrated
       + stop_go · distance · (70 - speed) / 20             below 70 km/h, calibrated
```

A segment's energy never goes below its auxiliary load: a descent saves energy but never charges the battery, which keeps every weight non-negative so Dijkstra, the battery limits and the heuristics stay valid.

Charging power follows the vehicle: constant on AC, tapering above 80% on fast DC chargers, and a fixed plug-in time is paid once per stop.

## Elevation

Node elevations come from terrain tiles on AWS Open Data (Terrarium, about 30 m, no key or login), sampled with bilinear interpolation, cached under `cache/dem/` and lightly smoothed along the road network. Turn it off per trip under **Advanced** to see how much it matters. `Planner(elevation=False)` does the same in code.

Measured on the real corridors, with the Tesla Model 3 (49 kWh usable) so a leg fits the battery:

| Trip | Net climb | Energy, flat | Energy, with elevation | Difference |
| --- | --- | --- | --- | --- |
| Milano to Torino, 145 km | +120 m | 32.23 kWh | 33.25 kWh | +1.01 kWh |
| Torino to Milano | −120 m | 31.62 kWh | 31.77 kWh | +0.14 kWh |
| Torino to Courmayeur, 149 km | +967 m | 28.97 kWh | 34.25 kWh | **+18%** |
| Courmayeur to Torino | −967 m | 29.02 kWh | 28.16 kWh | −3% |

With the Twingo (21.3 kWh usable, 0 °C, 3 minutes per stop), Torino to Courmayeur goes from 134.4 to 147.3 minutes and from one stop to two. The same trip in the web app, with Courmayeur geocoded at 1,677 m, goes from 2 h 20 to 2 h 35.

What to trust, and what not:

- **Climbs are close to physics:** the Torino to Courmayeur climb costs 5.3 kWh against about 4.9 kWh of potential energy over efficiency.
- **Descents are prudent:** the model gives back 60% and never below zero, so Courmayeur to Torino saves 0.9 kWh where the physics suggests 1.5 to 2.7.
- **Elevation noise is real.** On the flat Milano to Torino corridor, raw terrain data added about +0.9 kWh of spurious energy in both directions (bridges and viaducts read as dips, so climbs are paid in full and descents only partly refunded). Smoothing the elevations along the network brings it to about +0.5 kWh, roughly 2%, part of which is real rolling terrain. On the Torino to Courmayeur path the gross ascent is 442 m and the gross descent 1,409 m for a net −967 m, which is why the app shows the net climb and the highest point, not the gross figures.
- Segments steeper than a 12% average are capped, to protect against data glitches (39 of 446 segments on that path).

## Calibration

Vehicle consumption is calibrated on public figures from [EV Database](https://ev-database.org) for four of the five vehicles (the Twizy has no comparable data and keeps approximate values, marked as such in the app). The reference gives usable battery, kerb mass and consumption in town, on the motorway at a constant 110 km/h, and combined, in mild weather (23 °C) and in the cold (−10 °C, heating on). These are estimates built from tests and the WLTP cycle, not instrumented measurements of this project.

Three parameters per vehicle are fitted, with rolling resistance (0.010) and drivetrain efficiency (0.90) fixed:

1. the effective drag area, on the motorway consumption in mild weather;
2. the cold penalty per kilometre, on the difference between cold and mild on the motorway;
3. the stop-and-go overhead below 70 km/h, on the urban consumption in mild weather.

The cold penalty is modelled per kilometre, not per hour, because the reference shows almost the same cold surcharge in town (54 to 57 Wh/km) and on the motorway (50 to 59 Wh/km), which constant heating power would not.

Before and after, range at 110 km/h against the reference (`uv run python -m benchmarks.calibrate` prints every point):

| Vehicle | Mild, before | Cold, before | Mild and cold, after | Urban cold, held out |
| --- | --- | --- | --- | --- |
| Tesla Model 3 SR+ | +18% | +32% | 0% | −4% |
| Renault Twingo Electric | +20% | +37% | 0% | +3% |
| Fiat 500e | +21% | +36% | 0% | −3% |
| MINI Electric | +19% | +37% | 0% | 0% |

The earlier model was too optimistic: it overstated range at 110 km/h by 18 to 37%. The last column is a point the fit never used (urban consumption in the cold), predicted within 4%. The calibration also changed the plans: Milano to Torino with the Twingo went from one stop and 113.8 minutes to two stops and 142.6 minutes.

Limits: the fit leans on one source and on a modelled "constant 110 km/h"; hot-weather consumption (above 24 °C) is not calibrated; the urban term is fitted at one point (50 km/h); the plans run at the speed limit, so on a motorway at 130 km/h consumption is about a third above the 110 km/h reference.

