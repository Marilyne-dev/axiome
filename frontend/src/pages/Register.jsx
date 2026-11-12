import { useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import AuthLayout from "./AuthLayout.jsx";
import PasswordField, { Strength } from "../components/PasswordField.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getPlans, signup } from "../api.js";
import { fmtMontant } from "../format.js";

const PAYS = ["France", "Martinique", "Guadeloupe", "Bénin", "Côte d'Ivoire", "Sénégal", "Togo", "Cameroun", "Mali", "Burkina Faso", "Niger", "Gabon", "Congo", "Belgique", "Suisse", "Luxembourg", "Maroc", "Tunisie", "Autre"];

export default function Register() {
  const { user } = useAuth();
  const [q] = useSearchParams();
  const [plans, setPlans] = useState([]);
  const [f, setF] = useState({
    plan_code: q.get("plan") || "cabinet", periode: q.get("periode") === "annuel" ? "annuel" : "mensuel",
    devise: q.get("devise") === "XOF" ? "XOF" : "EUR", cabinet_nom: "", pays: "France",
    admin_nom: "", admin_email: "", admin_password: "", confirm: "",
  });
  const [err, setErr] = useState(""); const [loading, setLoading] = useState(false); const [fait, setFait] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  useEffect(() => { getPlans().then(setPlans).catch(() => setErr("Impossible de charger les offres. Réessayez.")); }, []);

  if (user) return <Navigate to="/espace" replace />;
  const plan = plans.find((p) => p.code === f.plan_code);
  const match = f.confirm && (f.admin_password === f.confirm ? "ok" : "ko");

  const submit = async (e) => {
    e.preventDefault(); setErr("");
    if (f.admin_password !== f.confirm) return setErr("Les mots de passe ne correspondent pas.");
    setLoading(true);
    try {
      const { confirm, ...payload } = f;
      const r = await signup(payload);
      if (r.checkout_url) window.location.assign(r.checkout_url);
      else setFait(r.message || "Compte créé.");
    } catch (e2) { setErr(e2.message); setLoading(false); }
  };

  if (fait) return (
    <AuthLayout title="Compte créé" subtitle="Il reste une étape : le paiement.">
      <div className="alert ok">{fait}</div>
      <p className="muted" style={{ margin: "14px 0" }}>Connectez-vous pour régler votre abonnement depuis la page « Abonnement ».</p>
      <Link className="btn btn-primary" to="/connexion">Se connecter</Link>
    </AuthLayout>
  );

  return (
    <AuthLayout title="Créer l'espace de votre cabinet" subtitle="Vous serez l'administrateur de l'espace et pourrez créer les comptes de vos commissaires aux comptes."
      footer={<>Déjà inscrit ? <Link to="/connexion">Se connecter</Link></>}>
      <form className="auth-form" onSubmit={submit}>
        <div className="two">
          <label className="field">Offre
            <select value={f.plan_code} onChange={set("plan_code")}>{plans.map((p) => <option key={p.code} value={p.code}>{p.nom}</option>)}</select></label>
          <label className="field">Facturation
            <select value={f.periode} onChange={set("periode")}><option value="mensuel">Mensuelle</option><option value="annuel">Annuelle (2 mois offerts)</option></select></label>
        </div>
        <label className="field">Devise de paiement
          <select value={f.devise} onChange={set("devise")}><option value="EUR">Euro (carte bancaire)</option><option value="XOF">Franc CFA (Mobile Money, carte)</option></select></label>
        {plan && <div className="recap"><b>{plan.nom}</b><span>{fmtMontant(plan.prix[f.devise][f.periode], f.devise)} / {f.periode === "mensuel" ? "mois" : "an"}</span></div>}
        <div className="two">
          <label className="field">Nom du cabinet<input required minLength={2} autoComplete="organization" value={f.cabinet_nom} onChange={set("cabinet_nom")} /></label>
          <label className="field">Pays<select value={f.pays} onChange={set("pays")}>{PAYS.map((p) => <option key={p}>{p}</option>)}</select></label>
        </div>
        <div className="two">
          <label className="field">Votre nom complet<input required minLength={2} autoComplete="name" value={f.admin_nom} onChange={set("admin_nom")} /></label>
          <label className="field">E-mail professionnel<input type="email" required autoComplete="email" value={f.admin_email} onChange={set("admin_email")} /></label>
        </div>
        <PasswordField label="Mot de passe (10 caractères minimum, lettres et chiffres)" minLength={10} autoComplete="new-password"
          value={f.admin_password} onChange={set("admin_password")}><Strength value={f.admin_password} /></PasswordField>
        <PasswordField label="Confirmer le mot de passe" minLength={10} autoComplete="new-password" value={f.confirm} onChange={set("confirm")}>
          {match && <span className={`match ${match}`}>{match === "ok" ? "✓ Les mots de passe correspondent" : "Les mots de passe sont différents"}</span>}
        </PasswordField>
        {err && <div className="alert ko shake" key={err}>{err}</div>}
        <button className="btn btn-primary" disabled={loading || !plan}>{loading ? "Création de votre espace…" : "Continuer vers le paiement"}</button>
      </form>
      <Link to="/" className="back-home">← Retour au site</Link>
    </AuthLayout>
  );
}
