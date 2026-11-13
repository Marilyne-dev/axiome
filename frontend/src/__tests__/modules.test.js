import { describe, expect, it } from "vitest";
import { MODULES_CABINET, MODULES_MISSION, modulesCabinetPour } from "../modules.js";

const items = MODULES_MISSION.flatMap((g) => g.items);

describe("catalogue des modules", () => {
  it("chaque module de mission est bilingue (titre + description)", () => {
    for (const it of items) for (const l of ["fr", "en"]) {
      expect(it[l].length).toBe(2);
      expect(it[l][0].trim().length > 0 && it[l][1].trim().length > 0).toBe(true);
    }
  });
  it("les liens pointent vers les écrans du back pour la mission demandée", () => {
    const liens = items.map((it) => it.href(12));
    expect(liens).toContain("/missions/12/vue/cycles");
    expect(liens).toContain("/missions/12/vue/balance-agee/clients");
    expect(liens).toContain("/missions/12/vue");
    for (const l of liens) expect(l.startsWith("/missions/12/vue")).toBe(true);
  });
  it("pas de module en double", () => {
    const hrefs = items.map((it) => it.href(1));
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
  it("le menu du cabinet filtre selon les rôles", () => {
    const simple = modulesCabinetPour(["AUDITEUR"]).map((m) => m.href);
    expect(simple).toContain("/vue/lcbft");
    expect(simple).not.toContain("/console");
    expect(simple).not.toContain("/vue/administration");
    expect(modulesCabinetPour(["SUPERADMIN"]).map((m) => m.href)).toContain("/console");
    expect(modulesCabinetPour(["ADMIN"]).map((m) => m.href)).toContain("/vue/administration");
    expect(modulesCabinetPour(["CLIENT"]).map((m) => m.href)).toContain("/portail");
  });
  it("chaque entrée du menu a un libellé FR et EN", () => {
    for (const m of MODULES_CABINET) expect(Boolean(m.label.fr && m.label.en)).toBe(true);
  });
});
