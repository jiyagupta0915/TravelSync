# Week 14 : Floating Map

## Work done

+  Built the interactive map with Leaflet: a full map page for each trip
   and a floating map button, available from every page, that opens a
   panel with a trip picker.
+  Showed the destination, top places, saved stays and suggested stays as
   different pins, with a list beside the map.
+  Added an optional "Show my location" button, which only asks for
   permission when pressed.
+  Added driving distance and time using the Geoapify Route Matrix, with a
   straight-line distance as a fallback when it is unavailable.
+  Cached the distances for a day and limited live lookups to protect the
   free credits.
+  Fixed the layout so the map no longer covers the list in the panel and
   placed the map button directly above the chat button.