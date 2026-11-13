import { useState } from "react";
import useAsync from "../../components/app/useAsync.js";
import { assisterIa, getIaStatut } from "../../api.js";
import { useI18n } from "../../i18n.jsx";

// Assistant IA : l'écran interroge /ia/statut puis /ia/assister. La clé Anthropic reste côté serveur.
export default function Assistant() {
  const { t } = useI18n();
  const statut = useAsync(() => getIaStatut(), []);
  const [contexte, setContexte] = useState(""); const [prompt, setPrompt] = useState("");
  const [res, setRes] = useState(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  const envoyer = async (e) => {
    e.preventDefault(); if (!prompt.trim()) return;
    setBusy(true); setErr(""); setRes(null);
    try { setRes(await assisterIa(prompt, contexte)); } catch (x) { setErr(x.message); }
    setBusy(false);
  };
  const dispo = statut.data && statut.data.disponible;

  return (
    <>
      <div className="page-head"><div><h1>{t("ia.title")}</h1><p className="muted">{t("ia.subtitle")}</p></div></div>
      {statut.loading && <p className="muted">{t("ia.checking")}</p>}
      {statut.data && !dispo && <div className="alert ko" role="alert">{t("ia.off")}</div>}
      {dispo && (
        <form className="app-card" onSubmit={envoyer}>
          <label htmlFor="ia-ctx">{t("ia.context")}</label>
          <textarea id="ia-ctx" rows={3} value={contexte} placeholder={t("ia.contextPh")} onChange={(e) => setContexte(e.target.value)} />
          <label htmlFor="ia-prompt" style={{ marginTop: 12 }}>{t("ia.prompt")}</label>
          <textarea id="ia-prompt" rows={5} required value={prompt} placeholder={t("ia.promptPh")} onChange={(e) => setPrompt(e.target.value)} />
          <div style={{ marginTop: 12 }}><button className="btn btn-primary" disabled={busy || !prompt.trim()}>{busy ? t("ia.sending") : t("ia.send")}</button></div>
        </form>
      )}
      {err && <div className="alert ko" style={{ marginTop: 12 }}>{err}</div>}
      {res && (res.erreur
        ? <div className="alert ko" style={{ marginTop: 12 }}>{res.erreur}</div>
        : <div className="app-card" style={{ marginTop: 16 }}>
            <h3>{t("ia.reply")}</h3>
            <div style={{ whiteSpace: "pre-wrap" }}>{res.reponse}</div>
            <p className="muted" style={{ marginTop: 12 }}>{res.avertissement || t("ia.warn")}</p>
          </div>)}
    </>
  );
}
