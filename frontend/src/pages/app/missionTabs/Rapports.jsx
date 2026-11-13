import { useEffect, useState } from "react";
import { telechargerRapport, telechargerRapportGeneral, getSuggestionsRapportGeneral } from "../../../api.js";
import { FIcon, FormAlert, useToast } from "../../../components/app/FormKit.jsx";

const RAPPORTS = [
  ["lettre-mission", "Lettre de mission", "Engagement du cabinet : objet, périmètre et référentiel de la mission.", "file", "blue"],
  ["note-synthese", "Note de synthèse", "Seuils de signification et conclusions par cycle, en une page.", "gauge", "green"],
  ["feuille-garde", "Feuille de garde", "Page de garde du dossier : avancement, risques et responsables.", "shield", "gold"],
];

const OPINIONS = [
  ["sans_reserve", "Certification sans réserve"],
  ["avec_reserves", "Certification avec réserve(s)"],
  ["refus", "Refus de certifier"],
];

function sauvegarder({ blob, nom }) {
  const u = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = u; a.download = nom; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}

const box = { border: "1px solid rgba(128,128,128,.35)", borderRadius: 12, padding: 16, marginTop: 18 };
const lab = { display: "block", fontWeight: 600, margin: "14px 0 6px" };
const area = { width: "100%", boxSizing: "border-box", padding: 8, borderRadius: 8, border: "1px solid rgba(128,128,128,.4)", font: "inherit" };

export default function Rapports({ m }) {
  const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [toast, show] = useToast();
  const [opinion, setOpinion] = useState("");
  const [motif, setMotif] = useState("");
  const [points, setPoints] = useState("");
  const [finale, setFinale] = useState(false);

  const charger = async (ecraser) => {
    try {
      const r = await getSuggestionsRapportGeneral(m.id);
      const txt = (r.points_cles || []).join("\n");
      setPoints((cur) => (ecraser || !cur.trim() ? txt : cur));
    } catch { /* suggestions facultatives */ }
  };
  useEffect(() => { charger(false); }, [m.id]);

  const go = async (type, format, titre) => {
    setBusy(`${type}.${format}`); setErr("");
    try { sauvegarder(await telechargerRapport(m.id, type, format)); show(`${titre} : téléchargement lancé`); }
    catch (e) { setErr(e.status >= 500 ? "Le serveur n'a pas pu générer ce document. La conversion PDF nécessite LibreOffice : essayez le format Word." : e.message); }
    setBusy("");
  };

  const lignes = points.split("\n").map((x) => x.trim()).filter(Boolean);
  const manque = [];
  if (!opinion) manque.push("Choisir la nature de l'opinion.");
  else if (opinion !== "sans_reserve" && !motif.trim()) manque.push("Le motif est obligatoire pour une réserve ou un refus.");
  if (!lignes.length) manque.push("Renseigner au moins un point clé.");

  const goGeneral = async (format) => {
    setBusy(`rg.${format}`); setErr("");
    try {
      const body = { opinion: opinion || null, motif, points_cles: lignes, finale };
      sauvegarder(await telechargerRapportGeneral(m.id, format, body));
      show(finale ? "Rapport général (version finale) : téléchargement lancé" : "Rapport général (projet) : téléchargement lancé");
    } catch (e) { setErr(e.status >= 500 ? "Le serveur n'a pas pu générer ce document. La conversion PDF nécessite LibreOffice : essayez le format Word." : e.message); }
    setBusy("");
  };

  const bloque = finale && manque.length > 0;

  return (
    <>
      <div className="tab-head"><div><h3>Rapports et livrables</h3><p className="muted">Documents générés automatiquement à partir des données du dossier, au format Word ou PDF.</p></div></div>
      <FormAlert>{err}</FormAlert>
      <div className="rep-grid">
        {RAPPORTS.map(([type, titre, desc, ic, tone], i) => (
          <div key={type} className={`rep-card r-${tone}`} style={{ "--i": i }}>
            <div className="rep-ico"><FIcon n={ic === "gauge" ? "clock" : ic} size={24} /></div>
            <h4>{titre}</h4><p>{desc}</p>
            <div className="rep-btns">
              {["docx", "pdf"].map((fm) => <button key={fm} type="button" disabled={!!busy} onClick={() => go(type, fm, titre)}>
                {busy === `${type}.${fm}` ? <i className="spin dark" /> : <FIcon n="download" size={16} />}{fm === "docx" ? "Word" : "PDF"}</button>)}
            </div>
          </div>))}
      </div>

      <div style={box}>
        <h4 style={{ margin: 0 }}>Rapport général de certification</h4>
        <p className="muted" style={{ marginTop: 4 }}>L'opinion est choisie par le signataire : l'application ne la décide jamais.</p>

        <span style={lab}>Nature de l'opinion</span>
        {OPINIONS.map(([val, lib]) => (
          <label key={val} style={{ display: "block", margin: "4px 0" }}>
            <input type="radio" name="opinion" checked={opinion === val} onChange={() => setOpinion(val)} /> {lib}
          </label>
        ))}

        {(opinion === "avec_reserves" || opinion === "refus") && (
          <>
            <label style={lab} htmlFor="rg-motif">{opinion === "refus" ? "Motif du refus de certifier" : "Motif de la réserve"}</label>
            <textarea id="rg-motif" rows={4} style={area} value={motif} onChange={(e) => setMotif(e.target.value)} />
          </>
        )}

        <label style={lab} htmlFor="rg-points">Points clés de l'audit (un par ligne)</label>
        <textarea id="rg-points" rows={6} style={area} value={points} onChange={(e) => setPoints(e.target.value)} />
        <button type="button" disabled={!!busy} style={{ marginTop: 6 }} onClick={() => charger(true)}>Recharger les suggestions du dossier</button>

        <label style={{ display: "block", marginTop: 16 }}>
          <input type="checkbox" checked={finale} onChange={(e) => setFinale(e.target.checked)} /> Version finale (sans bandeau « PROJET »)
        </label>

        {!finale && <p className="muted" style={{ marginBottom: 0 }}>Sans cette case, le document porte le bandeau rouge « PROJET — NON FINALISÉ ».</p>}
        {finale && manque.length > 0 && (
          <ul style={{ color: "#b00020", margin: "8px 0 0 18px" }}>{manque.map((x) => <li key={x}>{x}</li>)}</ul>
        )}

        <div className="rep-btns" style={{ marginTop: 14 }}>
          {["docx", "pdf"].map((fm) => <button key={fm} type="button" disabled={!!busy || bloque} onClick={() => goGeneral(fm)}>
            {busy === `rg.${fm}` ? <i className="spin dark" /> : <FIcon n="download" size={16} />}{fm === "docx" ? "Word" : "PDF"}</button>)}
        </div>
      </div>
      {toast}
    </>
  );
}