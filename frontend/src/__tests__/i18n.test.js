import { describe, expect, it } from "vitest";
import { DICT, pick, translate } from "../i18n.jsx";

describe("i18n", () => {
  it("le français et l'anglais ont exactement les mêmes clés", () => {
    expect(Object.keys(DICT.en).sort()).toEqual(Object.keys(DICT.fr).sort());
  });
  it("aucune traduction vide", () => {
    for (const lang of ["fr", "en"]) for (const [k, v] of Object.entries(DICT[lang])) expect(v.trim().length > 0, `${lang}:${k}`).toBe(true);
  });
  it("traduit et remplace les variables", () => {
    expect(translate("en", "nav.logout")).toBe("Sign out");
    expect(translate("fr", "mod.intro", { mission: "Alpha" })).toContain("« Alpha »");
    expect(translate("en", "mod.intro", { mission: "Alpha" })).toContain("“Alpha”");
  });
  it("retombe sur la clé si elle est inconnue, et sur le français si la langue est inconnue", () => {
    expect(translate("fr", "cle.inexistante")).toBe("cle.inexistante");
    expect(translate("de", "nav.logout")).toBe("Se déconnecter");
  });
  it("pick choisit la langue avec repli français", () => {
    expect(pick({ fr: "a", en: "b" }, "en")).toBe("b");
    expect(pick({ fr: "a" }, "en")).toBe("a");
  });
});
