import { useState } from "react";
import { Link } from "react-router-dom";
import useAsync from "../../components/app/useAsync.js";
import { getMissions } from "../../api.js";
import { ErrorBox, Loading, Verrou } from "../../components/app/ui.jsx";
import { MODULES_MISSION } from "../../modules.js";
import { pick, useI18n } from "../../i18n.jsx";
import "./missionTabs/modules.css";

const TXT = {
  fr: {
    title: "Modules d'audit", sub: "Choisissez une mission : tous ses modules (cycles, FEC, rapprochement bancaire, TVA, paie, CSRD, fusion…) s'ouvrent d'ici.",
    mission: "Mission", open: "Ouvrir →", dossier: "Ouvrir le dossier de la mission (rapports, risques, planification…)",
    none: "Aucune mission pour le moment. Créez d'abord une mission pour accéder à ses modules.", create: "Aller aux missions",
  },
  en: {
    title: "Audit modules", sub: "Pick an engagement: all its modules (cycles, FEC, bank reconciliation, VAT, payroll, CSRD, merger…) open from here.",
    mission: "Engagement", open: "Open →", dossier: "Open the engagement file (reports, risks, planning…)",
    none: "No engagement yet. Create one first to reach its modules.", create: "Go to engagements",
  },
};

// Accès direct aux modules d'une mission depuis le menu : on choisit la mission, puis on ouvre le module voulu.
export default function ModulesHub() {
  const { lang } = useI18n();
  const L = TXT[lang] || TXT.fr;
  const { data, error, status, loading, reload } = useAsync(getMissions);
  const [sel, setSel] = useState("");
  const missions = data || [];
  const m = missions.find((x) => String(x.id) === sel) || missions[0];

  return (
    <>
      <div className="page-head"><div><h1>{L.title}</h1><p className="muted">{L.sub}</p></div></div>
      {status === 402 && <Verrou />}
      {error && status !== 402 && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && !m && <div className="app-card"><p className="muted pad">{L.none}</p><p className="pad"><Link className="btn btn-primary" to="/espace/missions">{L.create}</Link></p></div>}
      {m && (
        <div className="modules">
          <div className="app-card" style={{ padding: 16, marginBottom: 16 }}>
            <label htmlFor="hub-mission" style={{ display: "block", fontWeight: 600, marginBottom: 6 }}>{L.mission}</label>
            <select id="hub-mission" value={String(m.id)} onChange={(e) => setSel(e.target.value)}
              style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(128,128,128,.4)", font: "inherit", background: "#fff" }}>
              {missions.map((x) => <option key={x.id} value={String(x.id)}>{x.client ? `${x.client} : ` : ""}{x.intitule}{x.exercice ? ` (${x.exercice})` : ""}</option>)}
            </select>
            <p style={{ marginBottom: 0 }}><Link to={`/espace/missions/${m.id}`}>{L.dossier}</Link></p>
          </div>
          {MODULES_MISSION.map((g) => (
            <section key={g.groupe.fr} className="modules-groupe">
              <h3>{pick(g.groupe, lang)}</h3>
              <div className="modules-grid">
                {g.items.map((it) => { const [titre, desc] = pick(it, lang); return (
                  <a key={it.fr[0]} className="module-card" href={it.href(m.id)}>
                    <b>{titre}</b><span>{desc}</span><em>{L.open}</em>
                  </a>); })}
              </div>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
