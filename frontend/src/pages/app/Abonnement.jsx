import { useState } from "react";
import useAsync from "../../components/app/useAsync.js";
import { getAbonnement, payerAbonnement } from "../../api.js";
import { ErrorBox, Loading } from "../../components/app/ui.jsx";
import { fmtDate, fmtMontant } from "../../format.js";

const STATUTS = { actif: ["Actif", "ok"], en_attente_paiement: ["En attente de paiement", "warn"], expire: ["Expiré", "ko"], suspendu: ["Suspendu", "ko"], resilie: ["Résilié", "none"] };
const PAIEMENTS = { paye: ["Payé", "ok"], en_attente: ["En attente", "warn"], echoue: ["Échoué", "ko"] };
const Badge = ({ map, v }) => { const [l, c] = map[v] || [v, "none"]; return <span className={`badge b-${c}`}>{l}</span>; };

export default function Abonnement() {
  const { data, error, loading, reload } = useAsync(getAbonnement);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const payer = async () => {
    setBusy(true); setErr("");
    try { const r = await payerAbonnement(); window.location.assign(r.checkout_url); }
    catch (e) { setErr(e.message); setBusy(false); }
  };
  const a = data?.abonnement;
  return (
    <>
      <div className="page-head"><div><p className="eyebrow">Facturation</p><h1>Abonnement</h1></div></div>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && !a && <div className="app-card empty"><h3>Aucun abonnement</h3><p>Ce compte n'est rattaché à aucun cabinet.</p></div>}
      {a && (<>
        <div className="app-card">
          <div className="card-h"><h3>Offre {a.plan || "Sur mesure"}</h3><Badge map={STATUTS} v={a.statut} /></div>
          {a.plan ? (
            <div className="abo-grid">
              <div><small>Facturation</small><b>{a.periode === "annuel" ? "Annuelle" : "Mensuelle"} · {a.devise}</b></div>
              <div><small>Valable jusqu'au</small><b>{fmtDate(a.date_fin)}</b></div>
            </div>) : <p className="muted">Votre cabinet a été configuré directement par AXIOME : aucun paiement n'est requis.</p>}
          {data.peut_payer && a.plan && (
            <div style={{ marginTop: 18 }}>
              <button className="btn btn-primary" onClick={payer} disabled={busy}>{busy ? "Ouverture du paiement…" : a.statut === "actif" ? "Renouveler maintenant" : "Payer maintenant"}</button>
              {err && <div className="alert ko" style={{ marginTop: 12 }}>{err}</div>}
            </div>)}
        </div>
        {data.paiements.length > 0 && (
          <div className="app-card"><h3>Historique des paiements</h3>
            <div className="table-scroll"><table className="app-table"><thead><tr><th>Date</th><th>Période</th><th>Montant</th><th>Statut</th></tr></thead>
              <tbody>{data.paiements.map((p) => <tr key={p.reference}><td>{fmtDate(p.date)}</td><td>{p.periode === "annuel" ? "Annuelle" : "Mensuelle"}</td>
                <td><b>{fmtMontant(p.montant, p.devise)}</b></td><td><Badge map={PAIEMENTS} v={p.statut} /></td></tr>)}</tbody></table></div></div>)}
      </>)}
    </>
  );
}
