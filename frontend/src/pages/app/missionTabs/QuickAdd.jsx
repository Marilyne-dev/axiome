import { useState } from "react";
import { Drawer, FormAlert, Input, Section, Segmented, Select, SubmitBtn } from "../../../components/app/FormKit.jsx";

/* Panneau d'ajout générique : fields = [{ k, label, type, icon, options, required, half, hint }]. */
export default function QuickAdd({ open, onClose, title, subtitle, icon, tone = "blue", fields, initial = {}, formId, submitLabel, onSubmit, onDone, preview }) {
  const [f, setF] = useState(initial);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await onSubmit(f); setF(initial); setBusy(false); onDone(f); } catch (e2) { setErr(e2.message); setBusy(false); }
  };
  return (
    <Drawer open={open} onClose={onClose} tone={tone} size="md" icon={icon} title={title} subtitle={subtitle}
      footer={<><button type="button" className="btn-cancel" onClick={onClose}>Annuler</button><SubmitBtn form={formId} busy={busy} busyText="Enregistrement…">{submitLabel || "Enregistrer"}</SubmitBtn></>}>
      <form id={formId} className="elegant" onSubmit={go}>
        <Section className="span2" icon={icon} title="Détails" sub="Renseignez les informations ci-dessous">
          {fields.map((d) => {
            const common = { label: d.label, icon: d.icon, hint: d.hint, required: d.required, full: !d.half };
            if (d.type === "select") return <Select key={d.k} {...common} value={f[d.k] ?? ""} onChange={(e) => set(d.k, e.target.value)}>
              <option value="" disabled hidden></option>{d.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>;
            if (d.type === "seg") return <div key={d.k} className="full"><Segmented label={d.label} value={f[d.k]} options={d.options} onPick={(v) => set(d.k, v)} /></div>;
            return <Input key={d.k} {...common} type={d.type || "text"} step={d.type === "number" ? "any" : undefined} min={d.min} value={f[d.k] ?? ""} onChange={(e) => set(d.k, e.target.value)} />;
          })}
          {preview && <div className="full">{preview(f)}</div>}
        </Section>
        <FormAlert>{err}</FormAlert>
        <button className="hidden-submit" tabIndex={-1} aria-hidden="true" />
      </form>
    </Drawer>
  );
}
