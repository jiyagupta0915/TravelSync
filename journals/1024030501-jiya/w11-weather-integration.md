# Week 11 : Weather Integration for the Packing Assistant

## Work done

+  Added the second tier of the packing assistant: once a trip has travel
   dates, it fetches the real forecast from the Open-Meteo API and adjusts
   the weather-related items such as rain gear, warm layers and sun
   protection.
+  Chose Open-Meteo because it needs no API key.
+  Made the assistant fall back to the climate-based list when the
   forecast cannot be fetched, so the page never breaks.
+  Wrote tests for the packing rules.