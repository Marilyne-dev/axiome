import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import useAsync from "../../components/app/useAsync.js";
import { creerMission, getClients, getMissions, getOptionsMission } from "../../api.js";
import { ErrorBox, Loading, Verrou, MissionsTable } from "../../components/app/ui.jsx";
import { Chips, Drawer, FIcon, FormAlert, Input, Section, Select, SubmitBtn } from "../../components/app/FormKit.jsx";

function NouvelleMission({ open, onClose }) {
  const nav = useNavigate();
  const clients = useAsync(() => getClients(""));
  const opts = useAsync(getOptionsMission);
  const [f, setF] = useState({ client_id: "", intitule: "", exercice: String(new Date().getFullYear()), type_mission: "CERT_ANNUELS", referentiel: "PCG_FR", devise: "EUR" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async (e) => { e.preventDefault(); setBusy(true); setErr("");
    try { const r = await creerMission({ ...f, client_id: Number(f.client_id) }); nav(`/espace/missions/${r.id}`); } catch (e2) { setErr(e2.message); setBusy(false); } };
  const aucunClient = clients.data && !clients.data.length;
  return (
    <Drawer open={open} onClose={onClose} tone="violet" size="lg" icon="briefcase" title="Nouvelle mission" subtitle="Ouvrez un dossier d'audit : le programme de diligences est généré automatiquement."
      footer={<><button type="button" className="btn-cancel" onClick={onClose}>Annuler</button>
        {!aucunClient && <SubmitBtn form="form-mission" busy={busy} busyText="Création…">Créer la mission</SubmitBtn>}</>}>
      {aucunClient ? (
        <div className="drawer-empty"><div className="empty-ico"><FIcon n="building" size={30} /></div>
          <h3>Un client d'abord</h3><p>Pour ouvrir une mission, il faut d'abord <Link to="/espace/clients" onClick={onClose}>créer un client</Link>.</p></div>
      ) : (
        <form id="form-mission" className="elegant" onSubmit={go}>
          <Section icon="user" title="Dossier" sub="Pour qui, et sous quel intitulé">
            <Select full required icon="building" label="Client" value={f.client_id} onChange={set("client_id")}>
              <option value="" disabled hidden></option>
              {clients.data?.map((c) => <option key={c.id} value={c.id}>{c.raison_sociale}</option>)}</Select>
            <Input full required minLength={2} icon="file" label="Intitulé de la mission" hint="Ex. Certification des comptes 2026" value={f.intitule} onChange={set("intitule")} />
          </Section>
          <Section icon="scale" title="Cadre normatif" sub="Nature de la mission et référentiel comptable">
            <Select full icon="briefcase" label="Type de mission" value={f.type_mission} onChange={set("type_mission")}>
              {opts.data?.types.map((g) => <optgroup key={g.categorie} label={g.categorie}>{g.types.map((t) => <option key={t.code} value={t.code}>{t.libelle}</option>)}</optgroup>)}</Select>
            <Select full icon="scale" label="Référentiel" value={f.referentiel} onChange={set("referentiel")}>
              {opts.data?.referentiels.map((r) => <option key={r.code} value={r.code}>{r.libelle}</option>)}</Select>
          </Section>
          <Section className="span2 per" icon="calendar" title="Période et monnaie" sub="Exercice audité et devise de présentation">
            <Input icon="calendar" maxLength={9} label="Exercice" value={f.exercice} onChange={set("exercice")} />
            <Input icon="coin" maxLength={3} label="Devise (ISO 4217)" value={f.devise} onChange={(e) => setF({ ...f, devise: e.target.value.toUpperCase() })} />
            <div className="chips-cell"><Chips value={f.devise} options={["EUR", "XOF", "XAF", "USD", "MAD"]} onPick={(d) => setF({ ...f, devise: d })} /></div>
          </Section>
          <FormAlert>{err}</FormAlert>
          <button className="hidden-submit" tabIndex={-1} aria-hidden="true" />
        </form>
      )}
    </Drawer>
  );
}

export default function Missions() {
  const [nouvelle, setNouvelle] = useState(false);
  const { data, error, status, loading, reload } = useAsync(getMissions);
  return (
    <>
      <div className="page-head"><div><p className="eyebrow">Audit</p><h1>Missions</h1></div>
        <button className="btn btn-primary" onClick={() => setNouvelle(true)}>+ Nouvelle mission</button></div>
      <NouvelleMission open={nouvelle} onClose={() => setNouvelle(false)} />
      {status === 402 && <Verrou />}
      {error && status !== 402 && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && <div className="app-card">{data.length ? <MissionsTable rows={data} /> : <p className="muted pad">Aucune mission pour le moment.</p>}</div>}
    </>
  );
}
