import { useEffect, useState } from "react";
import useAsync from "../../../components/app/useAsync.js";
import { deciderAcceptation, genererLettre, getAcceptation, majAcceptation } from "../../../api.js";
import { ErrorBox, Loading } from "../../../components/app/ui.jsx";
import { FIcon, FormAlert, Segmented, Switch, Textarea, useToast } from "../../../components/app/FormKit.jsx";

const ETATS = { acceptee: ["Mission acceptée", "ok", "check"], refusee: ["Mission refusée", "ko", "close"] };

export default function Acceptation({ m, reload }) {
  const a = useAsync(() => getAcceptation(m.id), [m.id]);
  const [f, setF] = useState(null); const [motif, setMotif] = useState("");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState("");
  const [lettre, setLettre] = useState(null); const [toast, show] = useToast();
  useEffect(() => { if (a.data) { setF({ independance_ok: a.data.independance_ok, conflit_interet: a.data.conflit_interet, kyc_ok: a.data.kyc_ok, continuite_exploitation_ok: a.data.continuite_exploitation_ok, niveau_risque_global: a.data.niveau_risque_global }); setMotif(a.data.motivation || ""); } }, [a.data]);

  const enregistrer = async () => { setBusy("save"); setErr(""); try { await majAcceptation(m.id, { ...f, questionnaire: {} }); await a.reload(); show("Évaluation enregistrée"); } catch (e) { setErr(e.message); } setBusy(""); };
  const decider = async (decision) => {
    if (!window.confirm(decision === "acceptee" ? "Confirmer l'acceptation de la mission ?" : "Confirmer le refus de la mission ?")) return;
    setBusy(decision); setErr("");
    try { await majAcceptation(m.id, { ...f, questionnaire: {} }); await deciderAcceptation(m.id, { decision, motivation: motif }); await a.reload(); reload(); show(decision === "acceptee" ? "Mission acceptée" : "Mission refusée"); } catch (e) { setErr(e.message); }
    setBusy("");
  };
  const lettreGo = async () => { setBusy("lettre"); setErr(""); try { setLettre(await genererLettre(m.id)); show("Brouillon de lettre généré"); } catch (e) { setErr(e.message); } setBusy(""); };

  if (a.loading && !a.data) return <Loading />;
  if (a.error) return <ErrorBox message={a.error} onRetry={a.reload} />;
  if (!f) return null;
  const set = (k) => (v) => setF({ ...f, [k]: v });
  const etat = ETATS[a.data.decision];
  const pts = [f.independance_ok, !f.conflit_interet, f.kyc_ok, f.continuite_exploitation_ok].filter(Boolean).length;
  return (
    <>
      <div className="tab-head"><div><h3>Acceptation et maintien de la mission</h3><p className="muted">Indépendance, KYC, conflits d'intérêts. La décision finale est un acte humain, tracé.</p></div>
        {etat ? <span className={`status-big s-${etat[1]}`}><FIcon n={etat[2]} size={18} />{etat[0]}</span> : <span className="status-big s-wait"><FIcon n="clock" size={18} />Décision en attente</span>}</div>
      <div className="grid-2 gx">
        <div className="app-card">
          <div className="card-h"><h3>Évaluation préalable</h3><span className="chip">{pts} / 4 points favorables</span></div>
          <div className="sw-list">
            <Switch checked={f.independance_ok} onChange={set("independance_ok")} label="Indépendance vérifiée" hint="Aucune situation menaçant l'indépendance" />
            <Switch checked={f.kyc_ok} onChange={set("kyc_ok")} label="Connaissance du client (KYC) complète" hint="Identité, bénéficiaires effectifs, activité" />
            <Switch checked={f.continuite_exploitation_ok} onChange={set("continuite_exploitation_ok")} label="Continuité d'exploitation plausible" hint="Pas d'alerte majeure sur la pérennité" />
            <Switch tone="danger" checked={f.conflit_interet} onChange={set("conflit_interet")} label="Conflit d'intérêts identifié" hint="Bloque l'acceptation tant qu'il n'est pas levé" />
          </div>
          <Segmented label="Niveau de risque global" value={f.niveau_risque_global} onPick={set("niveau_risque_global")} options={[["faible", "Faible"], ["standard", "Standard"], ["eleve", "Élevé"]]} />
          <div className="form-actions"><button type="button" className="btn-submit" disabled={!!busy} onClick={enregistrer}>{busy === "save" ? <><i className="spin" />Enregistrement…</> : <>Enregistrer l'évaluation<FIcon n="arrow" size={17} /></>}</button></div>
        </div>
        <div className="app-card">
          <div className="card-h"><h3>Décision</h3></div>
          <Textarea label="Motivation de la décision" hint="Elle sera conservée dans le dossier et le journal d'audit" value={motif} onChange={(e) => setMotif(e.target.value)} />
          <div className="decide">
            <button type="button" className="btn-accept" disabled={!!busy} onClick={() => decider("acceptee")}>{busy === "acceptee" ? <i className="spin" /> : <FIcon n="check" size={18} />}Accepter la mission</button>
            <button type="button" className="btn-refuse" disabled={!!busy} onClick={() => decider("refusee")}>{busy === "refusee" ? <i className="spin dark" /> : <FIcon n="close" size={18} />}Refuser</button>
          </div>
          <small className="muted">Accepter fait passer la mission en phase de planification.</small>
        </div>
      </div>
      <FormAlert>{err}</FormAlert>
      <div className="app-card">
        <div className="card-h"><h3>Lettre de mission</h3>
          <button type="button" className="btn-mini" disabled={a.data.decision !== "acceptee" || !!busy} onClick={lettreGo}>{busy === "lettre" ? "Génération…" : lettre ? "Régénérer" : "Générer le brouillon"}</button></div>
        {lettre ? <div className="paper"><div className="paper-ref">{lettre.reference} · {lettre.statut}</div><pre>{lettre.corps}</pre><small className="muted">Pour le document Word ou PDF, ouvrez l'onglet « Rapports ».</small></div>
          : <div className="empty-tab"><p>{a.data.decision === "acceptee" ? "Générez un brouillon de lettre à partir des données de la mission." : "La lettre de mission est disponible une fois la mission acceptée."}</p></div>}
      </div>
      {toast}
    </>
  );
}
