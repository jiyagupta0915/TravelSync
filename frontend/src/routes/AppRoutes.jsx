import { Routes, Route } from "react-router-dom";
import Landing from "../pages/Landing/Landing";
import Login from "../pages/Auth/Login";
import Signup from "../pages/Auth/Signup";
import Home from "../pages/Home/Home";
import SelectDestination from "../pages/Planner/SelectDestination";
import RecommendDestination from "../pages/Planner/RecommendDestination";
import PackingHome from "../pages/Packing/PackingHome";
import PackingAssistant from "../pages/Packing/PackingAssistant";
import MyTrips from "../pages/Trips/MyTrips";
import TripHub from "../pages/Trips/TripHub";
import ProtectedRoute from "./ProtectedRoute";
import HealthSafety from "../pages/Health/HealthSafety";
import StaysHome from "../pages/Stays/StaysHome";
import StayRecommendations from "../pages/Stays/StayRecommendations";

// All app routes are centralized here so no component needs to
// know about routing structure beyond this file.
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />

      <Route
        path="/planner/select-destination"
        element={
          <ProtectedRoute>
            <SelectDestination />
          </ProtectedRoute>
        }
      />

      <Route
        path="/planner/recommend"
        element={
          <ProtectedRoute>
            <RecommendDestination />
          </ProtectedRoute>
        }
      />

      <Route
        path="/packing"
        element={
          <ProtectedRoute>
            <PackingHome />
          </ProtectedRoute>
        }
      />

      <Route
        path="/health"
        element={
          <ProtectedRoute>
            <HealthSafety />
          </ProtectedRoute>
        }
      />

      <Route
        path="/trip/:tripId/packing"
        element={
          <ProtectedRoute>
            <PackingAssistant />
          </ProtectedRoute>
        }
      />  

      <Route
        path="/stays"
        element={
          <ProtectedRoute>
            <StaysHome />
          </ProtectedRoute>
        }
      />

      <Route
        path="/trip/:tripId/stays"
        element={
          <ProtectedRoute>
            <StayRecommendations />
          </ProtectedRoute>
        }
      />

        <Route
        path="/trips"
        element={
          <ProtectedRoute>
            <MyTrips />
          </ProtectedRoute>
        }
      />

      <Route
        path="/trip/:tripId"
        element={
          <ProtectedRoute>
            <TripHub />
          </ProtectedRoute>
        }
      />

    </Routes>
  );
}