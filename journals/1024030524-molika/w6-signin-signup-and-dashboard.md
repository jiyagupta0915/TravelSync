# Week 6 : Sign In / Sign Up Pages and Home Dashboard

## Work done

+  Built the Login, Signup and Home Dashboard pages, which together with the
   Landing page make up the 4 core screens of the app.
+  Added the supporting architecture (auth context, protected routing and
   design tokens) that the rest of the team can build on directly.
+  Built a small reusable component system (Navbar, Sidebar, FeatureCard,
   TripPathCard, PasswordInput) instead of duplicating markup across pages.
+  Structured the mock authentication layer so that it can later be
   swapped for a real backend (FastAPI/JWT) without rewriting the
   components that use it, by keeping all mock logic behind a stable
   `AuthContext` interface.

## Problem faced and how I solved it

+  **Problem:** the initial mock login took the displayed name from the
   email address instead of the name entered at signup, so the dashboard
   greeting showed the wrong name after logging in again.
+  **Solution:** added a mock "users table" in `localStorage`, so that
   `login()` looks up the previously registered name instead of guessing
   it from the email.
