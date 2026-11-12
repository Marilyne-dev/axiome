import { useState } from "react";
import useAsync from "../../../components/app/useAsync.js";
import { ajouterBudget, ajouterEquipe, ajouterJalon, getCollaborateurs, getPlanification, majPlanification } from "../../../api.js";
import { ErrorBox, Loading } from "../../../components/app/ui.jsx";
import { FIcon, FormAlert, Input, Textarea, useToast } from "../../../components/app/FormKit.jsx";
import QuickAdd from "./QuickAdd.jsx";

const nb = (v, d = 0) => (v == null ? "—" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d }).format(v));
const date = (d) => (d ? new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(d)) : "Sans échéance");
const STATUTS = { a_faire: ["À faire", "none"], en_cours: ["En cours", "warn"], fait: ["Terminé", "ok"] };
const ROLES = [["associe", "Associé signataire"], ["manager", "Manager"], ["collaborateur", "Collaborateur"], ["stagiaire", "Stagiaire"]];

const Stat = ({ icon, label, value, tone, i = 0 }) => (
  <div className={`kpi kx k-${tone}`} style={{ "--i": i }}><div className="kx-glow" /><div className="kpi-ico"><FIcon n={icon} size={22} /></div><div><div className="kpi-v sm">{value}</div><div className="kpi-l">{label}</div></div></div>
);

function Cadrage({ plan, m, onSaved }) {
  const [f, setF] = useState({ date_debut: plan.date_debut || "", date_fin: plan.date_fin || "", honoraires: plan.honoraires ?? 0, devise: plan.devise || m.devise, approche: plan.approche || "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await majPlanification(m.id, { ...f, date_debut: f.date_debut || null, date_fin: f.date_fin || null, honoraires: Number(f.honoraires) || 0, devise: (f.devise || "EUR").toUpperCase() }); onSaved(); } catch (e2) { setErr(e2.message); }
    setBusy(false);
  };
  return (
    <form className="app-card" onSubmit={go}>
      <div className="card-h"><h3>Cadrage de la mission</h3><span className="chip">Planification</span></div>
      <div className="fgrid four">
        <Input type="date" icon="calendar" label="Début" value={f.date_debut} onChange={set("date_debut")} />
        <Input type="date" icon="calendar" label="Fin" value={f.date_fin} onChange={set("date_fin")} />
        <Input type="number" step="any" min="0" icon="coin" label="Honoraires" value={f.honoraires} onChange={set("honoraires")} />
        <Input maxLength={3} icon="coin" label="Devise" value={f.devise} onChange={(e) => setF({ ...f, devise: e.target.value.toUpperCase() })} />
        <Textarea full label="Approche d'audit" hint="Stratégie, zones de focus, contraintes particulières" value={f.approche} onChange={set("approche")} />
      </div>
      <FormAlert>{err}</FormAlert>
      <div className="form-actions"><button className="btn-submit" disabled={busy}>{busy ? <><i className="spin" />Enregistrement…</> : <>Enregistrer le cadrage<FIcon n="arrow" size={17} /></>}</button></div>
    </form>
  );
}

const Liste = ({ titre, icone, onAdd, vide, children }) => (
  <div className="app-card">
    <div className="card-h"><h3>{titre}</h3><button type="button" className="btn-mini" onClick={onAdd}><FIcon n="plus" size={14} />Ajouter</button></div>
    {children && (Array.isArray(children) ? children.length : true) ? children : <div className="empty-tab"><p>{vide}</p></div>}
  </div>
);

export default function Planification({ m }) {
  const p = useAsync(() => getPlanification(m.id), [m.id]);
  const c = useAsync(getCollaborateurs);
  const [dlg, setDlg] = useState(null);
  const [toast, show] = useToast();
  const fini = (msg) => { setDlg(null); p.reload(); show(msg); };
  const noms = Object.fromEntries((c.data || []).map((u) => [u.id, u.nom]));
  const d = p.data;
  return (
    <>
      <div className="tab-head"><div><h3>Planification</h3><p className="muted">Calendrier, équipe et budget de la mission.</p></div></div>
      {p.loading && !d && <Loading />}
      {p.error && <ErrorBox message={p.error} onRetry={p.reload} />}
      {d && (<>
        <div className="kpis">
          <Stat i={0} icon="coin" tone="blue" label="Honoraires" value={`${nb(d.honoraires)} ${d.devise}`} />
          <Stat i={1} icon="file" tone="violet" label="Budget prévu" value={`${nb(d.total_budget)} ${d.devise}`} />
          <Stat i={2} icon="clock" tone="green" label="Heures estimées" value={`${nb(d.total_heures, 1)} h`} />
          <Stat i={3} icon="calendar" tone="red" label="Période" value={d.date_debut && d.date_fin ? `${date(d.date_debut)} → ${date(d.date_fin)}` : "À définir"} />
        </div>
        <Cadrage key={d.id + String(d.honoraires) + (d.date_debut || "")} plan={d} m={m} onSaved={() => { p.reload(); show("Cadrage enregistré"); }} />
        <div className="grid-2 gx">
          <Liste titre="Jalons" onAdd={() => setDlg("jalon")} vide="Aucun jalon défini. Ajoutez les étapes clés de la mission.">
            {d.jalons.length ? <ul className="timeline">{d.jalons.map((j) => { const [l, cl] = STATUTS[j.statut] || [j.statut, "none"]; return <li key={j.id} className={`tl-${cl}`}><i /><div><b>{j.libelle}</b><small>{date(j.echeance)}</small></div><span className={`badge b-${cl}`}>{l}</span></li>; })}</ul> : null}
          </Liste>
          <Liste titre="Équipe" onAdd={() => setDlg("equipe")} vide="Aucun collaborateur affecté à cette mission.">
            {d.equipe.length ? <ul className="people">{d.equipe.map((a) => { const n = noms[a.user_id] || `Collaborateur #${a.user_id}`; return <li key={a.id}><span className="avatar sm">{n.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}</span><div><b>{n}</b><small>{(ROLES.find(([v]) => v === a.role_mission) || [, a.role_mission])[1]}</small></div><em>{nb(a.heures_estimees, 1)} h</em></li>; })}</ul> : null}
          </Liste>
        </div>
        <Liste titre="Budget" onAdd={() => setDlg("budget")} vide="Aucune ligne de budget. Ajoutez les postes de dépense prévus.">
          {d.budget.length ? <div className="table-scroll"><table className="app-table"><thead><tr><th>Poste</th><th className="r">Montant</th></tr></thead>
            <tbody>{d.budget.map((b) => <tr key={b.id}><td><b>{b.poste}</b></td><td className="r">{nb(b.montant)} {b.devise}</td></tr>)}
              <tr className="tot"><td>Total</td><td className="r">{nb(d.total_budget)} {d.devise}</td></tr></tbody></table></div> : null}
        </Liste>
      </>)}
      <QuickAdd open={dlg === "jalon"} onClose={() => setDlg(null)} tone="blue" icon="flag" formId="form-jalon" title="Nouveau jalon" subtitle="Une étape clé avec son échéance." submitLabel="Ajouter le jalon"
        initial={{ libelle: "", echeance: "", statut: "a_faire" }}
        fields={[{ k: "libelle", label: "Libellé du jalon", icon: "flag", required: true }, { k: "echeance", label: "Échéance", type: "date", icon: "calendar", half: true },
          { k: "statut", label: "Statut", type: "select", icon: "tag", half: true, options: [["a_faire", "À faire"], ["en_cours", "En cours"], ["fait", "Terminé"]] }]}
        onSubmit={(f) => ajouterJalon(m.id, { libelle: f.libelle, echeance: f.echeance || null, statut: f.statut })} onDone={() => fini("Jalon ajouté")} />
      <QuickAdd open={dlg === "equipe"} onClose={() => setDlg(null)} tone="violet" icon="users" formId="form-equipe" title="Affecter un collaborateur" subtitle="Choisissez un membre du cabinet et son rôle sur la mission." submitLabel="Affecter"
        initial={{ user_id: "", role_mission: "collaborateur", heures_estimees: "" }}
        fields={[{ k: "user_id", label: "Collaborateur", type: "select", icon: "user", required: true, options: (c.data || []).map((u) => [u.id, u.nom]) },
          { k: "role_mission", label: "Rôle sur la mission", type: "select", icon: "briefcase", half: true, options: ROLES },
          { k: "heures_estimees", label: "Heures estimées", type: "number", min: "0", icon: "clock", half: true }]}
        onSubmit={(f) => ajouterEquipe(m.id, { user_id: Number(f.user_id), role_mission: f.role_mission, heures_estimees: Number(f.heures_estimees) || 0 })} onDone={() => fini("Collaborateur affecté")} />
      <QuickAdd open={dlg === "budget"} onClose={() => setDlg(null)} tone="blue" icon="coin" formId="form-budget" title="Ligne de budget" subtitle="Un poste de dépense prévisionnel." submitLabel="Ajouter la ligne"
        initial={{ poste: "", montant: "", devise: d?.devise || m.devise }}
        fields={[{ k: "poste", label: "Poste", icon: "tag", required: true }, { k: "montant", label: "Montant", type: "number", min: "0", icon: "coin", half: true, required: true },
          { k: "devise", label: "Devise", icon: "coin", half: true }]}
        onSubmit={(f) => ajouterBudget(m.id, { poste: f.poste, montant: Number(f.montant) || 0, devise: (f.devise || "EUR").toUpperCase() })} onDone={() => fini("Ligne de budget ajoutée")} />
      {toast}
    </>
  );
}
