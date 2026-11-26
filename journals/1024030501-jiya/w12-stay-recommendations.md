# Week 12 : Stay Recommendations

## Work done

+  Built the stay recommendation feature. It finds hotels and other
   accommodation near a destination's top places using the Geoapify Places
   API (OpenStreetMap data).
+  Gave every stay a 0-100 match score from four explainable parts:
   location (40%), budget (30%), traveller type (20%) and quality (10%),
   with plain-English reasons shown next to each stay.
+  Cached the results in MongoDB for a week, so the free API credits last.

## Problem faced and how I solved it

+  **Problem:** the free Geoapify plan has a daily credit limit, so
   fetching stays on every page visit would use it up quickly.
+  **Solution:** cached results per destination and kept the API key on
   the server only.