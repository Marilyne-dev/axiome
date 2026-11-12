import logo from "../assets/axiome_logo.png";

/** Logo officiel AXIOME. `pill` ajoute un fond blanc pour les zones sombres. */
export default function Logo({ height = 40, pill = false }) {
  return (
    <img src={logo} alt="AXIOME — Piloter aujourd'hui, réussir demain"
      className={`brand-logo${pill ? " pill" : ""}`} style={{ height }} />
  );
}
