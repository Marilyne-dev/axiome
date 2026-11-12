import CountUp from "./CountUp.jsx";

export const Stats = () => (
  <section className="stats-band">
    <div className="wrap stats">
      <div className="stat"><b><CountUp to={100} suffix="+" /></b><span>procédures précomplétées</span></div>
      <div className="stat"><b><CountUp to={4} /></b><span>livrables prêts à l'emploi</span></div>
      <div className="stat"><b><CountUp to={5} /></b><span>référentiels couverts</span></div>
      <div className="stat"><b><CountUp to={3} /></b><span>modules, un seul écosystème</span></div>
    </div>
  </section>
);

const I = (d) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{d}</svg>;
const STEPS = [
  { t: "Import du FEC", d: "FEC, grands livres et DSN chargés en quelques secondes.", c: "#2F5BFF",
    i: I(<path d="M6 3h8l4 4v14H6zM14 3v4h4M12 11v6M9 14l3 3 3-3" />) },
  { t: "Analyse ML", d: "Détection d'anomalies et réconciliation automatique.", c: "#7C5CFC",
    i: I(<path d="M4 18l5-6 4 3 7-9M4 21h16" />) },
  { t: "Papiers de travail", d: "100+ procédures précomplétées, prêtes pour le dossier.", c: "#1E7145",
    i: I(<><rect x="4" y="5" width="16" height="14" rx="2" /><path d="M4 10h16M10 5v14" /></>) },
  { t: "Revue & restitution", d: "Revue analytique commentée, Power BI, Word, PowerPoint.", c: "#E0A100",
    i: I(<path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16l2 2 4-4" />) },
  { t: "Certification", d: "Dossier documenté. L'opinion reste celle du commissaire.", c: "#7A6310",
    i: I(<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5" />) },
];

export const Pipeline = () => (
  <section className="section alt" id="process">
    <div className="wrap">
      <div className="sec-head">
        <div className="eyebrow">Du FEC à la certification</div>
        <h2>Chaque étape, automatisée et tracée.</h2>
      </div>
      <div className="pipe">
        <div className="pipe-line"><i /></div>
        {STEPS.map((s, i) => (
          <div className="pstep" key={s.t}>
            <div className="ico" style={{ color: s.c, animationDelay: `${i * 1.4}s` }}>{s.i}</div>
            <h4>{s.t}</h4><p>{s.d}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);
