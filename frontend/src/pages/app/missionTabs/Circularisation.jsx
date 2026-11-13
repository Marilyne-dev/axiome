import { useState } from "react";
import useAsync from "../../../components/app/useAsync.js";
import { confirmationRecue, creerConfirmation, getConfirmations, relancerConfirmation, supprimerConfirmation } from "../../../api.js";
import { ErrorBox, Loading, Progress } from "../../../components/app/ui.jsx";
import { FIcon, FormAlert, useToast } from "../../../components/app/FormKit.jsx";
import QuickAdd from "./QuickAdd.jsx";
import "../../../audit.css";

const TYPES = [["banque", "Banque"], ["client", "Client"], ["fournisseur", "Fournisseur"], ["avocat", "Avocat"], ["assurance", "Assurance"], ["fiscal", "Administration fiscale"], ["social", "Organisme social"]];
const STATUTS = { envoyee: ["Envoyée", "info"], relancee: ["Relancée", "warn"], recue: ["Reçue", "ok"] };
const libType = (c) => (TYPES.find(([k]) => k === c) || [, c])[1];
const date = (iso) => (iso ? new Date(iso).toLocaleDateString("fr-FR") : "—");

/* Circularisation : demandes de confirmation aux tiers, relances et réceptions. */
export default function Circularisation({ m }) {
  const l = useAsync(() => getConfirmations(m.id), [m.id]);
  const [open, setOpen] = useState(false); const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  const [aSupprimer, setASupprimer] = useState(0); const [toast, show] = useToast();
  const rows = l.data || [];
  const nb = (s) => rows.filter((c) => c.statut === s).length;
  const recues = nb("recue");

  const agir = async (cle, fn, msg) => {
    setBusy(cle); setErr("");
    try { await fn(); await l.reload(); if (msg) show(msg); } catch (e) { setErr(e.message); }
    setBusy(""); setASupprimer(0);
  };

  return (
    <>
      <div className="tab-head"><div><h3>Circularisation</h3><p className="muted">Confirmations externes : suivez chaque demande, relancez les tiers silencieux et marquez les réponses reçues.</p></div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}><FIcon n="plus" size={16} />&nbsp;Nouvelle demande</button></div>
      <QuickAdd open={open} onClose={() => setOpen(false)} tone="blue" icon="users" formId="form-confirmation" title="Nouvelle demande de confirmation"
        subtitle="Indiquez le tiers à interroger : la demande est enregistrée comme envoyée." submitLabel="Enregistrer la demande"
        initial={{ tiers: "", type_tiers: "banque" }}
        fields={[{ k: "tiers", label: "Nom du tiers", icon: "building", required: true, hint: "Ex. BNP Paribas, Cabinet Martin (avocat)" },
          { k: "type_tiers", label: "Type de tiers", type: "select", icon: "tag", options: TYPES }]}
        onSubmit={(f) => creerConfirmation(m.id, { tiers: f.tiers.trim(), type_tiers: f.type_tiers })}
        onDone={() => { setOpen(false); l.reload(); show("Demande de confirmation enregistrée"); }} />
      {toast}
      <FormAlert>{err}</FormAlert>
      {l.loading && !l.data && <Loading />}
      {l.error && <ErrorBox message={l.error} onRetry={l.reload} />}
      {l.data && (
        <>
          <div className="circ-kpis">
            <div className="ck"><span>Demandes</span><b>{rows.length}</b></div>
            <div className="ck"><span>Envoyées</span><b>{nb("envoyee")}</b></div>
            <div className="ck"><span>Relancées</span><b>{nb("relancee")}</b></div>
            <div className="ck ck-ok"><span>Reçues</span><b>{recues}</b></div>
          </div>
          <div className="app-card">
            <div className="card-h"><h3>Suivi des confirmations</h3>{rows.length > 0 && <span className="chip">{recues} / {rows.length} reçues</span>}</div>
            {rows.length > 0 && <div className="prog-line"><Progress value={recues} max={rows.length} tone="green" /><span>{Math.round((recues / rows.length) * 100)} %</span></div>}
            {rows.length ? (
              <div className="table-scroll"><table className="app-table">
                <thead><tr><th>Tiers</th><th>Type</th><th>Statut</th><th>Créée le</th><th className="r">Actions</th></tr></thead>
                <tbody>{rows.map((c) => {
                  const [lib, tone] = STATUTS[c.statut] || [c.statut, "none"];
                  return (
                    <tr key={c.id}>
                      <td><b>{c.tiers}</b></td><td><span className="tag">{libType(c.type_tiers)}</span></td>
                      <td><span className={`badge b-${tone}`}>{lib}</span></td><td>{date(c.cree_le)}</td>
                      <td className="r"><div className="row-actions">
                        {c.statut !== "recue" && <>
                          <button type="button" className="btn-mini" disabled={!!busy} onClick={() => agir(`r${c.id}`, () => relancerConfirmation(m.id, c.id), "Relance enregistrée")}>
                            {busy === `r${c.id}` ? <i className="spin dark" /> : "Relancer"}</button>
                          <button type="button" className="btn-mini ok" disabled={!!busy} onClick={() => agir(`o${c.id}`, () => confirmationRecue(m.id, c.id), "Confirmation marquée comme reçue")}>
                            {busy === `o${c.id}` ? <i className="spin dark" /> : "Marquer reçue"}</button></>}
                        {aSupprimer === c.id
                          ? <><button type="button" className="btn-mini danger" disabled={!!busy} onClick={() => agir(`s${c.id}`, () => supprimerConfirmation(m.id, c.id), "Demande supprimée")}>Confirmer</button>
                              <button type="button" className="btn-mini" onClick={() => setASupprimer(0)}>Annuler</button></>
                          : <button type="button" className="btn-mini danger" disabled={!!busy} onClick={() => setASupprimer(c.id)}>Supprimer</button>}
                      </div></td>
                    </tr>);
                })}</tbody></table></div>
            ) : <div className="empty-tab"><p>Aucune demande de confirmation pour cette mission. Cliquez sur « Nouvelle demande » pour circulariser une banque, un client ou un fournisseur.</p></div>}
          </div>
        </>)}
    </>
  );
}
