import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import AuthLayout from "./AuthLayout.jsx";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { confirmerPaiementTest, getOptionsPaiement, getPaiement, payerFedapay, payerMobileMoney, payerStripe, payerVirement } from "../api.js";
import { fmtMontant } from "../format.js";

/** Retour du fournisseur de paiement : on vérifie l'état réel puis on ouvre l'espace. */
export function PaiementRetour() {
  const [q] = useSearchParams(); const ref = q.get("ref"); const annule = q.get("annule");
  const [etat, setEtat] = useState(null); const [err, setErr] = useState("");
  useEffect(() => {
    if (!ref) return;
    let stop = false, essais = 0;
    const tick = async () => {
      try {
        const r = await getPaiement(ref); if (stop) return; setEtat(r);
        if (r.statut === "en_attente" && ++essais < 40) setTimeout(tick, 3000);
      } catch (e) { if (!stop) setErr(e.message); }
    };
    tick(); return () => { stop = true; };
  }, [ref]);

  if (!ref || err) return <AuthLayout title="Paiement introuvable"><div className="alert ko">{err || "Lien de paiement invalide."}</div><Link className="btn btn-ghost" to="/">Retour au site</Link></AuthLayout>;
  if (!etat) return <AuthLayout title="Vérification du paiement…"><p className="muted">Un instant.</p></AuthLayout>;
  if (etat.statut === "paye") return (
    <AuthLayout title="Paiement confirmé" subtitle={`Votre espace AXIOME — offre ${etat.plan} — est prêt.`}>
      <div className="alert ok">Merci ! {fmtMontant(etat.montant, etat.devise)} reçus. Votre abonnement est actif.</div>
      <Link className="btn btn-primary" style={{ marginTop: 16 }} to="/connexion">Accéder à mon espace</Link>
    </AuthLayout>);
  if (etat.statut === "echoue" || annule) return (
    <AuthLayout title="Paiement non abouti" subtitle="Aucun montant n'a été débité par AXIOME.">
      <p className="muted">Votre compte est créé : connectez-vous pour réessayer le paiement depuis la page « Abonnement ».</p>
      <Link className="btn btn-primary" style={{ marginTop: 16 }} to="/connexion">Se connecter</Link>
    </AuthLayout>);
  return <AuthLayout title="Paiement en cours de vérification…" subtitle="Cette page se met à jour automatiquement."><p className="muted">Si vous venez de payer, la confirmation peut prendre quelques instants.</p></AuthLayout>;
}

const ICONES = { stripe: "💳", mobile_money: "📱", fedapay: "🏦", virement: "🧾" };

/** Carte / SEPA : les champs sont ceux de Stripe (iframe sécurisée), rien ne passe par nos serveurs. */
function StripeForm({ reference, onError }) {
  const stripe = useStripe(); const elements = useElements(); const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const submit = async (e) => {
    e.preventDefault(); if (!stripe || !elements) return; setBusy(true); onError("");
    const { error } = await stripe.confirmPayment({ elements, redirect: "if_required",
      confirmParams: { return_url: `${window.location.origin}/paiement/retour?ref=${reference}` } });
    if (error) { onError(error.message || "Paiement refusé."); setBusy(false); } else nav(`/paiement/retour?ref=${reference}`);
  };
  return (
    <form onSubmit={submit} className="pay-panel" style={{ border: 0, paddingTop: 0 }}>
      <PaymentElement options={{ layout: "tabs" }} />
      <button className="btn btn-primary" disabled={!stripe || busy}>{busy ? "Traitement…" : "Payer"}</button>
    </form>
  );
}

function PanneauStripe({ reference, cle, onError }) {
  const [secret, setSecret] = useState(null);
  const stripePromise = useMemo(() => loadStripe(cle), [cle]);
  useEffect(() => { payerStripe(reference).then((r) => setSecret(r.client_secret)).catch((e) => onError(e.message)); }, [reference]);
  if (!secret) return <p className="muted">Chargement du formulaire sécurisé…</p>;
  return <Elements stripe={stripePromise} options={{ clientSecret: secret, locale: "fr" }}><StripeForm reference={reference} onError={onError} /></Elements>;
}

function PanneauMobileMoney({ reference, operateurs, onError }) {
  const nav = useNavigate();
  const [op, setOp] = useState(operateurs[0]?.code); const [numero, setNumero] = useState("");
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  const go = async (e) => {
    e.preventDefault(); setBusy(true); onError("");
    try { const r = await payerMobileMoney(reference, { operateur: op, numero }); setMsg(r.message); setTimeout(() => nav(`/paiement/retour?ref=${reference}`), 1500); }
    catch (e2) { onError(e2.message); setBusy(false); }
  };
  return (
    <form className="pay-panel" onSubmit={go}>
      <label className="field">Opérateur<select value={op} onChange={(e) => setOp(e.target.value)}>{operateurs.map((o) => <option key={o.code} value={o.code}>{o.libelle}</option>)}</select></label>
      <label className="field">Numéro Mobile Money<input required inputMode="tel" placeholder="97 00 00 00" value={numero} onChange={(e) => setNumero(e.target.value)} /></label>
      {msg ? <div className="alert ok">{msg}</div> : <button className="btn btn-primary" disabled={busy}>{busy ? "Envoi de la demande…" : "Payer avec Mobile Money"}</button>}
      <p className="pay-note">Vous recevrez une demande de confirmation sur ce numéro. Validez-la avec votre code secret.</p>
    </form>
  );
}

function PanneauFedapay({ reference, onError }) {
  const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); onError(""); try { const r = await payerFedapay(reference); window.location.assign(r.url); } catch (e) { onError(e.message); setBusy(false); } };
  return (
    <div className="pay-panel">
      <p className="pay-note">Vous serez redirigé vers la page sécurisée FedaPay : cartes Visa / Mastercard et tous les opérateurs Mobile Money.</p>
      <button className="btn btn-primary" onClick={go} disabled={busy}>{busy ? "Redirection…" : "Continuer vers FedaPay"}</button>
    </div>
  );
}

function PanneauVirement({ reference, onError }) {
  const [c, setC] = useState(null); const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); onError(""); try { setC(await payerVirement(reference)); } catch (e) { onError(e.message); } setBusy(false); };
  if (!c) return <div className="pay-panel"><button className="btn btn-primary" onClick={go} disabled={busy}>{busy ? "…" : "Afficher les coordonnées bancaires"}</button></div>;
  const L = [["Titulaire du compte", c.titulaire], ["Banque", c.banque], ["IBAN / N° de compte", c.iban], ["BIC", c.bic], ["Montant", fmtMontant(c.montant, c.devise)], ["Référence à indiquer", c.reference]].filter(([, v]) => v);
  return (
    <div className="pay-panel">
      <div className="pay-bank">{L.map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}</div>
      <p className="pay-note">Indiquez impérativement la référence dans le libellé du virement. Votre espace est activé dès réception (24 à 48 h ouvrées).</p>
      <Link className="btn btn-ghost" to="/connexion">J'ai effectué le virement</Link>
    </div>
  );
}

/** Page de paiement : le payeur choisit son moyen de paiement (carte, SEPA, Mobile Money, FedaPay, virement). */
export function PaiementPage() {
  const { ref } = useParams(); const nav = useNavigate();
  const [o, setO] = useState(null); const [err, setErr] = useState(""); const [choix, setChoix] = useState(null);
  useEffect(() => { getOptionsPaiement(ref).then(setO).catch((e) => setErr(e.message)); }, [ref]);
  useEffect(() => { if (o && o.statut !== "en_attente") nav(`/paiement/retour?ref=${ref}`, { replace: true }); }, [o]);
  const simuler = async () => { setErr(""); try { await confirmerPaiementTest(ref); nav(`/paiement/retour?ref=${ref}`); } catch (e) { setErr(e.message); } };

  if (!o) return <AuthLayout title="Paiement">{err ? <div className="alert ko">{err}</div> : <p className="muted">Chargement…</p>}</AuthLayout>;
  const m = o.methodes.find((x) => x.code === choix);
  return (
    <AuthLayout title="Régler votre abonnement" subtitle="Choisissez votre moyen de paiement. Les données de carte et de compte sont saisies dans des champs sécurisés des prestataires.">
      <div className="pay-total"><span>Offre {o.plan} · {o.periode === "annuel" ? "annuelle" : "mensuelle"}</span><b>{fmtMontant(o.montant, o.devise)}</b></div>
      {o.methodes.length === 0 && <div className="alert ko">Aucun moyen de paiement n'est encore activé pour cette devise. Contactez AXIOME.</div>}
      <div className="pay-methods">
        {o.methodes.map((x) => (
          <button type="button" key={x.code} className={`pay-m${choix === x.code ? " on" : ""}`} onClick={() => { setErr(""); setChoix(x.code); }}>
            <span className="ic">{ICONES[x.code]}</span><span><b>{x.libelle}</b><small>{x.detail}</small></span>
          </button>))}
      </div>
      {err && <div className="alert ko shake" key={err} style={{ marginBottom: 12 }}>{err}</div>}
      {m?.code === "stripe" && <PanneauStripe reference={ref} cle={o.stripe_cle_publique} onError={setErr} />}
      {m?.code === "mobile_money" && <PanneauMobileMoney reference={ref} operateurs={m.operateurs} onError={setErr} />}
      {m?.code === "fedapay" && <PanneauFedapay reference={ref} onError={setErr} />}
      {m?.code === "virement" && <PanneauVirement reference={ref} onError={setErr} />}
      {o.simulation && (
        <div className="pay-test"><b>Mode test (développement uniquement)</b>
          <span>Aucun argent réel. Ce bouton n'existe pas en production.</span>
          <button type="button" className="btn btn-ghost" onClick={simuler}>Simuler un paiement réussi</button></div>)}
      <Link to="/connexion" className="back-home">← Payer plus tard</Link>
    </AuthLayout>
  );
}
