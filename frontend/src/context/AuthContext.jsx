import { createContext, useContext, useEffect, useState } from "react";
import * as api from "../api.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

const KEY = "axiome_tokens";
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };

// Jetons restaurés dès le chargement du module, avant tout appel API.
const initial = load();
if (initial) api.setSession({ access: initial.access, refresh: initial.refresh });

export function AuthProvider({ children }) {
  const [tokens, setTokens] = useState(load);
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!tokens);

  const store = (t) => { localStorage.setItem(KEY, JSON.stringify(t)); setTokens(t); api.setSession({ access: t.access, refresh: t.refresh }); };
  const logout = () => {
    localStorage.removeItem(KEY); setTokens(null); setUser(null); api.setSession({ access: null, refresh: null });
    // Supprime aussi le cookie de session utilisé par les écrans rendus par le back (sinon ils restent accessibles).
    try { fetch("/logout", { redirect: "manual", credentials: "same-origin" }).catch(() => {}); } catch { /* sans effet */ }
  };
  api.setSession({ onChange: store, onExpired: logout });

  // Au chargement : vérifie le jeton ; s'il est expiré, tente le refresh avant de déconnecter.
  useEffect(() => {
    if (!tokens) return;
    (async () => {
      try { setUser(await api.getMe(tokens.access)); }
      catch {
        try {
          const r = await api.refresh(tokens.refresh);
          const t = { access: r.access_token, refresh: r.refresh_token };
          store(t); setUser(await api.getMe(t.access));
        } catch { logout(); }
      } finally { setReady(true); }
    })();
  }, []); // eslint-disable-line

  // Retourne { mfaRequired: true } si le code MFA est demandé, sinon ouvre la session.
  const signIn = async (payload) => {
    const r = await api.login(payload);
    if (r.mfa_required) return { mfaRequired: true };
    const t = { access: r.access_token, refresh: r.refresh_token };
    store(t); setUser(await api.getMe(t.access));
    return { mfaRequired: false };
  };


  return <AuthContext.Provider value={{ user, ready, signIn, logout }}>{children}</AuthContext.Provider>;
}
