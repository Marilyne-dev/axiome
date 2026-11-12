import { useState } from "react";

export default function PasswordField({ label, value, onChange, autoComplete, minLength, children }) {
  const [show, setShow] = useState(false);
  return (
    <label className="field">{label}
      <span className="pw">
        <input type={show ? "text" : "password"} required minLength={minLength}
          autoComplete={autoComplete} value={value} onChange={onChange} />
        <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Masquer le mot de passe" : "Afficher le mot de passe"}>
          {show ? "Masquer" : "Afficher"}
        </button>
      </span>
      {children}
    </label>
  );
}

export function Strength({ value }) {
  const score = [value.length >= 8, value.length >= 12, /[a-z]/.test(value) && /[A-Z]/.test(value),
    /\d/.test(value), /[^A-Za-z0-9]/.test(value)].filter(Boolean).length;
  const level = value ? Math.min(4, Math.max(1, score - (value.length < 8 ? 1 : 0))) : 0;
  const names = ["", "Faible", "Moyen", "Bon", "Excellent"];
  return (
    <span className={`strength s${level}`}>
      <span className="segs">{[1, 2, 3, 4].map((n) => <i key={n} className={n <= level ? "on" : ""} />)}</span>
      <em>{names[level]}</em>
    </span>
  );
}
