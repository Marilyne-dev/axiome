import { MODULES_MISSION } from "../../../modules.js";
import "./modules.css";

// Onglet « Modules » : accès à tous les écrans d'audit rendus par le back pour cette mission.
// Navigation complète (<a>) : ces pages ne sont pas des routes React, elles sont servies par FastAPI
// sur la même origine (proxy Vite) et reconnaissent la session via le cookie posé à la connexion.
export default function Modules({ m }) {
  return (
    <div className="modules">
      <p className="muted">Ces modules s'ouvrent dans l'espace de travail AXIOME de la mission « {m.intitule} ». Utilisez « Tableau de bord » pour revenir à votre espace.</p>
      {MODULES_MISSION.map((g) => (
        <section key={g.groupe} className="modules-groupe">
          <h3>{g.groupe}</h3>
          <div className="modules-grid">
            {g.items.map(([titre, desc, href]) => (
              <a key={titre} className="module-card" href={href(m.id)}>
                <b>{titre}</b>
                <span>{desc}</span>
                <em>Ouvrir →</em>
              </a>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
