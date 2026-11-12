import { useEffect, useRef } from "react";

const SEL = ".sec-head, .mod, .out, .d-text, .d-media, .pcard, .steps, .plan, .qa, .cta, .stat, .pstep, .hv-wrap, .why-card";

export default function Fx() {
  const bar = useRef(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const onScroll = () => {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight || 1;
      if (!reduce) h.style.setProperty("--sy", h.scrollTop);
      if (bar.current) bar.current.style.transform = `scaleX(${h.scrollTop / max})`;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    if (reduce) return () => window.removeEventListener("scroll", onScroll);

    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const el = e.target;
        el.classList.add("in");
        io.unobserve(el);
        // Après l'animation, on rend la main au CSS d'origine (survols, etc.)
        setTimeout(() => {
          el.classList.remove("reveal", "in", "from-l", "from-r", "zoom");
          el.style.transitionDelay = "";
        }, 1300);
      });
    }, { threshold: 0.12 });

    document.querySelectorAll(SEL).forEach((el) => {
      const idx = Math.min([...el.parentElement.children].indexOf(el), 5);
      el.classList.add("reveal");
      if (el.matches(".d-text")) el.classList.add("from-l");
      if (el.matches(".d-media")) el.classList.add("from-r");
      if (el.matches(".cta, .hv-wrap")) el.classList.add("zoom");
      el.style.transitionDelay = `${idx * 100}ms`;
      io.observe(el);
    });
    return () => { io.disconnect(); window.removeEventListener("scroll", onScroll); };
  }, []);

  return <div className="progress" ref={bar} />;
}
