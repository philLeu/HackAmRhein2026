# Final demo readiness checklist

Use the V2 flow in [the five-minute story](demo-story.md). The older scenario and provider-replay controls are no longer part of the app.

## On the presentation laptop

1. Start the app from the repository root using the Python 3.12 instructions in the [README](../README.md). Open its local URL in the presentation browser; check the projector view, text size and power supply.
2. Open **Demo**, click **Reset demo**, and confirm that the fixed clock and three route buttons appear. Demo mode is the network-independent path.
3. Rehearse the two changes: set **Rotterdam → Basel** gauge to **470 cm** for the illustrative 12-hour delay; set **Production → Hospital** forecast snowfall to **Yes**. Check that the recommendation, route summaries and schedule update and that changing an input clears confirmation.
4. Confirm that the app labels simulated evidence and states route status in text as well as colour or icons. On the presentation screen, check that buttons, plan picker and detail expanders remain readable.
5. Run the full five-minute story twice with @philLeu speaking and @Fhuelin operating. Agree which optional click to skip if the first run is long. Reset Demo after the last rehearsal.

## Fallbacks

- If a live provider or venue Wi-Fi fails, switch to **Demo** and explain that the values are simulated. Do not describe them as current observations.
- If the app stops, restart it from the README command. Keep screenshots of the current Plan, changed route, and Sources & assumptions screens outside Git as a visual backup. The older `demo-fallback.svg` describes the former screen and should not be presented as a current screenshot.
- Bring the public repository link and the short submission summary. The app runs locally; `127.0.0.1` on another person's computer will not reach the presentation laptop.

The prototype uses invented treatment inputs, does not process patient data, and makes no clinical or transport booking decision.
