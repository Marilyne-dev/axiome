import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import AuthLayout from "./AuthLayout.jsx";
import PasswordField from "../components/PasswordField.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const { user, signIn } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", mfa_code: "" });
  const [mfa, setMfa] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/espace" replace />;

  const submit = async (e) => {
    e.preventDefault(); setLoading(true); setErr("");
    try {
      const r = await signIn(f);
      if (r.mfaRequired) { setMfa(true); setErr("Saisissez le code à 6 chiffres de votre application d'authentification."); }
      else nav("/espace");
    }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  return (
    <AuthLayout title="Bon retour parmi nous" subtitle="Connectez-vous pour accéder à votre espace AXIOME."
      footer={<>Pas encore de compte ? <Link to="/inscription">Créer un compte</Link></>}>
      <form className="auth-form" onSubmit={submit}>
        <label className="field">E-mail
          <input type="email" required autoComplete="email" value={f.email}
            onChange={(e) => setF({ ...f, email: e.target.value })} />
        </label>
        <PasswordField label="Mot de passe" autoComplete="current-password" value={f.password}
          onChange={(e) => setF({ ...f, password: e.target.value })} />
        {mfa && (
          <label className="field">Code de vérification
            <input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required autoFocus autoComplete="one-time-code"
              value={f.mfa_code} onChange={(e) => setF({ ...f, mfa_code: e.target.value })} />
          </label>
        )}
        {err && <div className="alert ko shake" key={err}>{err}</div>}
        <button className="btn btn-primary" disabled={loading}>{loading ? "Connexion…" : "Se connecter"}</button>
      </form>
      <Link to="/" className="back-home">← Retour au site</Link>
    </AuthLayout>
  );
}
