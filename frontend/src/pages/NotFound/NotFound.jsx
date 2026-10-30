import { Link } from "react-router-dom";
import { useAuth } from "../../context/useAuth";
import "../../styles/appPages.css";

// Shown for any URL that doesn't exist. It sits outside the signed-in shell, so it works for everyone.
export default function NotFound() {
  const { isAuthenticated } = useAuth();
  return (
    <main className="ts-notfound">
      <p className="dashboard__eyebrow">ERROR 404</p>
      <h1>We couldn't find that page</h1>
      <p>The link may be broken or the page may have moved.</p>
      <div className="ts-actions">
        <Link className="btn btn--primary" to={isAuthenticated ? "/home" : "/"}>{isAuthenticated ? "Go to your dashboard" : "Back to home"}</Link>
        {!isAuthenticated && <Link className="ts-btn-secondary" to="/login">Log in</Link>}
      </div>
    </main>
  );
}
