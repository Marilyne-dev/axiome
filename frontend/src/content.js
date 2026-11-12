// Contenu de la landing page (intégré au front : le site public ne dépend d'aucune API).
// Les offres seront remplacées par les vraies offres de l'API à l'étape « abonnements ».
export const CONTENT = {
  standards: [
    { tag: "NEP", label: "Normes d'exercice professionnel" },
    { tag: "ISA", label: "200–720" },
    { tag: "IA\u00A0ACT", label: "Règl. (UE) 2024/1689" },
    { tag: "LCB-FT", label: "CMF · TRACFIN" },
    { tag: "RGPD", label: "Règl. (UE) 2016/679" },
  ],
  modules: [
    { id: "analytics", num: "01", name: "ANALYTICS", title: "Documents prêts à l'emploi",
      text: "Exploitez le FEC et la DSN pour produire analyses, papiers de travail, synthèses et supports de restitution." },
    { id: "platform", num: "02", name: "PLATEFORME", title: "Le dossier d'audit, de bout en bout",
      text: "Structurez et documentez le dossier : acceptation, planification, réalisation, finalisation — avec la conformité réglementaire intégrée." },
    { id: "link", num: "03", name: "LINK", title: "Add-in Excel pour l'audit",
      text: "Importez, organisez et référencez les justificatifs directement depuis vos papiers de travail." },
  ],
  outputs: [
    { logo: "BI", tool: "Power BI", color: "#E8B400", title: "Rapport interactif", text: "100+ pages d'analyses organisées par cycle, pensées pour les dossiers volumineux." },
    { logo: "XL", tool: "Excel", color: "#1E7145", title: "Papiers de travail", text: "Procédures automatisées et précomplétées, prêtes pour le dossier (pack WAUX)." },
    { logo: "W", tool: "Word", color: "#2B579A", title: "Revue analytique", text: "Document généré et commenté, structuré selon les exigences professionnelles (NEP 520)." },
    { logo: "P", tool: "PowerPoint", color: "#D24726", title: "Support de restitution", text: "Trame préformatée intégrant analyses et visuels clés pour standardiser la restitution." },
  ],
  faq: [
    { q: "La suite est-elle conforme aux NEP et aux normes ISA ?", a: "Oui. La méthodologie suit les Normes d'Exercice Professionnel (dont les NEP 315 et 330 révisées) et les normes ISA 200 à 720. Le référentiel est mis à jour en continu. Les conclusions et l'opinion restent celles du commissaire aux comptes." },
    { q: "Comment sont protégées les données comptables ?", a: "Les traitements respectent le RGPD : chiffrement, gestion des accès, traçabilité et durées de conservation définies. Les données restent celles du cabinet et de ses clients ; aucune réutilisation à d'autres fins." },
    { q: "Quelle est l'approche vis-à-vis de l'IA Act ?", a: "Le système est positionné comme une aide à la décision sous contrôle humain. Un module dédié classe l'usage au regard du Règlement (UE) 2024/1689 et documente les obligations applicables (transparence, journalisation, supervision humaine)." },
    { q: "Les modules sont-ils utilisables séparément ?", a: "Oui. Analytics, Plateforme et Link sont souscriptibles indépendamment ou ensemble. La suite complète ajoute le portail collaborateurs / commissaires aux comptes et la conformité réglementaire intégrée." },
    { q: "Quels formats de données sont pris en charge ?", a: "Le FEC (format A47), les balances N/N-1, les grands livres et la DSN, ainsi que les exports Excel/CSV usuels. Les livrables sont générés en Power BI, Excel, Word et PowerPoint." },
  ],
};
