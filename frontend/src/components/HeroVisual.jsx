import CountUp from "./CountUp.jsx";

const LINE = "M0 130 C40 122 62 88 100 96 S160 58 200 68 S270 30 310 40 S370 22 400 12";

export default function HeroVisual() {
  const bars = [46, 72, 58, 90, 64, 82];
  return (
    <div className="hv-wrap">
      <div className="hv-chip c1"><i className="ok">✓</i> FEC importé · 1,2 M écritures</div>
      <div className="hv-chip c2"><i className="warn">!</i> 3 écarts atypiques</div>
      <div className="hv-chip c3"><i className="ok">✓</i> NEP 315 · à jour</div>

      <div className="mock hv">
        <div className="mock-bar"><span className="dots"><i /><i /><i /></span>
          <span className="ttl">AXIOME · Mission 2026 · Revue analytique</span></div>
        <div className="hv-body">
          <div className="hv-kpis">
            <div className="kpi"><span>Écritures analysées</span><b><CountUp to={1284560} /></b></div>
            <div className="kpi"><span>Anomalies détectées</span><b className="red"><CountUp to={37} /></b></div>
            <div className="kpi"><span>Procédures complétées</span><b><CountUp to={112} />/120</b></div>
          </div>

          <div className="hv-chart">
            <div className="hv-t">Chiffre d'affaires mensuel</div>
            <svg viewBox="0 0 400 160" preserveAspectRatio="none">
              <defs>
                <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#2F5BFF" stopOpacity=".28" /><stop offset="1" stopColor="#2F5BFF" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[40, 80, 120].map((y) => <line key={y} x1="0" x2="400" y1={y} y2={y} stroke="#E5EBF3" />)}
              <path className="area" d={`${LINE} L400 160 L0 160 Z`} fill="url(#ga)" />
              <path className="line" d={LINE} pathLength="1" fill="none" stroke="#2F5BFF" strokeWidth="3" strokeLinecap="round" />
              <circle className="pulse" cx="100" cy="96" r="5" fill="#E0544A" />
              <circle className="pulse d2" cx="310" cy="40" r="5" fill="#E0A100" />
            </svg>
          </div>

          <div className="hv-side">
            <div className="donut">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="36" fill="none" stroke="#EAF1FF" strokeWidth="12" />
                <circle className="ring" cx="50" cy="50" r="36" fill="none" stroke="#C9A227" strokeWidth="12"
                  strokeLinecap="round" pathLength="1" strokeDasharray="1" transform="rotate(-90 50 50)" />
              </svg>
              <b>93 %</b>
            </div>
            <div className="bars">
              {bars.map((h, i) => <i key={i} style={{ height: `${h}%`, animationDelay: `${1.6 + i * 0.12}s` }} />)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
