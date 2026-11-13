import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import Logo from "../Logo.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { Icon, ICONS } from "./ui.jsx";
import { MODULES_CABINET } from "../../modules.js";

const NAV = [["/espace", "Tableau de bord", "home", true], ["/espace/clients", "Clients", "users"], ["/espace/missions", "Missions", "folder"], ["/espace/abonnement", "Abonnement", "card"]];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const initiales = (user.nom_complet || user.email).split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="app-shell">
      <aside className={`app-side${open ? " open" : ""}`}>
        <div className="side-logo"><Logo height={38} pill /></div>
        <nav onClick={() => setOpen(false)}>
          {NAV.map(([to, label, icon, end]) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `side-link${isActive ? " on" : ""}`}><Icon d={ICONS[icon]} />{label}</NavLink>
          ))}
          <div className="side-sep">Modules du cabinet</div>
          {/* Écrans rendus par le back (même origine via le proxy) : navigation complète, pas de route React. */}
          {MODULES_CABINET.filter((m) => !m.role || user.roles.includes(m.role)).map((m) => (
            <a key={m.href} className="side-link" href={m.href}><Icon d={ICONS[m.icon]} />{m.label}</a>
          ))}
          <div className="side-sep">Dans une mission</div>
          <span className="side-link soon">Cycles, FEC, rapprochement, TVA, DSN, CSRD, fusion…<em>onglet « Modules »</em></span>
        </nav>
        <button className="side-out" onClick={logout}><Icon d={ICONS.logout} />Se déconnecter</button>
      </aside>
      {open && <div className="app-scrim" onClick={() => setOpen(false)} />}
      <div className="app-main">
        <header className="app-top">
          <button className="burger2" onClick={() => setOpen(true)} aria-label="Menu"><Icon d={ICONS.menu} /></button>
          <div className="top-user"><div className="avatar">{initiales}</div>
            <div><b>{user.nom_complet || user.email}</b><small>{user.roles.join(", ")}</small></div></div>
        </header>
        <main className="app-content"><Outlet /></main>
      </div>
    </div>
  );
}
