import { http, HttpResponse } from "msw";

import {
  makeCredential,
  makeCredentialValidation,
  makeRegulationSystem,
  makeValidateLoginResult,
} from "./fixtures";

const BASE = "http://localhost:8000";

export const handlers = [
  // Health check
  http.get(`${BASE}/health`, () => {
    return HttpResponse.json({ status: "ok" });
  }),

  // Regulation systems — list
  http.get(`${BASE}/api/admin/regulation-systems`, () => {
    const items = [
      makeRegulationSystem({ code: "SISREG", name: "SisReg", routeSegment: "sisreg", icon: "Monitor" }),
      makeRegulationSystem({ code: "ESUS", name: "e-SUS Regulação", routeSegment: "esus-regulacao", icon: "ArrowLeftRight" }),
      makeRegulationSystem({ code: "SIGA", name: "SIGA Saúde", routeSegment: "siga-saude", icon: "Hospital" }),
      makeRegulationSystem({ code: "CARE", name: "Care Paraná", routeSegment: "care-parana", icon: "Heart" }),
      makeRegulationSystem({ code: "SER", name: "SER (RJ)", routeSegment: "ser-rj", icon: "Landmark" }),
    ];
    return HttpResponse.json({ items, total: items.length });
  }),

  // Credentials — list
  http.get(`${BASE}/api/admin/credentials`, ({ request }) => {
    const url = new URL(request.url);
    const system = url.searchParams.get("system") ?? "SISREG";
    const items = [
      makeCredential({ systemCode: system, profileName: "VIDEOFONISTA" }),
      makeCredential({ systemCode: system, profileName: "VIDEOFONISTA", username: "user-extra" }),
    ];
    return HttpResponse.json({ items, total: items.length });
  }),

  // Credentials — states
  http.get(`${BASE}/api/admin/credentials/states`, () => {
    return HttpResponse.json([{ state: "AM", state_name: "Amazonas" }]);
  }),

  // Credentials — profiles
  http.get(`${BASE}/api/admin/credentials/profiles`, () => {
    return HttpResponse.json([
      { name: "VIDEOFONISTA", description: "Videofonista" },
      { name: "SOLICITANTE", description: "Solicitante" },
    ]);
  }),

  // Credentials — create
  http.post(`${BASE}/api/admin/credentials`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(makeCredential({ username: body.username as string }));
  }),

  // Credentials — update
  http.put(`${BASE}/api/admin/credentials/:id`, async ({ params }) => {
    return HttpResponse.json(makeCredential({ id: params.id as string }));
  }),

  // Credentials — delete
  http.delete(`${BASE}/api/admin/credentials/:id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Credentials — validate single
  http.post(`${BASE}/api/admin/credentials/:id/validate`, () => {
    return HttpResponse.json(makeCredentialValidation());
  }),

  // Credentials — validate login
  http.post(`${BASE}/api/admin/credentials/validate-login`, () => {
    return HttpResponse.json(makeValidateLoginResult());
  }),
];
