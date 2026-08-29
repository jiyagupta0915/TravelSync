import { useNavigate } from "react-router-dom";
import "./Planner.css";

// Placeholder for the future "Help me find one" KNN-based
// recommendation questionnaire workflow.
export default function RecommendDestination() {
  const navigate = useNavigate();

  return (
    <div className="planner-placeholder">
      <h1>Destination Recommendation</h1>
      <p>Coming next...</p>
      <button className="btn btn--ghost" onClick={() => navigate("/home")}>
        ← Back to Home
      </button>
    </div>
  );
}