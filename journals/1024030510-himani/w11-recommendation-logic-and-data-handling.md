# Week 11 : Recommendation Logic and Data Handling

## Work done

+  Continued working on the recommendation logic and the way destination records are evaluated against the user's inputs.
+  The backend uses a content-based weighted KNN-style approach. Interest and traveller-type features are scaled using StandardScaler, and a weighted Euclidean distance is used to calculate preference similarity.
+  The recommendation engine first selects up to 60 candidates based on preference similarity and then considers trip-duration, budget and geographical-distance compatibility.
+  The final ranking combines preference similarity (60%), duration compatibility (15%), budget compatibility (15%) and distance compatibility (10%).
+  For distance calculations, the engine uses the Haversine formula with destination and starting-location coordinates. It can return a ranked list of recommendations, with six results as the default.
+  Reviewed how the returned destination information and scores are passed back by the FastAPI recommendation endpoint for display in the application.
