import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import Background from "../components/Background.jsx";
import bgImg from "../assets/auth-bg.svg";
import visImg from "../assets/auth-visual.svg";
import { AuthScene } from "../components/Illustrations.jsx";

const POINTS = ["Analyses FEC et DSN automatisées", "Dossier d'audit aligné sur les NEP", "Conformité IA Act, LCB-FT et RGPD"];

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="auth-page">
      <div className="auth-side">
        <div className="auth-img" style={{ backgroundImage: `url(${bgImg})` }} aria-hidden="true" />
        <Background variant="dark" />
        <Link to="/" className="logo"><Logo height={44} pill /></Link>
        <div className="auth-side-in">
          <figure className="auth-photo"><img src={visImg} alt="Tableau de bord d'audit AXIOME" /><figcaption><i />FEC analysé · 37 anomalies repérées</figcaption></figure>
          <AuthScene />
          <h2>L'audit légal augmenté par la donnée.</h2>
          <ul className="auth-points">
            {POINTS.map((p, i) => <li key={p} style={{ animationDelay: `${0.5 + i * 0.25}s` }}><span>✓</span>{p}</li>)}
          </ul>
        </div>
      </div>
      <div className="auth-main">
        <Background variant="light" />
        <div className="auth-card">
          <h1>{title}</h1>
          <p className="auth-sub">{subtitle}</p>
          {children}
          <p className="auth-foot">{footer}</p>
        </div>
      </div>
    </div>
  );
}
