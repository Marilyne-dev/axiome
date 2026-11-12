import { useEffect, useState } from "react";

/* Illustration animée de la bannière : dossier d'audit, courbe, bouclier, particules. */
export function HeroScene() {
  return (
    <svg className="hero-scene" viewBox="0 0 420 260" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="hsG1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".95" /><stop offset="1" stopColor="#DCE6FF" stopOpacity=".9" /></linearGradient>
        <linearGradient id="hsG2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#7C5CFC" /><stop offset="1" stopColor="#2F5BFF" /></linearGradient>
        <linearGradient id="hsG3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#E9C84A" /><stop offset="1" stopColor="#C9A227" /></linearGradient>
      </defs>
      <circle className="hs-orb o1" cx="70" cy="60" r="46" fill="#fff" opacity=".07" />
      <circle className="hs-orb o2" cx="360" cy="40" r="30" fill="#E9C84A" opacity=".22" />
      <circle className="hs-orb o3" cx="380" cy="210" r="54" fill="#fff" opacity=".06" />
      <g className="hs-float a">
        <rect x="70" y="52" width="190" height="150" rx="18" fill="url(#hsG1)" />
        <rect x="88" y="72" width="70" height="9" rx="4.5" fill="#2F5BFF" opacity=".85" />
        <rect x="88" y="90" width="120" height="6" rx="3" fill="#9DB1E6" />
        <path className="hs-line" d="M90 176 L116 150 L140 160 L170 122 L200 134 L238 98" stroke="url(#hsG2)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle className="hs-dot" cx="238" cy="98" r="6" fill="#7C5CFC" />
        <g opacity=".9">{[0, 1, 2, 3, 4].map((i) => <rect key={i} className="hs-bar" style={{ animationDelay: `${.5 + i * .12}s` }} x={96 + i * 14} y={196 - [14, 22, 17, 30, 26][i]} width="8" height={[14, 22, 17, 30, 26][i]} rx="2.5" fill="#C9D6F7" />)}</g>
      </g>
      <g className="hs-float b">
        <rect x="236" y="116" width="128" height="86" rx="16" fill="#0B1533" opacity=".86" />
        <rect x="236" y="116" width="128" height="86" rx="16" stroke="#fff" strokeOpacity=".22" />
        <circle cx="262" cy="144" r="13" fill="#17A673" />
        <path d="M255.5 144.5l4.5 4.5 8-9" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="282" y="136" width="64" height="7" rx="3.5" fill="#fff" opacity=".85" />
        <rect x="282" y="150" width="44" height="6" rx="3" fill="#fff" opacity=".4" />
        <rect x="252" y="172" width="96" height="8" rx="4" fill="#fff" opacity=".14" />
        <rect className="hs-prog" x="252" y="172" width="64" height="8" rx="4" fill="url(#hsG3)" />
      </g>
      <g className="hs-float c">
        <path d="M312 38l34 12v30c0 20-14 34-34 42-20-8-34-22-34-42V50z" fill="url(#hsG2)" stroke="#fff" strokeOpacity=".5" strokeWidth="2" />
        <path d="M298 80l10 10 20-22" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      {[[40, 150], [44, 210], [250, 30], [398, 120], [20, 100]].map(([x, y], i) => <circle key={i} className="hs-spark" style={{ animationDelay: `${i * .6}s` }} cx={x} cy={y} r="3" fill="#fff" />)}
    </svg>
  );
}

/* Donut des risques par niveau (trait animé). */
const COLORS = { critique: "#DC3B4B", eleve: "#EA7B1E", modere: "#E0A100", faible: "#17A673" };
export function RiskDonut({ data, order }) {
  const total = order.reduce((a, [k]) => a + (data[k] || 0), 0);
  const [on, setOn] = useState(false);
  useEffect(() => { const t = setTimeout(() => setOn(true), 120); return () => clearTimeout(t); }, []);
  const R = 62, C = 2 * Math.PI * R;
  let acc = 0;
  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 160 160" className="donut" role="img" aria-label="Répartition des risques">
        <circle cx="80" cy="80" r={R} fill="none" stroke="#EEF2F8" strokeWidth="18" />
        {total > 0 && order.map(([k]) => {
          const n = data[k] || 0; if (!n) return null;
          const len = (n / total) * C, off = acc; acc += len;
          return <circle key={k} cx="80" cy="80" r={R} fill="none" stroke={COLORS[k]} strokeWidth="18" strokeLinecap="butt"
            strokeDasharray={`${on ? Math.max(len - 3, 0) : 0} ${C}`} strokeDashoffset={-off}
            transform="rotate(-90 80 80)" style={{ transition: "stroke-dasharray 1.1s cubic-bezier(.2,.8,.2,1)" }} />;
        })}
        <text x="80" y="78" textAnchor="middle" className="donut-n">{total}</text>
        <text x="80" y="98" textAnchor="middle" className="donut-l">risque{total > 1 ? "s" : ""}</text>
      </svg>
      <ul className="donut-leg">
        {order.map(([k, label]) => <li key={k}><i style={{ background: COLORS[k] }} />{label}<b>{data[k] || 0}</b></li>)}
      </ul>
    </div>
  );
}

/* Anneau de progression (quotas, avancement). */
export function Ring({ value, max, size = 92, color = "#2F5BFF", children }) {
  const [on, setOn] = useState(false);
  useEffect(() => { const t = setTimeout(() => setOn(true), 150); return () => clearTimeout(t); }, []);
  const R = 38, C = 2 * Math.PI * R, p = max ? Math.min(1, value / max) : 0;
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg viewBox="0 0 92 92"><circle cx="46" cy="46" r={R} fill="none" stroke="#EEF2F8" strokeWidth="9" />
        <circle cx="46" cy="46" r={R} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" transform="rotate(-90 46 46)"
          strokeDasharray={`${on ? p * C : 0} ${C}`} style={{ transition: "stroke-dasharray 1.1s cubic-bezier(.2,.8,.2,1)" }} /></svg>
      <div className="ring-in">{children}</div>
    </div>
  );
}
