import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import Logo from "../Logo.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { Icon, ICONS } from "./ui.jsx";
import { modulesCabinetPour } from "../../modules.js";
import { pick, useI18n } from "../../i18n.jsx";
import "../../langswitch.css";

const SPARK = <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" />;
const NAV = [["/espace", "nav.dashboard", ICONS.home, true], ["/espace/clients", "nav.clients", ICONS.users], ["/espace/missions", "nav.missions", ICONS.folder],
  ["/espace/assistant", "nav.assistant", SPARK], ["/espace/abonnement", "nav.subscription", ICONS.card]];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const initiales = (user.nom_complet || user.email).split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="app-shell">
      <aside className={`app-side${open ? " open" : ""}`}>
        <div className="side-logo"><Logo height={38} pill /></div>
        <nav onClick={() => setOpen(false)}>
          {NAV.map(([to, cle, icone, end]) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `side-link${isActive ? " on" : ""}`}><Icon d={icone} />{t(cle)}</NavLink>
          ))}
          <div className="side-sep">{t("nav.cabinet")}</div>
          {/* Écrans rendus par le back (même origine via le proxy) : navigation complète, pas de route React. */}
          {modulesCabinetPour(user.roles).map((m) => (
            <a key={m.href} className="side-link" href={m.href}><Icon d={ICONS[m.icon]} />{pick(m.label, lang)}</a>
          ))}
          <div className="side-sep">{t("nav.inMission")}</div>
          <span className="side-link soon">{t("nav.inMissionHint")}<em>{t("nav.inMissionTab")}</em></span>
        </nav>
        <button className="side-out" onClick={logout}><Icon d={ICONS.logout} />{t("nav.logout")}</button>
      </aside>
      {open && <div className="app-scrim" onClick={() => setOpen(false)} />}
      <div className="app-main">
        <header className="app-top">
          <button className="burger2" onClick={() => setOpen(true)} aria-label="Menu"><Icon d={ICONS.menu} /></button>
          <button type="button" className="lang-switch" onClick={() => setLang(lang === "fr" ? "en" : "fr")} aria-label="Language">{t("lang.switch")}</button>
          <div className="top-user"><div className="avatar">{initiales}</div>
            <div><b>{user.nom_complet || user.email}</b><small>{user.roles.join(", ")}</small></div></div>
        </header>
        <main className="app-content"><Outlet /></main>
      </div>
    </div>
  );
}
