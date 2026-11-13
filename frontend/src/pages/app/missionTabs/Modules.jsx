import { useEffect, useRef, useState } from "react";
import { getTache, lancerDossierExcel, telechargerTache } from "../../../api.js";
import { MODULES_MISSION } from "../../../modules.js";
import { pick, useI18n } from "../../../i18n.jsx";
import "./modules.css";

function sauvegarder({ blob, nom }) {
  const u = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = u; a.download = nom; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}

// Génération du classeur complet en tâche de fond : lancement, suivi (polling) puis téléchargement.
function DossierArrierePlan({ missionId }) {
  const { t } = useI18n();
  const [etat, setEtat] = useState("idle"); const [tid, setTid] = useState(""); const [err, setErr] = useState("");
  const vivant = useRef(true);
  useEffect(() => () => { vivant.current = false; }, []);

  const suivre = async (id) => {
    try {
      const e = await getTache(id);
      if (!vivant.current) return;
      if (e.statut === "termine") setEtat("termine");
      else if (e.statut === "echec") { setErr(e.erreur || ""); setEtat("echec"); }
      else setTimeout(() => suivre(id), 1500);
    } catch (x) { if (vivant.current) { setErr(x.message); setEtat("echec"); } }
  };
  const lancer = async () => {
    setErr(""); setEtat("en_cours");
    try { const r = await lancerDossierExcel(missionId); setTid(r.id); suivre(r.id); }
    catch (x) { setErr(x.message); setEtat("echec"); }
  };
  return (
    <section className="modules-groupe">
      <div className="module-card static">
        <b>{t("mod.bg.title")}</b><span>{t("mod.bg.desc")}</span>
        {etat === "idle" && <button type="button" className="btn btn-primary" onClick={lancer}>{t("mod.bg.start")}</button>}
        {etat === "en_cours" && <span role="status">{t("mod.bg.running")}</span>}
        {etat === "termine" && <span><b>{t("mod.bg.done")}</b> <button type="button" className="btn btn-primary" onClick={async () => sauvegarder(await telechargerTache(tid))}>{t("mod.bg.download")}</button></span>}
        {etat === "echec" && <span className="alert ko">{t("mod.bg.fail")}{err ? ` : ${err}` : ""} <button type="button" className="btn" onClick={lancer}>{t("mod.bg.start")}</button></span>}
      </div>
    </section>
  );
}

// Onglet « Modules » : accès à tous les écrans d'audit rendus par le back pour cette mission.
// Navigation complète (<a>) : ces pages ne sont pas des routes React, elles sont servies par FastAPI
// sur la même origine (proxy Vite) et reconnaissent la session via le cookie posé à la connexion.
export default function Modules({ m }) {
  const { lang, t } = useI18n();
  return (
    <div className="modules">
      <p className="muted">{t("mod.intro", { mission: m.intitule })}</p>
      <DossierArrierePlan missionId={m.id} />
      {MODULES_MISSION.map((g) => (
        <section key={g.groupe.fr} className="modules-groupe">
          <h3>{pick(g.groupe, lang)}</h3>
          <div className="modules-grid">
            {g.items.map((it) => { const [titre, desc] = pick(it, lang); return (
              <a key={it.fr[0]} className="module-card" href={it.href(m.id)}>
                <b>{titre}</b><span>{desc}</span><em>{t("mod.open")}</em>
              </a>); })}
          </div>
        </section>
      ))}
    </div>
  );
}
