import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { importerFec } from "../../../api.js";
import { FIcon, FormAlert } from "../../../components/app/FormKit.jsx";
import "../../../audit.css";

const nb = (v, d = 0) => (v == null ? "—" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d }).format(v));
const taille = (o) => (o < 1048576 ? `${Math.max(1, Math.round(o / 1024))} Ko` : `${(o / 1048576).toFixed(1).replace(".", ",")} Mo`);

/* Import du FEC (DGFiP) : le grand livre est agrégé en balance et remplace celle de la mission. */
export default function ImportFec({ m, reload }) {
  const [file, setFile] = useState(null); const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [ask, setAsk] = useState(false); const [res, setRes] = useState(null);
  const input = useRef(null);
  const existante = m.balance?.nb_lignes || 0;

  const choisir = (f) => { setFile(f || null); setErr(""); setAsk(false); setRes(null); };
  const deposer = (e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) choisir(f); };
  const lancer = async (confirmer = false) => {
    if (!file) return;
    setBusy(true); setErr("");
    try {
      const r = await importerFec(m.id, file, confirmer);
      setRes(r); setAsk(false); setFile(null); if (input.current) input.current.value = "";
      await reload?.();
    } catch (e) {
      if (e.status === 409) setAsk(true); else setErr(e.message);
    }
    setBusy(false);
  };

  return (
    <>
      <div className="tab-head"><div><h3>Import du FEC</h3>
        <p className="muted">Le fichier des écritures comptables est agrégé en balance générale et remplace la balance de la mission.</p></div></div>
      <div className="grid-2 gx">
        <div className="app-card">
          <label className={`dz${drag ? " on" : ""}${file ? " has" : ""}`} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={deposer}>
            <input ref={input} type="file" accept=".txt,.csv,.fec" onChange={(e) => choisir(e.target.files?.[0])} />
            <span className="dz-ico"><FIcon n={file ? "file" : "download"} size={26} /></span>
            {file ? (<><b>{file.name}</b><small>{taille(file.size)} · prêt à être importé</small></>)
              : (<><b>Déposez votre FEC ici</b><small>ou cliquez pour choisir un fichier (.txt, .csv, .fec)</small></>)}
          </label>

          {ask && (
            <div className="fec-confirm" role="alertdialog">
              <FIcon n="warn" size={20} />
              <div><b>Une balance existe déjà ({nb(existante)} lignes).</b>
                <p>L'import la remplace entièrement par le contenu de ce FEC. Cette action ne peut pas être annulée.</p></div>
              <div className="fc-btns">
                <button type="button" className="btn-cancel" onClick={() => setAsk(false)}>Annuler</button>
                <button type="button" className="btn btn-primary" disabled={busy} onClick={() => lancer(true)}>{busy ? "Import…" : "Remplacer la balance"}</button>
              </div>
            </div>)}

          <FormAlert>{err}</FormAlert>
          {!ask && <div className="form-actions"><button type="button" className="btn btn-primary" disabled={!file || busy} onClick={() => lancer(false)}>{busy ? "Import en cours…" : "Importer le FEC"}</button></div>}
        </div>

        <div className="app-card">
          <h3>Avant d'importer</h3>
          <ul className="fec-tips">
            <li><FIcon n="check" size={16} />Fichier FEC tabulé ou séparé par « | » ou « ; », avec les colonnes <span className="mono">CompteNum</span>, <span className="mono">Debit</span> et <span className="mono">Credit</span>.</li>
            <li><FIcon n="check" size={16} />Les écritures sont cumulées par compte, puis classées selon le plan comptable.</li>
            <li><FIcon n="warn" size={16} />Un FEC ne couvre qu'un exercice : les soldes N-1 restent à zéro (importez la balance Excel pour la revue N / N-1).</li>
            <li><FIcon n="clock" size={16} />Taille maximale : 25 Mo.</li>
          </ul>
          <p className="fec-state"><span className={`badge b-${existante ? "ok" : "none"}`}>{existante ? `${nb(existante)} lignes en base` : "Aucune balance"}</span>
            <small className="muted">pour « {m.intitule} »</small></p>
        </div>
      </div>

      {res && (
        <div className="app-card fec-res">
          <div className="card-h"><h3>Import terminé</h3>
            <span className={`badge b-${res.equilibre ? "ok" : "ko"}`}>{res.equilibre ? "Écritures équilibrées" : "Écart débit / crédit"}</span></div>
          <div className="fec-kpis">
            <div><span>Comptes</span><b>{nb(res.nb_comptes)}</b></div>
            <div><span>Écritures</span><b>{nb(res.nb_ecritures)}</b></div>
            <div><span>Total débit</span><b>{nb(res.total_debit, 2)}</b></div>
            <div><span>Total crédit</span><b>{nb(res.total_credit, 2)}</b></div>
            <div><span>Résultat net</span><b>{nb(res.resultat_net)}</b></div>
            <div><span>Chiffre d'affaires</span><b>{nb(res.chiffre_affaires)}</b></div>
            <div><span>Capitaux propres</span><b>{nb(res.capitaux_propres)}</b></div>
          </div>
          {!res.equilibre && <p className="alert ko" style={{ marginTop: 14 }}>Le total des débits ne correspond pas au total des crédits : le FEC est peut-être incomplet. Vérifiez le fichier avant de poursuivre.</p>}
          <p className="muted" style={{ marginTop: 14 }}>La balance est à jour. Vous pouvez reporter ces agrégats dans le calcul des seuils, puis lancer l'analyse financière
            depuis <Link className="row-link" to={`/espace/missions/${m.id}`}>le dossier de la mission</Link>.</p>
        </div>)}
    </>
  );
}
