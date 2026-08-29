import { Routes, Route } from "react-router-dom";
import Landing from "../pages/Landing/Landing";
import Login from "../pages/Auth/Login";
import Signup from "../pages/Auth/Signup";
import Home from "../pages/Home/Home";
import SelectDestination from "../pages/Planner/SelectDestination";
import RecommendDestination from "../pages/Planner/RecommendDestination";
import ProtectedRoute from "./ProtectedRoute";

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
    </Routes>
  );
}