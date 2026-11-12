// Client API : toutes les requêtes passent par /api (proxy Vite -> FastAPI, préfixe retiré).
let session = { access: null, refresh: null, onChange: () => {}, onExpired: () => {} };
export const setSession = (s) => { session = { ...session, ...s }; };

async function raw(path, { method = "GET", body, token, blob } = {}) {
  const headers = {};
  const form = typeof FormData !== "undefined" && body instanceof FormData;
  if (!form) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body ? (form ? body : JSON.stringify(body)) : undefined });
  } catch {
    throw new Error("Serveur injoignable. Vérifiez que le back-end est démarré.");
  }
  if (blob && res.ok) {   // téléchargement de fichier (rapports Word / PDF)
    const m = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") || "");
    return { blob: await res.blob(), nom: m ? m[1] : "document" };
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    if (res.status === 405 || (res.status === 404 && (!d || d === "Not Found"))) throw Object.assign(new Error("Cette fonction n'est pas encore disponible."), { status: res.status });
    throw Object.assign(new Error(typeof d === "string" ? d : "Requête invalide. Vérifiez les champs."), { status: res.status });
  }
  return data;
}

// Requête authentifiée : en cas de 401, tente un refresh une fois, sinon déconnecte.
async function authed(path, opts = {}) {
  try {
    return await raw(path, { ...opts, token: session.access });
  } catch (e) {
    if (e.status !== 401 || !session.refresh) throw e;
    try {
      const r = await refresh(session.refresh);
      const t = { access: r.access_token, refresh: r.refresh_token };
      session = { ...session, ...t }; session.onChange(t);
      return await raw(path, { ...opts, token: t.access });
    } catch (e2) { session.onExpired(); throw e2; }
  }
}

// ---- Authentification ----
export const login = ({ email, password, mfa_code }) =>
  raw("/auth/login", { method: "POST", body: { email, password, ...(mfa_code ? { mfa_code } : {}) } });
export const refresh = (refresh_token) => raw("/auth/refresh", { method: "POST", body: { refresh_token } });
export const getMe = (token) => raw("/auth/me", { token });

// ---- Espace cabinet ----
export const getDashboard = () => authed("/espace/dashboard");
export const getClients = (q = "") => authed(`/espace/clients${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const getMissions = () => authed("/espace/missions");

export const getAbonnement = () => authed("/espace/abonnement");
export const payerAbonnement = () => authed("/espace/abonnement/payer", { method: "POST" });
export const getOffres = () => authed("/espace/offres");
export const changerOffre = (plan_code, periode) => authed("/espace/abonnement/changer-offre", { method: "POST", body: { plan_code, periode } });

// ---- Site public : offres, inscription, paiement ----
export const getPlans = () => raw("/public/plans");
export const signup = (payload) => raw("/public/signup", { method: "POST", body: payload });
export const getPaiement = (ref) => raw(`/public/paiements/${ref}`);
export const confirmerPaiementTest = (ref) => raw(`/public/paiements/${ref}/confirmer-test`, { method: "POST" });
export const getOptionsPaiement = (ref) => raw(`/public/paiements/${ref}/options`);
export const payerStripe = (ref) => raw(`/public/paiements/${ref}/stripe`, { method: "POST" });
export const payerMobileMoney = (ref, body) => raw(`/public/paiements/${ref}/mobile-money`, { method: "POST", body });
export const payerFedapay = (ref) => raw(`/public/paiements/${ref}/fedapay`, { method: "POST" });
export const payerVirement = (ref) => raw(`/public/paiements/${ref}/virement`, { method: "POST" });

// ---- Clients, missions et dossier d'audit ----
export const creerClient = (body) => authed("/espace/clients", { method: "POST", body });
export const getOptionsMission = () => authed("/espace/referentiels-types");
export const creerMission = (body) => authed("/espace/missions", { method: "POST", body });
export const getMission = (id) => authed(`/espace/missions/${id}`);
export const basculerDiligence = (id, did) => authed(`/espace/missions/${id}/diligences/${did}`, { method: "PATCH" });
export const getControles = (id) => authed(`/espace/missions/${id}/controles`);
export const importerBalance = (id, fichier) => { const f = new FormData(); f.append("fichier", fichier); return authed(`/missions/${id}/import/balance`, { method: "POST", body: f }); };
export const calculerSeuils = (id, body) => authed(`/missions/${id}/seuils`, { method: "POST", body });
export const getAnalyse = (id) => authed(`/missions/${id}/analyse-financiere`);
export const getRevue = (id) => authed(`/missions/${id}/revue-analytique`);
export const getBenford = (id) => authed(`/missions/${id}/fraude/benford`);
export const getIndicateursFraude = (id) => authed(`/missions/${id}/fraude/indicateurs`);

// ---- Mission : risques, planification, acceptation, rapports ----
export const getRisques = (id) => authed(`/missions/${id}/risques`);
export const getHeatmap = (id) => authed(`/missions/${id}/risques/heatmap`);
export const ajouterRisque = (id, body) => authed(`/missions/${id}/risques`, { method: "POST", body });
export const getPlanification = (id) => authed(`/missions/${id}/planification`);
export const majPlanification = (id, body) => authed(`/missions/${id}/planification`, { method: "PUT", body });
export const ajouterJalon = (id, body) => authed(`/missions/${id}/planification/jalons`, { method: "POST", body });
export const ajouterEquipe = (id, body) => authed(`/missions/${id}/planification/equipe`, { method: "POST", body });
export const ajouterBudget = (id, body) => authed(`/missions/${id}/planification/budget`, { method: "POST", body });
export const getCollaborateurs = () => authed("/espace/collaborateurs");
export const getAcceptation = (id) => authed(`/missions/${id}/acceptation`);
export const majAcceptation = (id, body) => authed(`/missions/${id}/acceptation`, { method: "PUT", body });
export const deciderAcceptation = (id, body) => authed(`/missions/${id}/acceptation/decision`, { method: "POST", body });
export const genererLettre = (id) => authed(`/missions/${id}/acceptation/lettre-mission`, { method: "POST" });
export const telechargerRapport = (id, type, format) => authed(`/missions/${id}/rapports/${type}?format=${format}`, { blob: true });
