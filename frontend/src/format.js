// Montants : EUR en centimes, XOF en unités entières.
export const fmtMontant = (v, devise) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: devise, maximumFractionDigits: devise === "XOF" ? 0 : 2 })
    .format(devise === "XOF" ? v : v / 100);
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" }) : "—");
