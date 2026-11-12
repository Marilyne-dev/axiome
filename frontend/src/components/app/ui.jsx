import { Link } from "react-router-dom";
export const Icon = ({ d, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);
export const ICONS = {
  home: <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5" /></>,
  folder: <path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  alert: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18v.5" /></>,
  gauge: <><path d="M4 18a8 8 0 1 1 16 0" /><path d="M12 18l4-6" /></>,
  logout: <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4M15 8l4 4-4 4M19 12H9" />,
  card: <><rect x="2.5" y="5" width="19" height="14" rx="2.5" /><path d="M2.5 10h19M6 15h4" /></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
};

const NIVEAUX = { faible: ["Faible", "ok"], modere: ["Modéré", "warn"], eleve: ["Élevé", "high"], critique: ["Critique", "ko"] };
export const RiskBadge = ({ niveau }) => {
  const [label, cls] = NIVEAUX[niveau] || ["—", "none"];
  return <span className={`badge b-${cls}`}>{label}</span>;
};
export const Progress = ({ value, max, tone = "blue" }) => (
  <div className="prog"><i className={`t-${tone}`} style={{ width: `${max ? Math.min(100, (value / max) * 100) : 0}%` }} /></div>
);
export const Loading = () => <div className="skeleton-wrap"><div className="skeleton" /><div className="skeleton" /><div className="skeleton s" /></div>;
export const ErrorBox = ({ message, onRetry }) => (
  <div className="app-card app-error"><b>Impossible de charger les données.</b><p>{message}</p>
    {onRetry && <button className="btn btn-ghost" onClick={onRetry}>Réessayer</button>}</div>
);
export const NoCabinet = () => (
  <div className="app-card empty">
    <div className="empty-ico"><Icon d={ICONS.folder} size={34} /></div>
    <h3>Votre compte n'est rattaché à aucun cabinet</h3>
    <p>Un cabinet est créé lors de l'abonnement à AXIOME. Tant qu'aucun cabinet n'est associé à ce compte, il n'y a ni client ni mission à afficher.</p>
  </div>
);
export const MissionsTable = ({ rows }) => (
  <div className="table-scroll"><table className="app-table">
    <thead><tr><th>Mission</th><th>Client</th><th>Exercice</th><th>Référentiel</th><th>Avancement</th><th>Risque</th></tr></thead>
    <tbody>{rows.map((m) => (
      <tr key={m.id}>
        <td><Link className="row-link" to={`/espace/missions/${m.id}`}><b>{m.intitule}</b></Link><span className="sub">{m.statut}</span></td>
        <td>{m.client}</td><td>{m.exercice || "—"}</td><td><span className="mono tag">{m.referentiel}</span></td>
        <td className="w-prog"><Progress value={m.avancement} max={100} /><span className="pct">{m.avancement} %</span></td>
        <td><RiskBadge niveau={m.risque_max} />{m.nb_anomalies ? <span className="sub">{m.nb_anomalies} anomalie(s)</span> : null}</td>
      </tr>))}
    </tbody></table></div>
);

export const Verrou = ({ statut }) => (
  <div className="app-card empty">
    <div className="empty-ico lock"><Icon d={ICONS.card} size={34} /></div>
    <h3>{statut === "expire" ? "Votre abonnement a expiré" : "Activez votre abonnement"}</h3>
    <p>{statut === "expire" ? "Renouvelez votre abonnement pour retrouver l'accès à vos clients et à vos missions. Vos données sont conservées."
      : "Votre espace est créé. Il sera accessible dès la confirmation du paiement."}</p>
    <a className="btn btn-primary" style={{ marginTop: 18 }} href="/espace/abonnement">Voir mon abonnement</a>
  </div>
);
