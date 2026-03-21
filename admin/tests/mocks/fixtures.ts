import type { Credential, CredentialValidation, ValidateLoginResult } from "@/types/credential";
import type { RegulationSystem } from "@/types/regulation-system";

let counter = 0;
function nextId(): string {
  counter += 1;
  return `00000000-0000-0000-0000-${String(counter).padStart(12, "0")}`;
}

export function makeCredential(overrides: Partial<Credential> = {}): Credential {
  return {
    id: nextId(),
    userId: "b3a7c9e1-4f2d-4e8a-9c1b-5d6f7a8b9c0e",
    profileId: nextId(),
    username: `user-${counter}`,
    profileName: "VIDEOFONISTA",
    systemCode: "SISREG",
    scope: "regulation",
    state: "AM",
    stateName: "Amazonas",
    unitName: null,
    unitCnes: null,
    isActive: true,
    lastValidatedAt: null,
    isValid: null,
    createdAt: "2026-03-01T10:00:00Z",
    updatedAt: null,
    ...overrides,
  };
}

export function makeCredentialValidation(overrides: Partial<CredentialValidation> = {}): CredentialValidation {
  return {
    username: "op1",
    valid: true,
    error: null,
    ...overrides,
  };
}

export function makeValidateLoginResult(overrides: Partial<ValidateLoginResult> = {}): ValidateLoginResult {
  return {
    username: "op1",
    valid: true,
    error: null,
    unitCnes: "1234567",
    unitName: "UBS Centro",
    profileType: "videofonista",
    state: "AM",
    stateName: "Amazonas",
    ...overrides,
  };
}

export function makeRegulationSystem(overrides: Partial<RegulationSystem> = {}): RegulationSystem {
  return {
    id: nextId(),
    code: "SISREG",
    name: "SisReg",
    description: "Sistema Nacional de Regulação do SUS",
    baseUrl: "https://sisregiii.saude.gov.br",
    routeSegment: "sisreg",
    icon: "Monitor",
    tablePrefix: "sisreg",
    isActive: true,
    createdAt: "2026-03-01T10:00:00Z",
    updatedAt: null,
    createdBy: null,
    updatedBy: null,
    ...overrides,
  };
}
