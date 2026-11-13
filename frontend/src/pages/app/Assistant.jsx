import { useEffect, useRef, useState } from "react";
import useAsync from "../../components/app/useAsync.js";
import { creerConversation, envoyerMessageIa, getConversation, getConversations, getIaStatut, supprimerConversation } from "../../api.js";
import { useI18n } from "../../i18n.jsx";
import "./assistant.css";

const TXT = {
  fr: {
    history: "Conversations", nouvelle: "Nouvelle conversation", del: "Supprimer", confirm: "Supprimer cette conversation ?",
    empty: "Posez votre première question. Vos échanges sont enregistrés et vous pouvez les reprendre plus tard.",
    you: "Vous", ai: "Assistant", ph: "Écrivez votre message…", ctx: "Ajouter un contexte (facultatif)",
    ctxPh: "Ex. : mission, cycle, constats déjà relevés. Envoyé avec chaque message.",
    send: "Envoyer", thinking: "Rédaction…", warn: "Réponses de l'IA : à valider par le professionnel.",
  },
  en: {
    history: "Conversations", nouvelle: "New conversation", del: "Delete", confirm: "Delete this conversation?",
    empty: "Ask your first question. Your exchanges are saved and you can pick them up later.",
    you: "You", ai: "Assistant", ph: "Write your message…", ctx: "Add context (optional)",
    ctxPh: "E.g. engagement, cycle, findings so far. Sent with every message.",
    send: "Send", thinking: "Drafting…", warn: "AI answers: to be validated by the professional.",
  },
};

// Assistant IA : fil de conversation continu, enregistré côté serveur (liste de conversations par utilisateur).
export default function Assistant() {
  const { t, lang } = useI18n();
  const L = TXT[lang] || TXT.fr;
  const statut = useAsync(() => getIaStatut(), []);
  const [convs, setConvs] = useState([]);
  const [cid, setCid] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [texte, setTexte] = useState("");
  const [ctx, setCtx] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const fil = useRef(null);
  const dispo = statut.data && statut.data.disponible;

  const rafraichir = async () => { try { setConvs(await getConversations()); } catch { /* liste facultative */ } };
  const ouvrir = async (id) => {
    setErr(""); setCid(id);
    try { const c = await getConversation(id); setMsgs(c.messages || []); } catch (e) { setErr(e.message); }
  };
  const nouvelle = () => { setCid(null); setMsgs([]); setErr(""); };

  useEffect(() => {
    (async () => {
      try { const l = await getConversations(); setConvs(l); if (l.length) ouvrir(l[0].id); } catch { /* ignoré */ }
    })();
  }, []); // eslint-disable-line
  useEffect(() => { if (fil.current) fil.current.scrollTop = fil.current.scrollHeight; }, [msgs, busy]);

  const envoyer = async () => {
    const contenu = texte.trim();
    if (!contenu || busy) return;
    setBusy(true); setErr("");
    let id = cid; let cree = false;
    const tmp = { id: `tmp-${Date.now()}`, role: "user", contenu };
    try {
      if (!id) { const c = await creerConversation(); id = c.id; cree = true; setCid(id); }
      setMsgs((m) => [...m, tmp]); setTexte("");
      const r = await envoyerMessageIa(id, contenu, ctx);
      setMsgs((m) => [...m.filter((x) => x.id !== tmp.id), ...r.messages]);
      rafraichir();
    } catch (e) {
      setMsgs((m) => m.filter((x) => x.id !== tmp.id)); setTexte(contenu); setErr(e.message);
      if (cree) { supprimerConversation(id).catch(() => {}); setCid(null); }
    }
    setBusy(false);
  };

  const supprimer = async () => {
    if (!cid || !window.confirm(L.confirm)) return;
    try { await supprimerConversation(cid); nouvelle(); rafraichir(); } catch (e) { setErr(e.message); }
  };

  // Ordinateur : Entrée envoie, Maj+Entrée saute une ligne. Téléphone : Entrée saute une ligne, le bouton envoie.
  const touche = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !window.matchMedia("(pointer: coarse)").matches) { e.preventDefault(); envoyer(); }
  };

  return (
    <>
      <div className="page-head"><div><h1>{t("ia.title")}</h1><p className="muted">{t("ia.subtitle")}</p></div></div>
      {statut.loading && <p className="muted">{t("ia.checking")}</p>}
      {statut.data && !dispo && <div className="alert ko" role="alert">{t("ia.off")}</div>}
      {dispo && (
        <div className="app-card ia-chat">
          <div className="ia-bar">
            <select aria-label={L.history} value={cid == null ? "" : String(cid)} onChange={(e) => (e.target.value ? ouvrir(Number(e.target.value)) : nouvelle())}>
              <option value="">+ {L.nouvelle}</option>
              {convs.map((c) => <option key={c.id} value={String(c.id)}>{c.titre || L.nouvelle}</option>)}
            </select>
            <button type="button" className="btn" onClick={nouvelle}>{L.nouvelle}</button>
            {cid != null && <button type="button" className="btn" onClick={supprimer}>{L.del}</button>}
          </div>

          <div className="ia-thread" ref={fil} aria-live="polite">
            {msgs.length === 0 && !busy && <p className="muted">{L.empty}</p>}
            {msgs.map((m) => (
              <div key={m.id} className={`ia-msg ${m.role}`}>
                <small>{m.role === "user" ? L.you : L.ai}</small>
                <div className="ia-text">{m.contenu}</div>
              </div>
            ))}
            {busy && <div className="ia-msg assistant"><small>{L.ai}</small><div className="ia-text muted">{L.thinking}</div></div>}
          </div>

          {err && <div className="alert ko" role="alert">{err}</div>}

          <details className="ia-ctx">
            <summary>{L.ctx}</summary>
            <textarea rows={3} value={ctx} placeholder={L.ctxPh} aria-label={L.ctx} onChange={(e) => setCtx(e.target.value)} />
          </details>

          <div className="ia-compose">
            <textarea rows={2} value={texte} placeholder={L.ph} aria-label={L.ph} onChange={(e) => setTexte(e.target.value)} onKeyDown={touche} />
            <button type="button" className="btn btn-primary" disabled={busy || !texte.trim()} onClick={envoyer}>{busy ? L.thinking : L.send}</button>
          </div>
          <p className="muted ia-hint">{L.warn}</p>
        </div>
      )}
    </>
  );
}
