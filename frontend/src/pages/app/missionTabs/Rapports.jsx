import { useState } from "react";
import { telechargerRapport } from "../../../api.js";
import { FIcon, FormAlert, useToast } from "../../../components/app/FormKit.jsx";

const RAPPORTS = [
  ["lettre-mission", "Lettre de mission", "Engagement du cabinet : objet, périmètre et référentiel de la mission.", "file", "blue"],
  ["rapport-general", "Rapport général", "Livrable principal de certification, avec le cadre normatif applicable.", "scale", "violet"],
  ["note-synthese", "Note de synthèse", "Seuils de signification et conclusions par cycle, en une page.", "gauge", "green"],
  ["feuille-garde", "Feuille de garde", "Page de garde du dossier : avancement, risques et responsables.", "shield", "gold"],
];

function sauvegarder({ blob, nom }) {
  const u = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = u; a.download = nom; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}

export default function Rapports({ m }) {
  const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [toast, show] = useToast();
  const go = async (type, format, titre) => {
    setBusy(`${type}.${format}`); setErr("");
    try { sauvegarder(await telechargerRapport(m.id, type, format)); show(`${titre} : téléchargement lancé`); }
    catch (e) { setErr(e.status >= 500 ? "Le serveur n'a pas pu générer ce document. La conversion PDF nécessite LibreOffice : essayez le format Word." : e.message); }
    setBusy("");
  };
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
      {toast}
    </>
  );
}
