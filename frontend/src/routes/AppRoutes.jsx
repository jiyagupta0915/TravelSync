import { Routes, Route } from "react-router-dom";
import Landing from "../pages/Landing/Landing";
import Login from "../pages/Auth/Login";
import Signup from "../pages/Auth/Signup";
import ForgotPassword from "../pages/Auth/ForgotPassword";
import ResetPassword from "../pages/Auth/ResetPassword";
import Home from "../pages/Home/Home";
import SelectDestination from "../pages/Planner/SelectDestination";
import RecommendDestination from "../pages/Planner/RecommendDestination";
import PackingHome from "../pages/Packing/PackingHome";
import PackingAssistant from "../pages/Packing/PackingAssistant";
import MyTrips from "../pages/Trips/MyTrips";
import TripHub from "../pages/Trips/TripHub";
import HealthSafety from "../pages/Health/HealthSafety";
import StaysHome from "../pages/Stays/StaysHome";
import StayRecommendations from "../pages/Stays/StayRecommendations";
import Groups from "../pages/Groups/Groups";
import GroupDetail from "../pages/Groups/GroupDetail";
import Bookings from "../pages/Bookings/Bookings";
import Profile from "../pages/Account/Profile";
import Settings from "../pages/Account/Settings";
import NotFound from "../pages/NotFound/NotFound";
import ProtectedRoute from "./ProtectedRoute";
import AppShell from "../components/AppShell/AppShell";

// All routes live here.
//  * Public pages: landing, auth, password recovery.
//  * Planner pages: signed-in, own top navigation (Navbar).
//  * Everything else signed-in renders inside <AppShell/>, the single sidebar + top bar layout.
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/planner/select-destination" element={<SelectDestination />} />
        <Route path="/planner/recommend" element={<RecommendDestination />} />

        <Route element={<AppShell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/trips" element={<MyTrips />} />
          <Route path="/trip/:tripId" element={<TripHub />} />
          <Route path="/packing" element={<PackingHome />} />
          <Route path="/trip/:tripId/packing" element={<PackingAssistant />} />
          <Route path="/stays" element={<StaysHome />} />
          <Route path="/trip/:tripId/stays" element={<StayRecommendations />} />
          <Route path="/health" element={<HealthSafety />} />
          <Route path="/groups" element={<Groups />} />
          <Route path="/groups/:groupId" element={<GroupDetail />} />
          <Route path="/bookings" element={<Bookings />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
