import { useState } from "react";
import useAsync from "../../components/app/useAsync.js";
import { changerOffre, getAbonnement, getOffres, payerAbonnement } from "../../api.js";
import { ErrorBox, Loading } from "../../components/app/ui.jsx";
import { fmtDate, fmtMontant } from "../../format.js";
import "../../offres.css";

const STATUTS = { actif: ["Actif", "ok"], en_attente_paiement: ["En attente de paiement", "warn"], expire: ["Expiré", "ko"], suspendu: ["Suspendu", "ko"], resilie: ["Résilié", "none"] };
const PAIEMENTS = { paye: ["Payé", "ok"], en_attente: ["En attente", "warn"], echoue: ["Échoué", "ko"] };
const Badge = ({ map, v }) => { const [l, c] = map[v] || [v, "none"]; return <span className={`badge b-${c}`}>{l}</span>; };

/** Choix d'une autre offre (montée ou descente) ou d'une autre période, puis paiement. */
function ChangerOffre({ abo }) {
  const { data, error, loading, reload } = useAsync(getOffres);
  const [periode, setPeriode] = useState(abo.periode || "mensuel");
  const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  if (loading) return <div className="app-card"><Loading /></div>;
  if (error) return <div className="app-card"><ErrorBox message={error} onRetry={reload} /></div>;
  if (!data?.peut_changer || !data.offres.length) return null;
  const devise = abo.devise;
  const courante = data.offres.find((o) => o.actuelle);
  const prixCourant = courante ? courante.prix[devise][abo.periode] : 0;

  const choisir = async (o) => {
    const prix = fmtMontant(o.prix[devise][periode], devise);
    const duree = periode === "annuel" ? "un an" : "un mois";
    const ok = window.confirm(`Passer à l'offre ${o.nom} (${periode === "annuel" ? "annuelle" : "mensuelle"}) ?\n\nVous allez régler ${prix}. L'offre change dès que le paiement est confirmé, et la nouvelle période de ${duree} démarre à ce moment-là.`);
    if (!ok) return;
    setBusy(o.code); setErr("");
    try { const r = await changerOffre(o.code, periode); window.location.assign(r.checkout_url); }
    catch (e) { setErr(e.message); setBusy(""); }
  };

  const libelle = (o) => {
    if (o.actuelle) return periode === abo.periode ? "Offre actuelle" : (periode === "annuel" ? "Passer en annuel" : "Passer en mensuel");
    return o.prix[devise][periode] >= prixCourant ? "Passer à cette offre" : "Choisir cette offre";
  };

  return (
    <div className="app-card">
      <div className="chg-head">
        <div><h3 style={{ marginBottom: 2 }}>Changer d'offre</h3><p>Montez en gamme quand votre cabinet grandit, ou ajustez votre formule.</p></div>
        <div className="toggle">
          {[["mensuel", "Mensuel"], ["annuel", "Annuel · 2 mois offerts"]].map(([v, l]) =>
            <button key={v} type="button" className={periode === v ? "on" : ""} onClick={() => setPeriode(v)}>{l}</button>)}
        </div>
      </div>
      <div className="plans chg">
        {data.offres.map((o) => {
          const identique = o.actuelle && periode === abo.periode;
          const bloque = identique || !o.possible || busy !== "";
          return (
            <div key={o.code} className={`plan${o.featured ? " feat" : ""}${o.actuelle ? " cur" : ""}${!o.possible ? " no" : ""}`}>
              <div className="pname">{o.nom}</div>
              <div className="pdesc">{o.description}</div>
              <div className="price">{fmtMontant(o.prix[devise][periode], devise)}<small> / {periode === "mensuel" ? "mois" : "an"}</small></div>
              <ul>{o.fonctionnalites.map((f) => <li key={f}><span className="tick">✓</span>{f}</li>)}</ul>
              {!o.possible && <div className="chg-why">Impossible pour l'instant : {o.raison}.</div>}
              <button type="button" className={`btn ${o.actuelle ? "btn-ghost" : "btn-primary"}`} disabled={bloque} onClick={() => choisir(o)}>
                {busy === o.code ? "Ouverture du paiement…" : libelle(o)}
              </button>
            </div>
          );
        })}
      </div>
      {err && <div className="alert ko" style={{ marginTop: 14 }}>{err}</div>}
      <p className="chg-note">Devise de facturation : {devise}. L'administrateur du cabinet n'est pas décompté des comptes inclus. Le changement prend effet à la confirmation du paiement ; la nouvelle période démarre alors immédiatement.</p>
    </div>
  );
}

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
        {data.peut_changer && a.plan && <ChangerOffre abo={a} />}
        {data.paiements.length > 0 && (
          <div className="app-card"><h3>Historique des paiements</h3>
            <div className="table-scroll"><table className="app-table"><thead><tr><th>Date</th><th>Période</th><th>Montant</th><th>Statut</th></tr></thead>
              <tbody>{data.paiements.map((p) => <tr key={p.reference}><td>{fmtDate(p.date)}</td><td>{p.periode === "annuel" ? "Annuelle" : "Mensuelle"}</td>
                <td><b>{fmtMontant(p.montant, p.devise)}</b></td><td><Badge map={PAIEMENTS} v={p.statut} /></td></tr>)}</tbody></table></div></div>)}
      </>)}
    </>
  );
}
