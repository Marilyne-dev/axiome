import { useState } from "react";
import useAsync from "../../../components/app/useAsync.js";
import { ajouterRisque, getHeatmap, getRisques } from "../../../api.js";
import { ErrorBox, Loading } from "../../../components/app/ui.jsx";
import { FIcon, useToast } from "../../../components/app/FormKit.jsx";
import { RiskDonut } from "../../../components/app/DashViz.jsx";
import QuickAdd from "./QuickAdd.jsx";

const NIVEAUX = { faible: ["Faible", "ok"], modere: ["Modéré", "warn"], eleve: ["Élevé", "high"], critique: ["Critique", "ko"] };
const niveau = (s) => (s >= 16 ? "critique" : s >= 9 ? "eleve" : s >= 4 ? "modere" : "faible");
const ORDRE = [["critique", "Critique"], ["eleve", "Élevé"], ["modere", "Modéré"], ["faible", "Faible"]];
const CATS = [["inherent", "Risque inhérent"], ["controle", "Risque de contrôle"], ["fraude", "Fraude"], ["continuite", "Continuité d'exploitation"], ["conformite", "Conformité"]];
const NIV5 = [[1, "1 · Très faible"], [2, "2 · Faible"], [3, "3 · Moyen"], [4, "4 · Élevé"], [5, "5 · Très élevé"]];

const Pastille = ({ score }) => { const [l, c] = NIVEAUX[niveau(score)]; return <span className={`badge b-${c}`}>{l} · {score}</span>; };

function Heat({ matrice }) {
  return (
    <div className="heat">
      <div className="heat-y">Impact</div>
      <div className="heat-grid">
        {[5, 4, 3, 2, 1].map((imp) => [1, 2, 3, 4, 5].map((pro) => {
          const n = matrice?.[imp - 1]?.[pro - 1] || 0;
          return <div key={`${imp}-${pro}`} className={`hc hc-${niveau(imp * pro)}${n ? " has" : ""}`} style={{ "--d": `${(imp + pro) * 45}ms` }} title={`Impact ${imp} × Probabilité ${pro}`}>{n > 0 && <b>{n}</b>}</div>;
        }))}
      </div>
      <div className="heat-x">Probabilité →</div>
    </div>
  );
}

export default function Risques({ m }) {
  const r = useAsync(() => getRisques(m.id), [m.id]);
  const h = useAsync(() => getHeatmap(m.id), [m.id]);
  const [open, setOpen] = useState(false);
  const [toast, show] = useToast();
  const rafraichir = () => { r.reload(); h.reload(); };
  return (
    <>
      <div className="tab-head"><div><h3>Cartographie des risques</h3><p className="muted">Probabilité × impact, priorisés automatiquement par score.</p></div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}><FIcon n="plus" size={16} />&nbsp;Ajouter un risque</button></div>
      <QuickAdd open={open} onClose={() => setOpen(false)} tone="violet" icon="shield" formId="form-risque" title="Nouveau risque" subtitle="Identifiez un risque et évaluez-le sur une échelle de 1 à 5."
        submitLabel="Ajouter le risque" initial={{ libelle: "", categorie: "inherent", probabilite: 3, impact: 3 }}
        fields={[{ k: "libelle", label: "Intitulé du risque", icon: "warn", required: true },
          { k: "categorie", label: "Catégorie", type: "select", icon: "tag", options: CATS },
          { k: "probabilite", label: "Probabilité", type: "seg", options: [1, 2, 3, 4, 5].map((n) => [n, String(n)]) },
          { k: "impact", label: "Impact", type: "seg", options: [1, 2, 3, 4, 5].map((n) => [n, String(n)]) }]}
        preview={(f) => <div className="score-prev"><span>Score estimé</span><Pastille score={(f.probabilite || 1) * (f.impact || 1)} /></div>}
        onSubmit={(f) => ajouterRisque(m.id, { libelle: f.libelle, categorie: f.categorie, probabilite: f.probabilite, impact: f.impact })}
        onDone={() => { setOpen(false); rafraichir(); show("Risque ajouté à la cartographie"); }} />
      {toast}
      {(r.loading || h.loading) && !r.data && <Loading />}
      {r.error && <ErrorBox message={r.error} onRetry={rafraichir} />}
      {h.data && (
        <div className="grid-2 gx">
          <div className="app-card"><div className="card-h"><h3>Matrice 5 × 5</h3><span className="chip">{h.data.total} risque(s)</span></div><Heat matrice={h.data.matrice} /></div>
          <div className="app-card"><div className="card-h"><h3>Répartition</h3><span className="chip">Par niveau</span></div><RiskDonut data={h.data.par_niveau} order={ORDRE} /></div>
        </div>)}
      {r.data && (
        <div className="app-card"><div className="card-h"><h3>Registre des risques</h3></div>
          {r.data.length ? (
            <div className="table-scroll"><table className="app-table"><thead><tr><th>Risque</th><th>Catégorie</th><th className="r">Prob.</th><th className="r">Impact</th><th>Niveau</th></tr></thead>
              <tbody>{r.data.map((x) => <tr key={x.id}><td><b>{x.libelle}</b></td><td><span className="tag">{(CATS.find(([c]) => c === x.categorie) || [, x.categorie])[1]}</span></td>
                <td className="r">{x.probabilite}</td><td className="r">{x.impact}</td><td><Pastille score={x.score} /></td></tr>)}</tbody></table></div>
          ) : <div className="empty-tab"><p>Aucun risque identifié pour cette mission. Cliquez sur « Ajouter un risque » pour commencer la cartographie.</p></div>}
        </div>)}
    </>
  );
}
