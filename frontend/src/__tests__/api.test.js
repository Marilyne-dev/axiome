import { afterEach, describe, expect, it, vi } from "vitest";
import { getMissions, setSession, telechargerTache } from "../api.js";

const rep = (status, body, headers = {}) => ({
  ok: status >= 200 && status < 300, status,
  headers: { get: (k) => headers[k] ?? null },
  json: async () => body, blob: async () => "BLOB",
});

afterEach(() => { vi.unstubAllGlobals(); setSession({ access: null, refresh: null, onChange: () => {}, onExpired: () => {} }); });

describe("client API", () => {
  it("envoie le jeton d'accès dans l'en-tête Authorization", async () => {
    const f = vi.fn(async () => rep(200, [{ id: 1 }])); vi.stubGlobal("fetch", f);
    setSession({ access: "tok" });
    expect(await getMissions()).toEqual([{ id: 1 }]);
    expect(f.mock.calls[0][0]).toBe("/api/espace/missions");
    expect(f.mock.calls[0][1].headers.Authorization).toBe("Bearer tok");
  });
  it("sur 401, rafraîchit le jeton une fois puis rejoue la requête", async () => {
    const appels = [];
    vi.stubGlobal("fetch", vi.fn(async (url, opts) => {
      appels.push(url);
      if (url === "/api/auth/refresh") return rep(200, { access_token: "neuf", refresh_token: "r2" });
      return opts.headers.Authorization === "Bearer neuf" ? rep(200, ["ok"]) : rep(401, { detail: "expiré" });
    }));
    const onChange = vi.fn();
    setSession({ access: "vieux", refresh: "r1", onChange });
    expect(await getMissions()).toEqual(["ok"]);
    expect(appels).toEqual(["/api/espace/missions", "/api/auth/refresh", "/api/espace/missions"]);
    expect(onChange).toHaveBeenCalledWith({ access: "neuf", refresh: "r2" });
  });
  it("si le refresh échoue, déconnecte l'utilisateur", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => rep(401, { detail: "non" })));
    const onExpired = vi.fn();
    setSession({ access: "a", refresh: "r", onExpired });
    await getMissions().then(() => { throw new Error("aurait dû échouer"); }, () => {});
    expect(onExpired).toHaveBeenCalled();
  });
  it("traduit un 404 générique en message lisible", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => rep(404, { detail: "Not Found" })));
    setSession({ access: "a" });
    await getMissions().then(() => { throw new Error("aurait dû échouer"); },
      (e) => expect(e.message).toBe("Cette fonction n'est pas encore disponible."));
  });
  it("serveur injoignable : message explicite", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network"); }));
    setSession({ access: "a" });
    await getMissions().then(() => { throw new Error("aurait dû échouer"); }, (e) => expect(e.message).toMatch(/Serveur injoignable/));
  });
  it("téléchargement d'une tâche : récupère le blob et le nom du fichier", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => rep(200, {}, { "Content-Disposition": 'attachment; filename="dossier_M3.xlsx"' })));
    setSession({ access: "a" });
    expect(await telechargerTache("abc")).toEqual({ blob: "BLOB", nom: "dossier_M3.xlsx" });
  });
});
