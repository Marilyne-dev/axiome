import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Background from "../components/Background.jsx";
import { Why } from "../components/Illustrations.jsx";
import Fx from "../components/Fx.jsx";
import HeroVisual from "../components/HeroVisual.jsx";
import { Stats, Pipeline } from "../components/Sections.jsx";
import { getPlans } from "../api.js";
import { CONTENT } from "../content.js";
import Logo from "../components/Logo.jsx";
import heroImg from "../assets/hero-bg.svg";

const fmt = (n) => new Intl.NumberFormat("fr-FR").format(Math.round(n));


/* ---------------------------------------------------------------- nav */
function Nav() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <header className="nav">
      <div className="wrap nav-in">
        <a href="#top" className="logo"><Logo height={40} /></a>
        <nav className={`nav-links${open ? " open" : ""}`}>
          <a href="#produits" onClick={close}>Produits</a>
          <a href="#tarifs" onClick={close}>Tarifs</a>
          <a href="#faq" onClick={close}>FAQ</a>
        </nav>
        <div className="nav-cta">
          <RouterLink to="/connexion" className="link-soft">Se connecter</RouterLink>
          <RouterLink to="/inscription" className="btn btn-ghost">Créer un compte</RouterLink>
        </div>
        <button className="burger" aria-label="Menu" onClick={() => setOpen(!open)}>
          <svg width="20" height="20" viewBox="0 0 24 24" stroke="#27384B" strokeWidth="2"><path d="M3 6h18M3 12h18M3 18h18" /></svg>
        </button>
      </div>
    </header>
  );
}

/* ---------------------------------------------------------------- hero + trust */
const Words = ({ text, start }) => text.split(" ").map((w, i) => (
  <span key={i}>{i > 0 && " "}<span className="w" style={{ animationDelay: `${start + i * 90}ms` }}>{w}</span></span>
));

const Hero = () => (
  <section className="hero" id="top">
    <div className="hero-img" style={{ backgroundImage: `url(${heroImg})` }} aria-hidden="true" />
    <Background variant="light" />
    <div className="wrap">
      <span className="badge"><span className="dot" />Nouveau · La suite AXIOME pour la campagne 2026–2027</span>
      <h1><Words text="Augmentez" start={150} /><br /><span className="accent"><Words text="vos missions d'audit." start={350} /></span></h1>
      <p className="sub">Un écosystème intelligent et intégré, conçu pour les commissaires aux comptes — du FEC à la certification.</p>
      <div className="hero-cta">
        <RouterLink to="/inscription" className="btn btn-primary">Créer un compte</RouterLink>
        <a href="#process" className="btn btn-light">Comment ça marche</a>
      </div>
      <HeroVisual />
    </div>
  </section>
);

const Trust = ({ standards }) => (
  <section className="trust">
    <div className="wrap">
      <div className="lbl">Conçu pour le commissariat aux comptes</div>
      <div className="marquee"><div className="marquee-track">
        {[...standards, ...standards, ...standards, ...standards].map((s, i) => <span className="std" key={i}><b>{s.tag}</b> {s.label}</span>)}
      </div></div>
      <div className="distinction"><span className="dot" />Méthodologie alignée sur les NEP révisées et la doctrine CNCC</div>
    </div>
  </section>
);

/* ---------------------------------------------------------------- modules */
const Chip = ({ bg, children }) => <span className="chip-logo" style={{ background: bg }}>{children}</span>;

function ModuleViz({ id }) {
  if (id === "analytics")
    return (
      <div className="viz flow-mini">
        <span className="tagpill">FEC</span><span className="tagpill">DSN</span><span className="arrow">→</span>
        <Chip bg="#2F5BFF">ML</Chip><span className="arrow">→</span>
        <Chip bg="#E0A100">BI</Chip><Chip bg="#1E7145">XL</Chip><Chip bg="#1B49C4">W</Chip>
      </div>
    );
  if (id === "platform")
    return (
      <div className="viz"><div className="row-check">
        <div className="rc"><span className="l"><span className="ico-ok">✓</span>Acceptation</span><span className="st-ok">Complète</span></div>
        <div className="rc"><span className="l"><span className="ico-ok">✓</span>Planification</span><span className="st-ok">Complète</span></div>
        <div className="rc"><span className="l"><span className="ico-run">●</span>Réalisation</span><span className="st-run">En cours</span></div>
      </div></div>
    );
  return (
    <div className="viz flow-mini" style={{ justifyContent: "center" }}>
      <Chip bg="#1E7145">XL</Chip><span className="arrow">⟷</span>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#7A6310" strokeWidth="1.8"><path d="M9 15l6-6M8 13l-2 2a3 3 0 104 4l2-2M16 11l2-2a3 3 0 10-4-4l-2 2" /></svg>
      <span className="arrow">⟷</span><Chip bg="#C0392B">PDF</Chip>
    </div>
  );
}

const cls = { analytics: "m-analytics", platform: "m-platform", link: "m-link" };

const Modules = ({ modules }) => (
  <section className="section" id="produits">
    <div className="wrap">
      <div className="sec-head">
        <div className="eyebrow">Les produits</div>
        <h2>Un écosystème, trois modules.</h2>
        <p>AXIOME couvre toute la mission, du retraitement des données comptables à la documentation du dossier.
          Trois modules — <b>Analytics</b>, <b>Plateforme</b> et <b>Link</b> — souscriptibles séparément ou ensemble.</p>
      </div>
      <div className="modules">
        {modules.map((m) => (
          <div className={`mod ${cls[m.id]}`} key={m.id}>
            <div className="num">{m.num} <b className="acn">{m.name}</b></div>
            <h3>{m.title}</h3>
            <p>{m.text}</p>
            <ModuleViz id={m.id} />
          </div>
        ))}
      </div>
    </div>
  </section>
);

/* ---------------------------------------------------------------- analytics */
const Analytics = ({ outputs }) => (
  <section className="section alt" id="analytics">
    <div className="wrap detail">
      <div className="d-text">
        <div className="eyebrow" style={{ color: "var(--blue)" }}><span className="n">01</span> ANALYTICS</div>
        <h2>Des documents prêts à l'emploi, pour chaque phase de la mission.</h2>
        <p>À partir du <b>FEC, des grands livres et de la DSN</b>, le module Analytics génère une bibliothèque de fichiers
          préétablis et précomplétés : il structure les travaux, fiabilise les analyses et livre une restitution à forte valeur ajoutée.</p>
        <ul className="d-list">
          <li><span className="tick">✓</span>100+ procédures précomplétées, prêtes à intégrer au dossier</li>
          <li><span className="tick">✓</span>Détection d'anomalies par Machine Learning (Isolation Forest, SHAP)</li>
          <li><span className="tick">✓</span>Revue analytique commentée, alignée NEP 520</li>
        </ul>
      </div>
      <div className="d-media">
        <div className="outputs">
          {outputs.map((o) => (
            <div className="out" key={o.tool}>
              <div className="head"><Chip bg={o.color}>{o.logo}</Chip><span className="mono">{o.tool}</span></div>
              <h4>{o.title}</h4><p>{o.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  </section>
);

/* ---------------------------------------------------------------- réconciliation CA (appelle le backend Python) */
const INIT = { ca: 63429831, encaissements: 65925562, creances_n: 9747605, creances_n1: 12000000, factures_a_etablir: 93445 };
const LABELS = {
  ca: "Chiffre d'affaires", encaissements: "Encaissements", creances_n: "Créances N",
  creances_n1: "Créances N-1", factures_a_etablir: "Factures à établir",
};


/* ---------------------------------------------------------------- plateforme */
const Platform = () => (
  <section className="section alt" id="platform">
    <div className="wrap">
      <div className="sec-head" style={{ textAlign: "left", maxWidth: "none", marginBottom: 34 }}>
        <div className="eyebrow" style={{ color: "var(--indigo)" }}>02 &nbsp;PLATEFORME</div>
        <h2>La plateforme d'audit nouvelle génération.</h2>
        <p style={{ marginLeft: 0 }}>Une plateforme moderne pour piloter vos missions, avec des questionnaires intelligents au service
          de votre jugement, alignée nativement sur les NEP révisées et connectée à votre environnement.</p>
      </div>
      <div className="steps">
        {["Acceptation", "Planification", "Réalisation", "Finalisation"].map((s, i) => (
          <span key={s} className="step">
            <span className="n">0{i + 1}</span> {s}{i < 3 && <span className="sep">→</span>}
          </span>
        ))}
      </div>
      <div className="pcards">
        <div className="pcard">
          <h3>Accompagner sans prescrire</h3>
          <p>Des signaux visuels guident la documentation. Les conclusions restent celles du commissaire aux comptes.</p>
          <div className="pbox">
            <div className="rc"><span className="l"><span className="ico-ok">✓</span>Prise de connaissance</span><span className="st-ok">Complète</span></div>
            <div className="rc" style={{ marginTop: 9 }}><span className="l"><span className="ico-run">!</span>Seuil de signification</span><span className="st-run">À compléter</span></div>
            <div className="orient"><div className="k">Orientation · prise de connaissance</div>
              <p><b>10 facteurs défavorables, 2 favorables</b> — la prédominance plaide pour un positionnement bas de fourchette.</p></div>
          </div>
        </div>
        <div className="pcard">
          <h3>Conforme aux NEP</h3>
          <p>Aligné sur l'ensemble des Normes d'Exercice Professionnel applicables, mis à jour en continu.</p>
          <div className="pbox">
            <div className="nepchip"><span className="tag">NEP 315</span> révisée · risques</div><br />
            <div className="nepchip"><span className="tag">NEP 330</span> révisée · réponse</div><br />
            <div className="nepchip"><span className="tag">NEP 240</span> fraude · ISA 240</div>
          </div>
        </div>
        <div className="pcard">
          <h3>Conformité réglementaire intégrée</h3>
          <p>IA Act, LCB-FT (TRACFIN), fraude, RGPD et déontologie — évalués et tracés dans le dossier.</p>
          <div className="pbox">
            <div className="rc"><span className="l">🤖 IA Act — classement du système</span></div>
            <div className="rc" style={{ marginTop: 9 }}><span className="l">🛡️ LCB-FT — vigilance &amp; soupçon</span></div>
            <div className="rc" style={{ marginTop: 9 }}><span className="l">🔗 API officielles INSEE · INPI · BODACC</span></div>
          </div>
        </div>
      </div>
    </div>
  </section>
);

/* ---------------------------------------------------------------- link */
const Link = () => (
  <section className="section" id="link">
    <div className="wrap detail">
      <div className="d-text">
        <div className="eyebrow" style={{ color: "var(--citron-d)" }}><span style={{ fontFamily: "var(--disp)", fontWeight: 800, fontSize: 22 }}>03</span> LINK</div>
        <h2>Les justificatifs, à portée de cellule.</h2>
        <p>Link est un add-in Excel qui permet d'importer et de référencer les justificatifs directement depuis les papiers de travail.
          Chaque pièce reste à portée de clic depuis votre feuille.</p>
        <ul className="d-list">
          <li><span className="tick">✓</span>Glisser-déposer les justificatifs dans Excel</li>
          <li><span className="tick">✓</span>Référencement cellule ⟷ pièce justificative</li>
          <li><span className="tick">✓</span>Un clic pour ouvrir la pièce probante depuis la cellule</li>
        </ul>
      </div>
      <div className="d-media">
        <div className="mock xl">
          <div className="xl-top">Microsoft Excel — Balance.xlsx<span className="live"><i />Link · add-in actif</span></div>
          <div className="xl-grid">
            <div className="xl-cells"><table><tbody>
              <tr><th>N°</th><th>Compte</th><th>Solde</th></tr>
              <tr><td>1</td><td>411000</td><td>142 380</td></tr>
              <tr className="sel"><td>2</td><td>512000</td><td>38 920 ●</td></tr>
              <tr><td>3</td><td>401000</td><td>87 410</td></tr>
              <tr><td>4</td><td>607000</td><td>24 105</td></tr>
              <tr><td>5</td><td>445000</td><td>11 230</td></tr>
            </tbody></table></div>
            <div className="xl-side">
              <div className="h">🔗 Link · cellule B3 liée</div>
              <div className="xl-doc">
                <div className="f">📄 Relevé_BNP_12.pdf</div>
                <div className="meta">BNP Paribas — Décembre 2024<br />Solde initial · 42 100,00<br />Débits · −18 245,33<br />Crédits · +15 065,33</div>
                <div className="solde"><span>Solde 31/12</span><span>38 920,00</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);

/* ---------------------------------------------------------------- tarifs + faq */
const prixFmt = (v, devise) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: devise, maximumFractionDigits: devise === "XOF" ? 0 : 2 })
  .format(devise === "XOF" ? v : v / 100);

function Plans() {
  const [plans, setPlans] = useState(null);
  const [devise, setDevise] = useState("EUR");
  const [periode, setPeriode] = useState("mensuel");
  useEffect(() => { getPlans().then(setPlans).catch(() => setPlans([])); }, []);
  const Toggle = ({ value, set, options }) => (
    <div className="toggle">{options.map(([v, l]) => <button key={v} type="button" className={value === v ? "on" : ""} onClick={() => set(v)}>{l}</button>)}</div>
  );
  return (
    <section className="section alt" id="tarifs">
      <div className="wrap">
        <div className="sec-head">
          <div className="eyebrow">Tarifs</div>
          <h2>Choisissez l'offre de votre cabinet.</h2>
          <p>Un espace dédié par cabinet, des comptes pour vos commissaires aux comptes, sans frais cachés. Paiement par carte bancaire ou Mobile Money.</p>
          <div className="toggles">
            <Toggle value={periode} set={setPeriode} options={[["mensuel", "Mensuel"], ["annuel", "Annuel · 2 mois offerts"]]} />
            <Toggle value={devise} set={setDevise} options={[["EUR", "EUR €"], ["XOF", "XOF FCFA"]]} />
          </div>
        </div>
        {plans === null && <p className="muted" style={{ textAlign: "center" }}>Chargement des offres…</p>}
        {plans && plans.length === 0 && <p className="muted" style={{ textAlign: "center" }}>Les offres sont momentanément indisponibles. Réessayez dans un instant.</p>}
        <div className="plans">
          {(plans || []).map((p) => (
            <div className={`plan${p.featured ? " feat" : ""}`} key={p.code}>
              <div className="pname">{p.nom}</div>
              <div className="pdesc">{p.description}</div>
              <div className="price">{prixFmt(p.prix[devise][periode], devise)}<small> / {periode === "mensuel" ? "mois" : "an"}</small></div>
              <ul>{p.fonctionnalites.map((f) => <li key={f}><span className="tick">✓</span>{f}</li>)}</ul>
              <RouterLink to={`/inscription?plan=${p.code}&periode=${periode}&devise=${devise}`}
                className={`btn ${p.featured ? "btn-primary" : "btn-ghost"}`}>S'abonner</RouterLink>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq({ faq }) {
  const [open, setOpen] = useState(0);
  return (
    <section className="section" id="faq">
      <div className="wrap">
        <div className="sec-head"><div className="eyebrow">FAQ</div><h2>Questions fréquentes.</h2></div>
        <div className="faq">
          {faq.map((f, i) => (
            <details className="qa" key={f.q} open={open === i}
              onClick={(e) => { e.preventDefault(); setOpen(open === i ? -1 : i); }}>
              <summary>{f.q}<span className="pm">+</span></summary>
              <div className="a">{f.a}</div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Appel final */
function Cta() {
  return (
    <section className="section" id="commencer" style={{ paddingBottom: 0 }}>
      <div className="cta"><Background variant="dark" />
        <h2>Prêt à augmenter vos missions d'audit ?</h2>
        <p>Créez l'espace de votre cabinet en quelques minutes et invitez vos commissaires aux comptes.</p>
        <div className="cta-actions">
          <a href="#tarifs" className="btn btn-primary">Choisir mon offre</a>
          <RouterLink to="/connexion" className="btn btn-ghost-light">Se connecter</RouterLink>
        </div>
      </div>
    </section>
  );
}

const Footer = () => (
  <footer>
    <div className="wrap">
      <div className="foot-grid">
        <div>
          <div className="logo"><Logo height={42} pill /></div>
          <p className="foot-about">AXIOME Audit &amp; Expertise — l'audit légal augmenté par la donnée. Fort-de-France, Martinique. Inscrite à la CNCC.</p>
        </div>
        <div className="foot-col"><h5>Produits</h5><a href="#analytics">Analytics</a><a href="#platform">Plateforme</a><a href="#link">Link</a><a href="#tarifs">Tarifs</a></div>
        <div className="foot-col"><h5>Ressources</h5><a href="#faq">FAQ</a><a href="#">Documentation</a><a href="#">Conformité &amp; sécurité</a></div>
        <div className="foot-col"><h5>Cabinet</h5><a href="#">À propos</a><a href="#">Contact</a><RouterLink to="/connexion">Se connecter</RouterLink></div>
      </div>
      <div className="foot-bot">
        <span>© 2026 AXIOME Audit &amp; Expertise. Tous droits réservés.</span>
        <span>Mentions légales · Politique de confidentialité (RGPD) · CGV</span>
      </div>
    </div>
  </footer>
);

/* ---------------------------------------------------------------- App */
export default function Landing() {
  const data = CONTENT;

  return (
    <>
      <Fx />
      <Nav />
      <Hero />
      <Trust standards={data.standards} />
      <Stats />
      <Pipeline />
      <Modules modules={data.modules} />
      <Why />
      <Analytics outputs={data.outputs} />
      <Platform />
      <Link />
      <Plans />
      <Faq faq={data.faq} />
      <Cta />
      <Footer />
    </>
  );
}
