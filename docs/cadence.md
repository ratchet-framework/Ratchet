# Cadence

Track anything that needs regular attention based on time elapsed, usage accumulated, or both — whichever threshold hits first.

## The problem

Calendar reminders fire on fixed dates. Real-world maintenance doesn't work that way. An oil change is due at 5,000 miles *or* 6 months — whichever comes first. If you drove hard this month, the calendar reminder is wrong. If the car sat in the garage all winter, the mileage reminder is wrong.

Cadence tracks both dimensions simultaneously and projects when you'll hit each threshold — so you get the right alert at the right time, not a fixed date you set and forgot about.

## What it tracks

Anything with:
- A **last serviced** date and/or usage reading
- One or more **thresholds** (time, usage, or both)
- An **alert window** (warn me X days or X units before I hit the threshold)

### Examples

| Item | Time threshold | Usage threshold |
|------|---------------|-----------------|
| Car oil change | 6 months | 5,000 miles |
| Running shoes | — | 500 miles |
| HVAC filter | 90 days | — |
| Dentist | 6 months | — |
| Bike chain | — | 2,000 miles |
| Water heater flush | 12 months | — |
| Laptop deep clean | 90 days | — |

## Data model

```json
{
  "items": [
    {
      "id": "string",
      "label": "Human-readable name",
      "category": "vehicle | home | health | fitness | equipment | other",
      "lastServiceDate": "YYYY-MM-DD",
      "lastServiceUsage": 0,
      "currentUsage": 0,
      "usageUnit": "miles | hours | km | sessions | null",
      "thresholds": {
        "time":  { "value": 6, "unit": "months" },
        "usage": { "value": 5000, "unit": "miles" }
      },
      "alertWindow": {
        "time":  { "value": 2, "unit": "weeks" },
        "usage": { "value": 500, "unit": "miles" }
      },
      "notes": ""
    }
  ]
}
```

Either threshold is optional. An item can have time-only, usage-only, or both.

## Agent integration

The Cadence checker runs on each heartbeat and surfaces upcoming items in the daily briefing:

```
🔧 Cadence alerts:
  WRX oil change — due in ~300 miles or 3 weeks (whichever first)
  HVAC filter — overdue by 12 days
```

Items in the alert window appear in briefings. Overdue items appear in every briefing until resolved.

## Projection

If the agent knows your typical usage rate (e.g. average weekly mileage from recent updates), it can project:

> "At your current rate of ~250 miles/week, WRX oil change is due in approximately 18 days."

Usage rate is calculated from the history of `currentUsage` updates over time.

## Resolving an item

When maintenance is done, update `lastServiceDate`, `lastServiceUsage`, and reset `currentUsage` delta. The clock and counter restart from zero.

## Capability unlock

Add `cadence` to your `capabilities.json` once you have at least one item tracked and alerting.
