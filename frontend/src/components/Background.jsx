// Fond animé réutilisable : blobs, grille, icônes flottantes (parallaxe), particules
const ICONS = {
  doc: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 12h6M9 16h6" /></>,
  chart: <path d="M4 20V10M10 20V4M16 20v-8M22 20H2" />,
  shield: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5" />,
  check: <><circle cx="12" cy="12" r="9" /><path d="M8 12.5l3 3 5-6" /></>,
  search: <><circle cx="11" cy="11" r="6" /><path d="M20 20l-4.5-4.5" /></>,
  coin: <><circle cx="12" cy="12" r="9" /><path d="M12 7v10M9.5 9.5h4a1.8 1.8 0 010 3.6h-3a1.8 1.8 0 000 3.6h4.3" /></>,
};
// [icône, left %, top %, taille px, durée s, délai s, facteur parallaxe]
const FLOATERS = [
  ["doc", 6, 14, 46, 9, 0, -0.06], ["chart", 88, 10, 52, 11, -2, -0.1], ["shield", 14, 62, 54, 10, -4, -0.08],
  ["check", 80, 58, 42, 8, -1, -0.12], ["search", 48, 8, 40, 12, -5, -0.05], ["coin", 92, 82, 44, 9, -3, -0.09],
  ["doc", 36, 84, 38, 13, -6, -0.07], ["chart", 62, 74, 36, 10, -7, -0.11], ["shield", 70, 22, 34, 12, -2.5, -0.04],
];
const DOTS = Array.from({ length: 22 }, (_, i) => ({
  left: (i * 37) % 100, size: 3 + (i % 4) * 2, dur: 14 + (i % 7) * 3, delay: -(i * 1.7),
}));

export default function Background({ variant = "light" }) {
  return (
    <div className={`bgfx ${variant}`} aria-hidden="true">
      <i className="bl b1" /><i className="bl b2" /><i className="bl b3" /><i className="bgrid" />
      {FLOATERS.map(([ic, l, t, s, d, dl, p], i) => (
        <span className="fl" key={i} style={{ left: `${l}%`, top: `${t}%`, "--p": p }}>
          <svg className="fli" viewBox="0 0 24 24" width={s} height={s} fill="none" stroke="currentColor"
            strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
            style={{ animationDuration: `${d}s`, animationDelay: `${dl}s` }}>{ICONS[ic]}</svg>
        </span>
      ))}
      {DOTS.map((o, i) => (
        <i className="dot" key={i} style={{ left: `${o.left}%`, width: o.size, height: o.size,
          animationDuration: `${o.dur}s`, animationDelay: `${o.delay}s` }} />
      ))}
    </div>
  );
}
