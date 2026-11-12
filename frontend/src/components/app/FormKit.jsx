import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/* Icônes de formulaire (trait fin, même style que le reste de l'espace). */
const P = {
  building: <><path d="M4 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16M14 9h5a1 1 0 0 1 1 1v11M3 21h18" /><path d="M8 8h2M8 12h2M8 16h2" /></>,
  hash: <path d="M5 9h14M4 15h14M10 4L8 20M16 4l-2 16" />,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.8 3 2.8 15 0 18M12 3c-2.8 3-2.8 15 0 18" /></>,
  tag: <><path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z" /><circle cx="8" cy="8" r="1.4" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2.5" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 13h18" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  file: <><path d="M6 3h8l5 5v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" /><path d="M14 3v5h5M8 13h8M8 17h5" /></>,
  scale: <><path d="M12 3v18M6 21h12M5 7h14" /><path d="M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15" rx="2.5" /><path d="M3.5 10h17M8 3v4M16 3v4" /></>,
  coin: <><circle cx="12" cy="12" r="9" /><path d="M14.5 9.2c-.6-.8-1.5-1.2-2.6-1.2-1.5 0-2.6.8-2.6 2s1 1.7 2.7 2c1.6.3 2.7.8 2.7 2s-1.1 2-2.7 2c-1.2 0-2.2-.5-2.8-1.3M12 6v2M12 16v2" /></>,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  sparkle: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  shield: <><path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5" /></>,
  download: <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />,
  plus: <path d="M12 5v14M5 12h14" />,
  flag: <path d="M5 21V4M5 4h11l-2 4 2 4H5" />,
  warn: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18v.5" /></>,
};
export const FIcon = ({ n, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{P[n]}</svg>
);

/* Champ à étiquette flottante, icône, validation visuelle. */
export function Input({ label, icon, hint, full, className = "", ...rest }) {
  return (
    <label className={`ff${full ? " full" : ""} ${className}`}>
      {icon && <span className="ff-ico"><FIcon n={icon} /></span>}
      <input placeholder=" " {...rest} />
      <span className="ff-label">{label}{rest.required ? " *" : ""}</span>
      <span className="ff-ok"><FIcon n="check" size={16} /></span>
      {hint && <small className="ff-hint">{hint}</small>}
    </label>
  );
}

export function Select({ label, icon, hint, full, children, ...rest }) {
  return (
    <label className={`ff ff-select${full ? " full" : ""}`}>
      {icon && <span className="ff-ico"><FIcon n={icon} /></span>}
      <select {...rest}>{children}</select>
      <span className="ff-label">{label}{rest.required ? " *" : ""}</span>
      <span className="ff-caret" />
      {hint && <small className="ff-hint">{hint}</small>}
    </label>
  );
}

/* Choix rapide en pastilles (ex. devises). */
export function Chips({ value, options, onPick }) {
  return <div className="chips">{options.map((o) => <button type="button" key={o} className={value === o ? "on" : ""} onClick={() => onPick(o)}>{o}</button>)}</div>;
}

export function Textarea({ label, hint, full, ...rest }) {
  return (
    <label className={`ff ff-area${full ? " full" : ""}`}>
      <textarea placeholder=" " rows={4} {...rest} />
      <span className="ff-label">{label}{rest.required ? " *" : ""}</span>
      {hint && <small className="ff-hint">{hint}</small>}
    </label>
  );
}

/* Interrupteur élégant (oui / non). */
export const Switch = ({ checked, onChange, label, hint, tone = "ok", disabled }) => (
  <button type="button" role="switch" aria-checked={checked} disabled={disabled} className={`sw sw-${tone}${checked ? " on" : ""}`} onClick={() => onChange(!checked)}>
    <span className="sw-track"><i /></span><span className="sw-txt"><b>{label}</b>{hint && <small>{hint}</small>}</span>
  </button>
);

/* Choix segmenté : options = [[valeur, libellé], ...]. */
export const Segmented = ({ value, options, onPick, label }) => (
  <div className="seg-wrap">{label && <span className="seg-label">{label}</span>}
    <div className="seg" role="radiogroup">{options.map(([v, l]) => <button type="button" role="radio" aria-checked={value === v} key={v} className={value === v ? "on" : ""} onClick={() => onPick(v)}>{l}</button>)}</div></div>
);

export const Section = ({ icon, title, sub, className = "", children }) => (
  <fieldset className={`fsec ${className}`}>
    <legend><span className="fsec-ico"><FIcon n={icon} size={16} /></span><span><b>{title}</b>{sub && <small>{sub}</small>}</span></legend>
    <div className="fgrid">{children}</div>
  </fieldset>
);

export const FormAlert = ({ children }) => children ? <div className="falert" role="alert"><span>!</span>{children}</div> : null;

export const SubmitBtn = ({ busy, form, children, busyText = "Enregistrement…" }) => (
  <button type="submit" form={form} className="btn-submit" disabled={busy}>
    {busy ? <><i className="spin" />{busyText}</> : <>{children}<FIcon n="arrow" size={17} /></>}
  </button>
);

/* Panneau latéral élégant : en-tête illustré, corps défilant, pied fixe. */
export function Drawer({ open, onClose, title, subtitle, tone = "blue", icon = "sparkle", size = "md", children, footer }) {
  const ref = useRef(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && close.current();
    document.addEventListener("keydown", k);
    const prev = document.body.style.overflow; document.body.style.overflow = "hidden";
    setTimeout(() => ref.current?.querySelector("input,select")?.focus(), 350);
    return () => { document.removeEventListener("keydown", k); document.body.style.overflow = prev; };
  }, [open]);
  if (!open) return null;
  return createPortal(
    <div className="drawer-root">
      <div className="drawer-scrim" onClick={onClose} />
      <aside className={`drawer d-${tone} sz-${size}`} ref={ref} role="dialog" aria-modal="true" aria-label={title}>
        <header className="drawer-head">
          <svg className="dh-art" viewBox="0 0 300 120" fill="none" aria-hidden="true">
            <circle className="dh-c1" cx="250" cy="30" r="46" fill="#fff" opacity=".10" /><circle className="dh-c2" cx="40" cy="100" r="34" fill="#E9C84A" opacity=".25" />
            <path d="M150 90l30-26 26 14 38-40" stroke="#fff" strokeOpacity=".55" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="244" cy="38" r="5" fill="#fff" />
          </svg>
          <button type="button" className="drawer-x" onClick={onClose} aria-label="Fermer"><FIcon n="close" /></button>
          <div className="dh-ico"><FIcon n={icon} size={22} /></div>
          <div className="dh-txt"><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
        </header>
        <div className="drawer-body">{children}</div>
        {footer && <footer className="drawer-foot">{footer}</footer>}
      </aside>
    </div>,
    document.body
  );
}

/* Notification de confirmation. */
export function useToast() {
  const [t, setT] = useState(null);
  const show = useCallback((msg) => { setT(msg); setTimeout(() => setT(null), 3600); }, []);
  const node = t ? <div className="toast" role="status"><span><FIcon n="check" size={16} /></span>{t}</div> : null;
  return [node, show];
}
