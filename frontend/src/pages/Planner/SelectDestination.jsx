import { useNavigate } from "react-router-dom";
import "./Planner.css";

// Placeholder for the future "I know my destination" workflow
// (destination search, place details, weather, hotels, etc.).
export default function SelectDestination() {
  const navigate = useNavigate();

  return (
    <div className="planner-placeholder">
      <h1>Known Destination Planner</h1>
      <p>Coming next...</p>
      <button className="btn btn--ghost" onClick={() => navigate("/home")}>
        ← Back to Home
      </button>
    </div>
  );
}