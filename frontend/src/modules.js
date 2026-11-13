// Catalogue des modules AXIOME rendus par le back (Jinja) et accessibles depuis le front.
// Ces écrans sont servis sur la même origine grâce au proxy Vite (cookie de session partagé).

// Modules rattachés à une mission : lien = /missions/{id}/vue/...
export const MODULES_MISSION = [
  { groupe: "Contrôle interne & programme d'audit", items: [
    ["Cycles, programme d'audit et contrôle interne", "Feuilles de travail par cycle, évaluation du contrôle interne, génération du dossier Excel par cycle.", (id) => `/missions/${id}/vue/cycles`],
    ["Échantillonnage", "Tirage d'échantillons par cycle, suivi des éléments testés et conclusions.", (id) => `/missions/${id}/vue/echantillonnage`],
    ["Détection de fraude (FEC)", "Import du FEC, indicateurs de fraude, loi de Benford.", (id) => `/missions/${id}/vue/fraude`],
    ["Circularisation", "Demandes de confirmation aux tiers et suivi des réponses.", (id) => `/missions/${id}/vue/confirmations`],
    ["GED — documents", "Dépôt, recherche plein texte et OCR des pièces du dossier.", (id) => `/missions/${id}/vue/documents`],
  ] },
  { groupe: "Vérifications et travaux spécifiques", items: [
    ["Rapprochement bancaire", "Rapprochement des relevés et du grand livre.", (id) => `/missions/${id}/vue/rapprochement`],
    ["Balance âgée clients", "Ancienneté des créances clients.", (id) => `/missions/${id}/vue/balance-agee/clients`],
    ["Balance âgée fournisseurs", "Ancienneté des dettes fournisseurs.", (id) => `/missions/${id}/vue/balance-agee/fournisseurs`],
    ["Analyse TVA", "Cohérence entre la TVA déclarée et la comptabilité.", (id) => `/missions/${id}/vue/analyse-tva`],
    ["Cadrage DSN", "Rapprochement des déclarations sociales et de la paie.", (id) => `/missions/${id}/vue/cadrage-dsn`],
    ["Reclassement", "Reclassement des lignes de la balance (unitaire ou en masse).", (id) => `/missions/${id}/vue/reclassement`],
    ["Vérifications spécifiques", "Concordance et points de contrôle propres à la mission.", (id) => `/missions/${id}/vue/verifications`],
    ["CSRD", "Double matérialité, points ESRS et rapport.", (id) => `/missions/${id}/vue/csrd`],
    ["Commissariat à la fusion", "Dossier de fusion, évaluations et rapport.", (id) => `/missions/${id}/vue/fusion`],
  ] },
  { groupe: "Suivi et restitution", items: [
    ["Journal des éditions", "Historique des rapports générés, export CSV.", (id) => `/missions/${id}/vue/editions`],
    ["Espace de travail complet", "Vue d'ensemble de la mission rendue par le back.", (id) => `/missions/${id}/vue`],
  ] },
];

// Modules transverses du cabinet : lien absolu. `role` = rôle requis pour afficher l'entrée (absent = tous).
export const MODULES_CABINET = [
  { label: "Fiche client complète", href: "/vue/clients", icon: "users" },
  { label: "LCB-FT", href: "/vue/lcbft", icon: "alert" },
  { label: "Pilotage détaillé", href: "/vue/pilotage", icon: "gauge" },
  { label: "Référentiels", href: "/vue/referentiels", icon: "folder" },
  { label: "Veille", href: "/vue/veille", icon: "folder" },
  { label: "Catalogue des missions", href: "/vue/catalogue", icon: "folder" },
  { label: "Administration du cabinet", href: "/vue/administration", icon: "users", role: "ADMIN" },
  { label: "Console éditeur", href: "/console", icon: "gauge", role: "SUPERADMIN" },
  { label: "Portail client", href: "/portail", icon: "home", role: "CLIENT" },
];
