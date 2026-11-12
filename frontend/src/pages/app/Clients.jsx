import { useState } from "react";
import useAsync from "../../components/app/useAsync.js";
import { creerClient, getClients } from "../../api.js";
import { ErrorBox, Loading, Verrou } from "../../components/app/ui.jsx";
import { Drawer, FormAlert, Input, Section, SubmitBtn, useToast } from "../../components/app/FormKit.jsx";

const PAYS = ["France", "Martinique", "Guadeloupe", "Bénin", "Côte d'Ivoire", "Sénégal", "Togo", "Cameroun", "Mali", "Burkina Faso", "Niger", "Gabon", "Congo", "Belgique", "Suisse", "Luxembourg", "Maroc", "Tunisie"];

function NouveauClient({ open, onClose, onDone }) {
  const vide = { raison_sociale: "", identifiant_legal: "", pays: "France", secteur: "" };
  const [f, setF] = useState(vide);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await creerClient(f); setF(vide); setBusy(false); onDone(f.raison_sociale); } catch (e2) { setErr(e2.message); setBusy(false); }
  };
  return (
    <Drawer open={open} onClose={onClose} tone="blue" size="md" icon="building" title="Nouveau client" subtitle="Ajoutez l'entité à auditer. Vous pourrez ensuite lui ouvrir une mission."
      footer={<><button type="button" className="btn-cancel" onClick={onClose}>Annuler</button><SubmitBtn form="form-client" busy={busy} busyText="Création…">Créer le client</SubmitBtn></>}>
      <form id="form-client" className="elegant" onSubmit={go}>
        <Section className="span2" icon="building" title="Identité" sub="Ce qui figurera sur le dossier">
          <Input required minLength={2} icon="building" label="Raison sociale" value={f.raison_sociale} onChange={set("raison_sociale")} />
          <Input icon="hash" label="SIREN / identifiant légal" hint="Facultatif : IFU, RCCM, SIREN…" value={f.identifiant_legal} onChange={set("identifiant_legal")} />
        </Section>
        <Section className="span2" icon="globe" title="Contexte" sub="Pays d'exercice et activité">
          <Input icon="globe" list="pays-liste" label="Pays" value={f.pays} onChange={set("pays")} />
          <Input icon="tag" label="Secteur d'activité" value={f.secteur} onChange={set("secteur")} />
          <datalist id="pays-liste">{PAYS.map((p) => <option key={p} value={p} />)}</datalist>
        </Section>
        <FormAlert>{err}</FormAlert>
        <button className="hidden-submit" tabIndex={-1} aria-hidden="true" />
      </form>
    </Drawer>
  );
}

export default function Clients() {
  const [q, setQ] = useState(""); const [nouveau, setNouveau] = useState(false);
  const [toast, show] = useToast();
  const { data, error, status, loading, reload } = useAsync(() => getClients(q), [q]);
  return (
    <>
      <div className="page-head"><div><p className="eyebrow">Portefeuille</p><h1>Clients</h1></div>
        <div className="head-actions"><input className="search" placeholder="Rechercher un client…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn btn-primary" onClick={() => setNouveau(true)}>+ Nouveau client</button></div></div>
      <NouveauClient open={nouveau} onClose={() => setNouveau(false)} onDone={(nom) => { setNouveau(false); reload(); show(`Client « ${nom} » créé`); }} />
      {toast}
      {status === 402 && <Verrou />}
      {error && status !== 402 && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && (<div className="app-card">{data.length ? (
        <div className="table-scroll"><table className="app-table"><thead><tr><th>Raison sociale</th><th>Identifiant légal</th><th>Pays</th><th>Secteur</th><th>Missions</th></tr></thead>
          <tbody>{data.map((c) => <tr key={c.id}><td><b>{c.raison_sociale}</b></td><td className="mono">{c.identifiant_legal || "—"}</td><td>{c.pays}</td><td>{c.secteur || "—"}</td><td>{c.nb_missions}</td></tr>)}</tbody></table></div>
      ) : <p className="muted pad">{q ? "Aucun client ne correspond à cette recherche." : "Aucun client pour le moment. Créez votre premier client pour ouvrir une mission."}</p>}</div>)}
    </>
  );
}
