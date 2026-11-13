import { createContext, useCallback, useContext, useMemo, useState } from "react";

// Interface bilingue FR / EN. Les textes sont rangés par clé ; une clé absente en anglais retombe sur le français.
// Étendre : ajouter la clé dans les deux dictionnaires, puis utiliser t("ma.cle") via useI18n().
export const DICT = {
  fr: {
    "nav.dashboard": "Tableau de bord", "nav.clients": "Clients", "nav.missions": "Missions", "nav.subscription": "Abonnement",
    "nav.assistant": "Assistant IA", "nav.cabinet": "Modules du cabinet", "nav.inMission": "Dans une mission",
    "nav.inMissionHint": "Cycles, FEC, rapprochement, TVA, DSN, CSRD, fusion…", "nav.inMissionTab": "onglet « Modules »",
    "nav.logout": "Se déconnecter", "lang.switch": "English",
    "mod.intro": "Ces modules s'ouvrent dans l'espace de travail AXIOME de la mission « {mission} ». Utilisez « Tableau de bord » pour revenir à votre espace.",
    "mod.open": "Ouvrir →",
    "mod.bg.title": "Dossier Excel complet", "mod.bg.desc": "Génère le classeur de tous les cycles en arrière-plan : vous pouvez continuer à travailler.",
    "mod.bg.start": "Générer en arrière-plan", "mod.bg.running": "Génération en cours…", "mod.bg.done": "Dossier prêt", "mod.bg.download": "Télécharger",
    "mod.bg.fail": "La génération a échoué",
    "ia.title": "Assistant IA", "ia.subtitle": "Aide à la rédaction et à la synthèse (notes, revues, conclusions). Vous validez toujours le résultat.",
    "ia.context": "Contexte (facultatif)", "ia.contextPh": "Ex. : mission, cycle, constats déjà relevés…",
    "ia.prompt": "Votre demande", "ia.promptPh": "Ex. : Rédige une note de synthèse sur les écarts du cycle Clients.",
    "ia.send": "Envoyer", "ia.sending": "Rédaction…", "ia.reply": "Proposition",
    "ia.off": "L'assistant IA n'est pas encore activé sur ce serveur : la clé API (ANTHROPIC_API_KEY) n'est pas configurée. Contactez l'administrateur.",
    "ia.warn": "Proposition de l'IA — à valider par le professionnel.", "ia.checking": "Vérification de l'assistant…",
  },
  en: {
    "nav.dashboard": "Dashboard", "nav.clients": "Clients", "nav.missions": "Engagements", "nav.subscription": "Subscription",
    "nav.assistant": "AI assistant", "nav.cabinet": "Firm modules", "nav.inMission": "Inside an engagement",
    "nav.inMissionHint": "Cycles, FEC, bank reconciliation, VAT, payroll, CSRD, merger…", "nav.inMissionTab": "“Modules” tab",
    "nav.logout": "Sign out", "lang.switch": "Français",
    "mod.intro": "These modules open in the AXIOME workspace of the engagement “{mission}”. Use “Dashboard” to go back to your space.",
    "mod.open": "Open →",
    "mod.bg.title": "Full Excel file", "mod.bg.desc": "Builds the workbook for every cycle in the background: you can keep working meanwhile.",
    "mod.bg.start": "Generate in background", "mod.bg.running": "Generating…", "mod.bg.done": "File ready", "mod.bg.download": "Download",
    "mod.bg.fail": "Generation failed",
    "ia.title": "AI assistant", "ia.subtitle": "Help with drafting and summarising (notes, reviews, conclusions). You always validate the output.",
    "ia.context": "Context (optional)", "ia.contextPh": "E.g. engagement, cycle, findings so far…",
    "ia.prompt": "Your request", "ia.promptPh": "E.g. Draft a summary note on the Trade receivables cycle variances.",
    "ia.send": "Send", "ia.sending": "Drafting…", "ia.reply": "Suggestion",
    "ia.off": "The AI assistant is not enabled on this server yet: the API key (ANTHROPIC_API_KEY) is not configured. Please contact your administrator.",
    "ia.warn": "AI suggestion — to be validated by the professional.", "ia.checking": "Checking the assistant…",
  },
};

export const LANGS = ["fr", "en"];
const KEY = "axiome_lang";

export function translate(lang, key, vars = {}) {
  const raw = (DICT[lang] && DICT[lang][key]) ?? DICT.fr[key] ?? key;
  return raw.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`));
}

/** Choix de l'élément selon la langue dans un objet { fr, en } (repli sur le français). */
export const pick = (obj, lang) => (obj && (obj[lang] ?? obj.fr));

const load = () => { try { const l = localStorage.getItem(KEY); return LANGS.includes(l) ? l : "fr"; } catch { return "fr"; } };

const Ctx = createContext({ lang: "fr", setLang: () => {}, t: (k, v) => translate("fr", k, v) });
export const useI18n = () => useContext(Ctx);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(load);
  const setLang = useCallback((l) => {
    if (!LANGS.includes(l)) return;
    setLangState(l);
    try { localStorage.setItem(KEY, l); } catch { /* stockage indisponible */ }
    try { document.documentElement.lang = l; } catch { /* hors navigateur */ }
    // Aligne la langue des écrans rendus par le back (préférence enregistrée sur le compte).
    try { fetch(`/vue/langue/${l}`, { redirect: "manual", credentials: "same-origin" }).catch(() => {}); } catch { /* sans effet */ }
  }, []);
  const value = useMemo(() => ({ lang, setLang, t: (k, v) => translate(lang, k, v) }), [lang, setLang]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
