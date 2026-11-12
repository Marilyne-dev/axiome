// Illustrations SVG animées (aucune image externe)
const org = (x, y) => ({ transformOrigin: `${x}px ${y}px` });

export function AuthScene() {
  return (
    <svg className="auth-scene" viewBox="0 0 440 400" fill="none">
      <defs>
        <linearGradient id="sh" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#2F5BFF" /><stop offset="1" stopColor="#7C5CFC" /></linearGradient>
        <radialGradient id="gl"><stop offset="0" stopColor="#2F5BFF" stopOpacity=".55" /><stop offset="1" stopColor="#2F5BFF" stopOpacity="0" /></radialGradient>
      </defs>
      <circle className="glow-pulse" cx="220" cy="200" r="130" fill="url(#gl)" />
      <g className="spin" style={org(220, 200)}>
        <circle cx="220" cy="200" r="150" stroke="#fff" strokeOpacity=".18" strokeDasharray="4 10" />
        <circle cx="370" cy="200" r="8" fill="#C9A227" /><circle cx="70" cy="200" r="5" fill="#fff" fillOpacity=".7" />
      </g>
      <g className="spin rev" style={{ ...org(220, 200), animationDuration: "16s" }}>
        <circle cx="220" cy="200" r="108" stroke="#fff" strokeOpacity=".14" strokeDasharray="2 8" />
        <circle cx="220" cy="92" r="6" fill="#7C5CFC" /><circle cx="328" cy="200" r="4" fill="#fff" fillOpacity=".8" />
      </g>
      <path d="M220 118 L288 144 V206 C288 246 260 274 220 288 C180 274 152 246 152 206 V144 Z" fill="url(#sh)" />
      <path d="M220 118 L288 144 V206 C288 246 260 274 220 288" fill="#fff" fillOpacity=".08" />
      <path className="check-loop" d="M190 206 l22 22 l42 -48" stroke="#fff" strokeWidth="11" strokeLinecap="round"
        strokeLinejoin="round" pathLength="1" />
      <g className="fl-a">
        <rect x="34" y="66" width="122" height="78" rx="14" fill="#fff" fillOpacity=".95" />
        <rect x="48" y="82" width="56" height="7" rx="3.5" fill="#0B1B2E" fillOpacity=".75" />
        <rect x="48" y="98" width="88" height="5" rx="2.5" fill="#94A8C0" /><rect x="48" y="110" width="70" height="5" rx="2.5" fill="#94A8C0" />
        <rect x="48" y="124" width="30" height="8" rx="4" fill="#C9A227" />
      </g>
      <g className="fl-b">
        <rect x="300" y="96" width="108" height="62" rx="14" fill="#fff" fillOpacity=".95" />
        <circle cx="326" cy="127" r="11" fill="#1E9E5A" /><path d="M321 127l4 4 7-8" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" fill="none" />
        <rect x="344" y="116" width="50" height="6" rx="3" fill="#0B1B2E" fillOpacity=".75" /><rect x="344" y="130" width="36" height="5" rx="2.5" fill="#94A8C0" />
      </g>
      <g className="fl-c">
        <rect x="60" y="272" width="130" height="86" rx="14" fill="#fff" fillOpacity=".95" />
        {[22, 40, 30, 54, 44].map((h, i) => (
          <rect key={i} className="gbar" x={76 + i * 22} y={338 - h} width="13" height={h} rx="3" fill={i === 3 ? "#C9A227" : "#2F5BFF"}
            style={{ animationDelay: `${0.4 + i * 0.15}s` }} />
        ))}
      </g>
      <g className="fl-a" style={{ animationDelay: "-2s" }}>
        <rect x="290" y="290" width="112" height="56" rx="14" fill="#fff" fillOpacity=".95" />
        <path className="line-loop" d="M304 330 C320 318 330 332 346 316 S376 306 390 300" stroke="#7C5CFC" strokeWidth="3.4" strokeLinecap="round" pathLength="1" />
      </g>
      {[[110, 40], [400, 232], [24, 214], [250, 366], [372, 60]].map(([x, y], i) => (
        <path key={i} className="twinkle" style={{ animationDelay: `${i * 0.6}s` }}
          d={`M${x} ${y - 9} L${x + 2.5} ${y - 2.5} L${x + 9} ${y} L${x + 2.5} ${y + 2.5} L${x} ${y + 9} L${x - 2.5} ${y + 2.5} L${x - 9} ${y} L${x - 2.5} ${y - 2.5}Z`} fill="#C9A227" />
      ))}
    </svg>
  );
}

function Clock() {
  return (
    <svg viewBox="0 0 200 170" fill="none">
      <circle className="glow-pulse" cx="100" cy="85" r="70" fill="#2F5BFF" fillOpacity=".18" />
      <circle cx="100" cy="85" r="56" fill="#fff" fillOpacity=".95" />
      {Array.from({ length: 12 }, (_, i) => (
        <line key={i} x1="100" y1="35" x2="100" y2={i % 3 === 0 ? 43 : 39} stroke="#0B1B2E" strokeOpacity=".5" strokeWidth="2.4"
          strokeLinecap="round" transform={`rotate(${i * 30} 100 85)`} />
      ))}
      <path className="spin" d="M100 85 L100 45" stroke="#2F5BFF" strokeWidth="4" strokeLinecap="round" style={{ ...org(100, 85), animationDuration: "6s" }} />
      <path className="spin" d="M100 85 L100 62" stroke="#0B1B2E" strokeWidth="5" strokeLinecap="round" style={{ ...org(100, 85), animationDuration: "72s" }} />
      <circle cx="100" cy="85" r="5" fill="#C9A227" />
      <path className="spin rev" d="M100 22 A63 63 0 0 1 163 85" stroke="#C9A227" strokeWidth="3" strokeLinecap="round" strokeDasharray="4 8" style={{ ...org(100, 85), animationDuration: "9s" }} />
    </svg>
  );
}

function Scan() {
  return (
    <svg viewBox="0 0 200 170" fill="none">
      <rect x="40" y="18" width="100" height="134" rx="12" fill="#fff" fillOpacity=".95" />
      {[40, 58, 76, 94, 112].map((y, i) => <rect key={y} x="56" y={y} width={i === 2 ? 68 : 52 + (i % 2) * 24} height="7" rx="3.5" fill={i === 2 ? "#E0544A" : "#C5D2E3"} className={i === 2 ? "blink" : ""} />)}
      <g className="scan-move">
        <circle cx="96" cy="78" r="26" fill="#2F5BFF" fillOpacity=".14" stroke="#2F5BFF" strokeWidth="5" />
        <path d="M115 97 L138 120" stroke="#2F5BFF" strokeWidth="8" strokeLinecap="round" />
      </g>
      <circle className="pulse-ring" cx="158" cy="38" r="8" fill="#C9A227" /><path d="M154 38l3 3 5-6" stroke="#0B1B2E" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function ShieldIllu() {
  return (
    <svg viewBox="0 0 200 170" fill="none">
      <circle className="glow-pulse" cx="100" cy="85" r="68" fill="#7C5CFC" fillOpacity=".22" />
      <g className="spin" style={{ ...org(100, 85), animationDuration: "18s" }}>
        <circle cx="100" cy="85" r="64" stroke="#fff" strokeOpacity=".3" strokeDasharray="3 9" />
        <circle cx="164" cy="85" r="6" fill="#C9A227" />
      </g>
      <path d="M100 34 L140 49 V86 C140 112 124 128 100 137 C76 128 60 112 60 86 V49 Z" fill="url(#sh2)" />
      <defs><linearGradient id="sh2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#7C5CFC" /><stop offset="1" stopColor="#2F5BFF" /></linearGradient></defs>
      <path className="check-loop" d="M80 86 l14 14 l28 -30" stroke="#fff" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" pathLength="1" />
    </svg>
  );
}

const WHY = [
  { Art: Clock, t: "Un temps précieux regagné", d: "Les procédures précomplétées et les analyses automatisées libèrent vos équipes des tâches répétitives." },
  { Art: Scan, t: "Des anomalies qui ne passent plus", d: "La détection par Machine Learning met en évidence les écritures atypiques à investiguer en priorité." },
  { Art: ShieldIllu, t: "Une conformité intégrée", d: "NEP, IA Act, LCB-FT et RGPD sont évalués et tracés directement dans le dossier." },
];

export const Why = () => (
  <section className="why" id="pourquoi">
    <WhyBg />
    <div className="wrap">
      <div className="sec-head">
        <div className="eyebrow">Pourquoi AXIOME</div>
        <h2>L'audit, plus rapide, plus sûr, plus serein.</h2>
        <p>Trois bénéfices concrets pour votre cabinet, dès la première mission.</p>
      </div>
      <div className="why-grid">
        {WHY.map(({ Art, t, d }) => (
          <div className="why-card" key={t}><Art /><h3>{t}</h3><p>{d}</p></div>
        ))}
      </div>
    </div>
  </section>
);

import Background from "./Background.jsx";
function WhyBg() { return <Background variant="dark" />; }
