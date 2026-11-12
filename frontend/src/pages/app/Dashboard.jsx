import { Link } from "react-router-dom";
import CountUp from "../../components/CountUp.jsx";
import useAsync from "../../components/app/useAsync.js";
import { getDashboard } from "../../api.js";
import { ErrorBox, Icon, ICONS, Loading, MissionsTable, NoCabinet, Verrou } from "../../components/app/ui.jsx";
import { HeroScene, RiskDonut, Ring } from "../../components/app/DashViz.jsx";
import { useAuth } from "../../context/AuthContext.jsx";

const RISQUES = [["critique", "Critique"], ["eleve", "Élevé"], ["modere", "Modéré"], ["faible", "Faible"]];
const jour = () => new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
const salut = () => { const h = new Date().getHours(); return h < 6 || h >= 18 ? "Bonsoir" : "Bonjour"; };

const Kpi = ({ icon, label, value, suffix, tone, i }) => (
  <div className={`kpi kx k-${tone}`} style={{ "--i": i }}>
    <div className="kx-glow" />
    <div className="kpi-ico"><Icon d={ICONS[icon]} /></div>
    <div><div className="kpi-v"><CountUp to={value} suffix={suffix} duration={1100} /></div><div className="kpi-l">{label}</div></div>
  </div>
);

const Quota = ({ label, q, color }) => {
  const illimite = !q.quota, plein = !illimite && q.utilises >= q.quota;
  return (
    <div className="quota-x">
      <Ring value={illimite ? 1 : q.utilises} max={illimite ? 1 : q.quota} color={plein ? "#DC3B4B" : color}>
        <b>{q.utilises}</b><small>{illimite ? "∞" : `/ ${q.quota}`}</small>
      </Ring>
      <div><h4>{label}</h4>
        <p>{illimite ? "Illimité avec votre offre" : plein ? <>Limite atteinte : <Link to="/espace/abonnement" className="lnk-offre">passez à une offre supérieure</Link></> : `${q.quota - q.utilises} restant(s)`}</p></div>
    </div>
  );
};

const ACTIONS = [
  ["/espace/clients", "users", "Nouveau client", "Ajouter une entité à auditer", "blue"],
  ["/espace/missions", "folder", "Nouvelle mission", "Ouvrir un dossier d'audit", "violet"],
  ["/espace/abonnement", "card", "Mon abonnement", "Offre, quotas et paiements", "gold"],
];

export default function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useAsync(getDashboard);
  const prenom = (user.nom_complet || user.email).split(" ")[0];
  const ok = data?.cabinet && !data.verrouille;
  return (
    <>
      <section className="hero-banner">
        <div className="hb-mesh" />
        <div className="hb-text">
          <p className="hb-date">{jour()}</p>
          <h1>{salut()}, {prenom} <span className="wave">👋</span></h1>
          <p className="hb-sub">{data?.cabinet ? <>{data.cabinet.nom} · {data.cabinet.pays}. {ok && data.kpis.anomalies > 0 ? `${data.kpis.anomalies} mission(s) demandent votre attention.` : "Votre activité d'audit en un coup d'œil."}</> : user.email}</p>
          {ok && <div className="hb-cta"><Link to="/espace/missions" className="btn btn-gold">Ouvrir une mission</Link><Link to="/espace/clients" className="btn btn-glass">Mes clients</Link></div>}
        </div>
        <HeroScene />
      </section>

      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && !data.cabinet && <NoCabinet />}
      {data?.verrouille && <Verrou statut={data.abonnement?.statut} />}

      {ok && (<>
        <div className="kpis">
          <Kpi i={0} icon="users" label="Clients" value={data.kpis.clients} tone="blue" />
          <Kpi i={1} icon="folder" label="Missions" value={data.kpis.missions} tone="violet" />
          <Kpi i={2} icon="alert" label="Missions à anomalies" value={data.kpis.anomalies} tone="red" />
          <Kpi i={3} icon="gauge" label="Avancement moyen" value={data.kpis.avancement_moyen} suffix=" %" tone="green" />
        </div>

        <div className="actions-row">
          {ACTIONS.map(([to, ic, t, d, tone], i) => (
            <Link key={to} to={to} className={`action a-${tone}`} style={{ "--i": i + 4 }}>
              <span className="action-ico"><Icon d={ICONS[ic]} /></span><span><b>{t}</b><small>{d}</small></span><i className="action-arrow">→</i>
            </Link>))}
        </div>

        <div className="grid-2 gx">
          <div className="app-card glass-card"><div className="card-h"><h3>Risques identifiés</h3><span className="chip">Tous dossiers</span></div>
            <RiskDonut data={data.risques_par_niveau} order={RISQUES} /></div>
          <div className="app-card glass-card"><div className="card-h"><h3>Capacité du cabinet</h3><span className="chip">Quotas</span></div>
            <div className="quotas-x"><Quota label="Collaborateurs" q={data.cabinet.collaborateurs} color="#7C5CFC" /><Quota label="Missions" q={data.cabinet.missions} color="#2F5BFF" /></div></div>
        </div>

        <div className="app-card"><div className="card-h"><h3>Missions récentes</h3><Link to="/espace/missions" className="link-soft">Voir toutes →</Link></div>
          {data.missions.length ? <MissionsTable rows={data.missions} /> : <p className="muted pad">Aucune mission pour le moment.</p>}</div>
      </>)}
    </>
  );
}
