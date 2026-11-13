import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import Modules from "../pages/app/missionTabs/Modules.jsx";

afterEach(() => vi.unstubAllGlobals());
const mission = { id: 7, intitule: "Audit Alpha 2025" };

describe("onglet Modules", () => {
  it("affiche tous les modules en français avec les bons liens", () => {
    const html = renderToStaticMarkup(<Modules m={mission} />);
    expect(html).toContain('href="/missions/7/vue/cycles"');
    expect(html).toContain('href="/missions/7/vue/analyse-tva"');
    expect(html).toContain("Rapprochement bancaire");
    expect(html).toContain("Audit Alpha 2025");
    expect(html).toContain("Générer en arrière-plan");
  });
  it("passe en anglais selon la langue enregistrée", () => {
    vi.stubGlobal("localStorage", { getItem: () => "en", setItem: () => {} });
    // Le contexte par défaut est français ; on vérifie ici le chargement de la préférence côté provider.
    return import("../i18n.jsx").then(({ LangProvider }) => {
      const html = renderToStaticMarkup(<LangProvider><Modules m={mission} /></LangProvider>);
      expect(html).toContain("Bank reconciliation");
      expect(html).toContain("Generate in background");
      expect(html).toContain('href="/missions/7/vue/csrd"');
    });
  });
});
