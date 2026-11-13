import { Fragment, useState } from "react";
import { Link, useParams } from "react-router-dom";
import useAsync from "../../components/app/useAsync.js";
import { basculerDiligence, calculerSeuils, getAnalyse, getBenford, getControles, getIndicateursFraude, getMission, getRevue, importerBalance } from "../../api.js";
import { ErrorBox, Loading, Progress, Verrou } from "../../components/app/ui.jsx";
import Risques from "./missionTabs/Risques.jsx";
import Planification from "./missionTabs/Planification.jsx";
import Acceptation from "./missionTabs/Acceptation.jsx";
import Rapports from "./missionTabs/Rapports.jsx";
import ImportFec from "./missionTabs/ImportFec.jsx";
import Circularisation from "./missionTabs/Circularisation.jsx";

const nb = (v, d = 0) => (v == null ? "—" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d }).format(v));
const PHASES = [["acceptation", "Acceptation"], ["planification", "Planification"], ["realisation", "Réalisation"], ["finalisation", "Finalisation"]];
const AGREGATS = [["capitaux_propres", "Capitaux propres"], ["dettes_financieres", "Dettes financières"], ["immobilisations", "Immobilisations"], ["stocks", "Stocks"], ["creances_clients", "Créances clients"], ["dettes_fournisseurs", "Dettes fournisseurs"], ["tresorerie_actif", "Trésorerie active"],
  ["fonds_de_roulement_net_global", "Fonds de roulement net global"], ["besoin_en_fonds_de_roulement", "Besoin en fonds de roulement"], ["tresorerie_nette", "Trésorerie nette"]];
const RATIOS = [["liquidite_generale", "Liquidité générale"], ["autonomie_financiere", "Autonomie financière"], ["taux_endettement", "Taux d'endettement"], ["couverture_immobilisations", "Couverture des immobilisations"], ["poids_bfr", "Poids du BFR"]];

const Sans = ({ children }) => <div className="empty-tab"><p>{children}</p></div>;

function Apercu({ m, reload }) {
  const faits = m.diligences.filter((d) => d.fait).length;
  const [busy, setBusy] = useState(0);
  const toggle = async (d) => { setBusy(d.id); try { await basculerDiligence(m.id, d.id); await reload(); } finally { setBusy(0); } };
  return (
    <div className="grid-2">
      <div className="app-card">
        <h3>Diligences — {m.type_libelle}</h3>
        <div className="prog-line"><Progress value={faits} max={m.diligences.length} /><span>{faits} / {m.diligences.length}</span></div>
        <ul className="checklist">{m.diligences.map((d) => (
          <li key={d.id}><label><input type="checkbox" checked={d.fait} disabled={busy === d.id} onChange={() => toggle(d)} /><span className={d.fait ? "done" : ""}>{d.libelle}</span></label></li>))}</ul>
      </div>
      <div className="app-card">
        <h3>Dossier</h3>
        <dl className="facts">
          <dt>Client</dt><dd>{m.client.raison_sociale}</dd><dt>Exercice</dt><dd>{m.exercice || "—"}</dd>
          <dt>Référentiel</dt><dd><span className="mono tag">{m.referentiel}</span></dd><dt>Pays · devise</dt><dd>{m.pays} · {m.devise}</dd>
          <dt>Base normative</dt><dd>{m.base_normative || "—"}</dd><dt>Livrable</dt><dd>{m.livrable || "—"}</dd>
          <dt>Balance importée</dt><dd>{m.balance.nb_lignes ? `${nb(m.balance.nb_lignes)} lignes` : "Pas encore"}</dd>
          <dt>Seuil de signification</dt><dd>{m.seuils ? `${nb(m.seuils.signification)} ${m.devise}` : "Non calculé"}</dd>
          <dt>Risques identifiés</dt><dd>{m.nb_risques}</dd>
        </dl>
      </div>
    </div>
  );
}

function Balance({ m, reload }) {
  const [file, setFile] = useState(null); const [res, setRes] = useState(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const ctl = useAsync(() => (m.balance.nb_lignes ? getControles(m.id) : Promise.resolve(null)), [m.balance.nb_lignes]);
  const go = async (e) => { e.preventDefault(); if (!file) return; setBusy(true); setErr(""); setRes(null);
    try { setRes(await importerBalance(m.id, file)); await reload(); ctl.reload(); } catch (e2) { setErr(e2.message); } setBusy(false); };
  return (
    <>
      <form className="app-card" onSubmit={go}>
        <h3>Importer la balance générale</h3>
        <p className="muted">Fichier Excel (.xlsx). Les colonnes (compte, libellé, solde N, solde N-1, mouvements) sont reconnues automatiquement. Réimporter remplace la balance précédente.</p>
        <div className="file-row"><input type="file" accept=".xlsx,.xlsm" onChange={(e) => setFile(e.target.files[0] || null)} />
          <button className="btn btn-primary" disabled={!file || busy}>{busy ? "Import…" : "Importer"}</button></div>
        {err && <div className="alert ko" style={{ marginTop: 12 }}>{err}</div>}
        {res && <div className="alert ok" style={{ marginTop: 12 }}>{nb(res.lignes_importees)} lignes importées.</div>}
      </form>
      {ctl.data && (
        <div className="app-card"><h3>Contrôles de cohérence</h3>
          {ctl.data.controles.map((c, i) => <div key={i} className="ctl"><span className={`badge b-${c.statut === "ok" ? "ok" : "ko"}`}>{c.statut === "ok" ? "OK" : "Anomalie"}</span><div><b>{c.libelle}</b><small>{c.detail}</small></div></div>)}
        </div>)}
    </>
  );
}

function Seuils({ m, reload }) {
  const [f, setF] = useState({ resultat_net: "", chiffre_affaires: "", capitaux_propres: "" });
  const [res, setRes] = useState(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async (e) => { e.preventDefault(); setBusy(true); setErr("");
    try { setRes(await calculerSeuils(m.id, { resultat_net: Number(f.resultat_net) || 0, chiffre_affaires: Number(f.chiffre_affaires) || 0, capitaux_propres: Number(f.capitaux_propres) || 0 })); await reload(); }
    catch (e2) { setErr(e2.message); } setBusy(false); };
  const s = res ? { signification: res.seuil_signification, planification: res.seuil_planification, remontee: res.seuil_remontee, base: res.base_retenue } : m.seuils;
  return (
    <div className="grid-2">
      <form className="app-card" onSubmit={go}>
        <h3>Calcul des seuils (NEP 320)</h3>
        <p className="muted">Saisissez les agrégats de référence en {m.devise}. Les taux par défaut sont paramétrables côté serveur.</p>
        <div className="form-grid one">
          <label className="field">Résultat net<input type="number" step="any" value={f.resultat_net} onChange={set("resultat_net")} /></label>
          <label className="field">Chiffre d'affaires<input type="number" step="any" value={f.chiffre_affaires} onChange={set("chiffre_affaires")} /></label>
          <label className="field">Capitaux propres<input type="number" step="any" value={f.capitaux_propres} onChange={set("capitaux_propres")} /></label>
        </div>
        {err && <div className="alert ko" style={{ margin: "12px 0" }}>{err}</div>}
        <button className="btn btn-primary" disabled={busy} style={{ marginTop: 14 }}>{busy ? "Calcul…" : "Calculer et enregistrer"}</button>
      </form>
      <div className="app-card"><h3>Résultat</h3>
        {s ? (<div className="seuils">
          <div className="kpi2"><span>Seuil de signification</span><b>{nb(s.signification)} {m.devise}</b></div>
          <div className="kpi2"><span>Seuil de planification</span><b>{nb(s.planification)} {m.devise}</b></div>
          <div className="kpi2"><span>Seuil de remontée</span><b>{nb(s.remontee)} {m.devise}</b></div>
          <small className="muted">Base retenue : {s.base || "—"}</small></div>) : <p className="muted">Aucun seuil calculé pour cette mission.</p>}
      </div>
    </div>
  );
}

function Analyse({ m }) {
  const a = useAsync(() => getAnalyse(m.id)); const r = useAsync(() => getRevue(m.id));
  if (!m.balance.nb_lignes) return <Sans>Importez d'abord la balance (onglet « Balance ») pour voir l'analyse financière.</Sans>;
  const sig = r.data?.lignes.filter((l) => l.significatif) || [];
  return (
    <>
      {a.error && <ErrorBox message={a.error} onRetry={a.reload} />}
      {a.data && (<div className="grid-2">
        <div className="app-card"><h3>Structure financière</h3><dl className="facts">{AGREGATS.map(([k, l]) => <Fragment key={k}><dt>{l}</dt><dd>{nb(a.data.agregats[k])} {m.devise}</dd></Fragment>)}</dl></div>
        <div className="app-card"><h3>Ratios</h3><dl className="facts">{RATIOS.map(([k, l]) => <Fragment key={k}><dt>{l}</dt><dd>{nb(a.data.ratios[k], 2)}</dd></Fragment>)}</dl>
          <small className="muted">Indicateurs d'aide à l'analyse, à recouper avec la liasse.</small></div></div>)}
      <div className="app-card"><h3>Revue analytique N / N-1</h3>
        {r.data && (<>
          <p className="muted">{m.seuils ? `Seuil de remontée appliqué : ${nb(r.data.seuil_applique)} ${m.devise} — ` : "Calculez les seuils pour signaler les écarts significatifs. "}{r.data.nb_significatifs} écart(s) significatif(s) sur {r.data.nb_comptes} comptes.</p>
          <div className="table-scroll"><table className="app-table"><thead><tr><th>Compte</th><th>Libellé</th><th className="r">N</th><th className="r">N-1</th><th className="r">Variation</th><th className="r">%</th></tr></thead>
            <tbody>{(sig.length ? sig : r.data.lignes.slice(0, 15)).map((l) => <tr key={l.compte} className={l.significatif ? "hot" : ""}><td className="mono">{l.compte}</td><td>{l.libelle}</td>
              <td className="r">{nb(l.solde_n)}</td><td className="r">{nb(l.solde_n1)}</td><td className="r">{nb(l.variation)}</td><td className="r">{l.variation_pct == null ? "—" : `${nb(l.variation_pct * 100, 1)} %`}</td></tr>)}</tbody></table></div>
          {!sig.length && <small className="muted">Aucun écart significatif : affichage des 15 premiers comptes.</small>}</>)}
      </div>
    </>
  );
}

function Fraude({ m }) {
  const b = useAsync(() => getBenford(m.id)); const ind = useAsync(() => getIndicateursFraude(m.id));
  if (!m.balance.nb_lignes) return <Sans>Importez d'abord la balance pour lancer les tests de détection.</Sans>;
  return (
    <>
      <div className="app-card"><h3>Loi de Benford — premier chiffre des soldes</h3>
        {b.error && <p className="alert ko">{b.error}</p>}
        {b.data && (b.data.exploitable ? (<>
          <div className="benford">{b.data.distribution.map((d) => (
            <div key={d.chiffre} className="bf-col"><div className="bf-bars"><i className="obs" style={{ height: `${d.observe * 190}px` }} title={`Observé ${nb(d.observe * 100, 1)} %`} /><i className="att" style={{ height: `${d.attendu * 190}px` }} title={`Attendu ${nb(d.attendu * 100, 1)} %`} /></div><b>{d.chiffre}</b></div>))}</div>
          <div className="bf-leg"><span><i className="obs" />Observé</span><span><i className="att" />Attendu (Benford)</span></div>
          <p>Conformité : <b>{b.data.conformite}</b> · MAD {b.data.mad} · χ² {b.data.khi2} (seuil 5 % : {b.data.khi2_critique_5pct}) sur {nb(b.data.n)} montants.
            {b.data.suspicion ? " L'écart justifie des investigations complémentaires." : ""}</p>
          {b.data.n < 100 && <p className="alert ko" style={{ background: "#FFF9E6", color: "#8A6300" }}>Échantillon réduit ({nb(b.data.n)} montants) : le test de Benford n'est fiable qu'à partir de plusieurs centaines de valeurs. Interprétez avec prudence.</p>}
        </>) : <p className="muted">{b.data.message}</p>)}
        <small className="muted">Ces signaux sont des pistes d'investigation, jamais un jugement d'audit.</small>
      </div>
      {ind.data?.n > 0 && (<div className="app-card"><h3>Indicateurs complémentaires</h3>
        <dl className="facts"><dt>Montants analysés</dt><dd>{nb(ind.data.n)}</dd><dt>Nombres ronds (≥ 1 000)</dt><dd>{nb(ind.data.nombres_ronds)} ({nb(ind.data.part_nombres_ronds * 100, 1)} %)</dd>
          <dt>Montants dupliqués</dt><dd>{nb(ind.data.nb_montants_dupliques)}</dd></dl></div>)}
    </>
  );
}

const ONGLETS = [["apercu", "Aperçu"], ["acceptation", "Acceptation"], ["planification", "Planification"], ["risques", "Risques"], ["balance", "Balance"], ["fec", "Import FEC"], ["seuils", "Seuils"], ["analyse", "Analyse"], ["fraude", "Fraude"], ["circularisation", "Circularisation"], ["rapports", "Rapports"]];

export default function MissionDetail() {
  const { id } = useParams(); const [tab, setTab] = useState("apercu");
  const { data: m, error, status, loading, reload } = useAsync(() => getMission(id), [id]);
  return (
    <>
      <div className="page-head"><div><p className="eyebrow"><Link to="/espace/missions">← Missions</Link></p><h1>{m ? m.intitule : "Mission"}</h1>
        {m && <p className="muted">{m.client.raison_sociale} · Exercice {m.exercice || "—"} · {m.type_libelle}</p>}</div></div>
      {status === 402 && <Verrou />}
      {error && status !== 402 && <ErrorBox message={error} onRetry={reload} />}
      {loading && !m && <Loading />}
      {m && (<>
        <div className="phases">{PHASES.map(([c, l], i) => <span key={c} className={`phase${m.statut === c ? " on" : ""}`}><em>{i + 1}</em>{l}</span>)}</div>
        <div className="tabs">{ONGLETS.map(([c, l]) => <button key={c} className={tab === c ? "on" : ""} onClick={() => setTab(c)}>{l}</button>)}</div>
        {tab === "apercu" && <Apercu m={m} reload={reload} />}
        {tab === "acceptation" && <Acceptation m={m} reload={reload} />}
        {tab === "planification" && <Planification m={m} />}
        {tab === "risques" && <Risques m={m} />}
        {tab === "balance" && <Balance m={m} reload={reload} />}
        {tab === "fec" && <ImportFec m={m} reload={reload} />}
        {tab === "seuils" && <Seuils m={m} reload={reload} />}
        {tab === "analyse" && <Analyse m={m} />}
        {tab === "fraude" && <Fraude m={m} />}
        {tab === "circularisation" && <Circularisation m={m} />}
        {tab === "rapports" && <Rapports m={m} />}
      </>)}
    </>
  );
}
