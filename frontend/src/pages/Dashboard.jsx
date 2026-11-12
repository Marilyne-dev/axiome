import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Dashboard() {
  const { user, logout } = useAuth();
  return (
    <div className="wrap" style={{ padding: "80px 24px" }}>
      <p className="eyebrow" style={{ color: "var(--blue)" }}>Espace client</p>
      <h1 style={{ fontFamily: "var(--disp)", fontSize: 40, letterSpacing: -1, margin: "12px 0" }}>
        Bonjour {user.nom_complet || user.email}
      </h1>
      <p style={{ color: "var(--slate)" }}>{user.email} · {user.roles.join(", ")}</p>
      <p style={{ margin: "24px 0", maxWidth: "56ch" }}>
        Votre compte est actif. Les modules Analytics, Plateforme et Link apparaîtront ici.
      </p>
      <div className="hero-cta" style={{ justifyContent: "flex-start" }}>
        <Link to="/" className="btn btn-light">Retour au site</Link>
        <button className="btn btn-ghost" onClick={logout}>Se déconnecter</button>
      </div>
    </div>
  );
}
