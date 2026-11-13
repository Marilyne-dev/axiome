// Catalogue des modules AXIOME rendus par le back (Jinja), accessibles depuis le front sur la même origine
// (proxy Vite, cookie de session partagé). Chaque entrée est bilingue : { fr: [titre, description], en: [...] }.

const m = (chemin, fr, en) => ({ href: (id) => `/missions/${id}/vue${chemin}`, fr, en });

export const MODULES_MISSION = [
  { groupe: { fr: "Contrôle interne & programme d'audit", en: "Internal control & audit programme" }, items: [
    m("/cycles", ["Cycles, programme d'audit et contrôle interne", "Feuilles de travail par cycle, évaluation du contrôle interne, génération du dossier Excel par cycle."],
      ["Cycles, audit programme and internal control", "Working papers per cycle, internal control assessment, Excel file generation per cycle."]),
    m("/echantillonnage", ["Échantillonnage", "Tirage d'échantillons par cycle, suivi des éléments testés et conclusions."],
      ["Sampling", "Sample selection per cycle, tracking of tested items and conclusions."]),
    m("/fraude", ["Détection de fraude (FEC)", "Import du FEC, indicateurs de fraude, loi de Benford."],
      ["Fraud detection (FEC)", "FEC import, fraud indicators, Benford's law."]),
    m("/confirmations", ["Circularisation", "Demandes de confirmation aux tiers et suivi des réponses."],
      ["Third-party confirmations", "Confirmation requests to third parties and reply tracking."]),
    m("/documents", ["GED — documents", "Dépôt, recherche plein texte et OCR des pièces du dossier."],
      ["Document management", "Upload, full-text search and OCR of file documents."]),
  ] },
  { groupe: { fr: "Vérifications et travaux spécifiques", en: "Specific checks and procedures" }, items: [
    m("/rapprochement", ["Rapprochement bancaire", "Rapprochement des relevés et du grand livre."], ["Bank reconciliation", "Reconciliation of bank statements and the general ledger."]),
    m("/balance-agee/clients", ["Balance âgée clients", "Ancienneté des créances clients."], ["Trade receivables ageing", "Ageing of trade receivables."]),
    m("/balance-agee/fournisseurs", ["Balance âgée fournisseurs", "Ancienneté des dettes fournisseurs."], ["Trade payables ageing", "Ageing of trade payables."]),
    m("/analyse-tva", ["Analyse TVA", "Cohérence entre la TVA déclarée et la comptabilité."], ["VAT analysis", "Consistency between declared VAT and the accounts."]),
    m("/cadrage-dsn", ["Cadrage DSN", "Rapprochement des déclarations sociales et de la paie."], ["Payroll (DSN) reconciliation", "Reconciliation of social filings and payroll."]),
    m("/reclassement", ["Reclassement", "Reclassement des lignes de la balance (unitaire ou en masse)."], ["Reclassification", "Reclassification of trial balance lines (single or bulk)."]),
    m("/verifications", ["Vérifications spécifiques", "Concordance et points de contrôle propres à la mission."], ["Specific verifications", "Consistency checks and control points specific to the engagement."]),
    m("/csrd", ["CSRD", "Double matérialité, points ESRS et rapport."], ["CSRD", "Double materiality, ESRS points and report."]),
    m("/fusion", ["Commissariat à la fusion", "Dossier de fusion, évaluations et rapport."], ["Merger appraisal", "Merger file, valuations and report."]),
  ] },
  { groupe: { fr: "Suivi et restitution", en: "Follow-up and reporting" }, items: [
    m("/editions", ["Journal des éditions", "Historique des rapports générés, export CSV."], ["Editions log", "History of generated reports, CSV export."]),
    m("", ["Espace de travail complet", "Vue d'ensemble de la mission rendue par le back."], ["Full workspace", "Engagement overview rendered by the back-end."]),
  ] },
];

// Modules transverses du cabinet. `role` = rôle requis pour afficher l'entrée (absent = tous).
export const MODULES_CABINET = [
  { href: "/vue/clients", icon: "users", label: { fr: "Fiche client complète", en: "Full client file" } },
  { href: "/vue/lcbft", icon: "alert", label: { fr: "LCB-FT", en: "AML-CFT" } },
  { href: "/vue/pilotage", icon: "gauge", label: { fr: "Pilotage détaillé", en: "Detailed monitoring" } },
  { href: "/vue/referentiels", icon: "folder", label: { fr: "Référentiels", en: "Frameworks" } },
  { href: "/vue/veille", icon: "folder", label: { fr: "Veille", en: "Regulatory watch" } },
  { href: "/vue/catalogue", icon: "folder", label: { fr: "Catalogue des missions", en: "Engagement catalogue" } },
  { href: "/vue/administration", icon: "users", role: "ADMIN", label: { fr: "Administration du cabinet", en: "Firm administration" } },
  { href: "/console", icon: "gauge", role: "SUPERADMIN", label: { fr: "Console éditeur", en: "Publisher console" } },
  { href: "/portail", icon: "home", role: "CLIENT", label: { fr: "Portail client", en: "Client portal" } },
];

/** Entrées du menu visibles pour une liste de rôles. */
export const modulesCabinetPour = (roles = []) => MODULES_CABINET.filter((x) => !x.role || roles.includes(x.role));
