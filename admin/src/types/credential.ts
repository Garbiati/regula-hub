export interface Credential {
  id: string;
  userId: string;
  profileId: string;
  username: string;
  profileName: string | null;
  systemCode: string | null;
  scope: string | null;
  state: string | null;
  stateName: string | null;
  unitName: string | null;
  unitCnes: string | null;
  isActive: boolean;
  lastValidatedAt: string | null;
  isValid: boolean | null;
  createdAt: string;
  updatedAt: string | null;
}

export interface CredentialCreate {
  user_id: string;
  profile_id: string;
  username: string;
  password: string;
  state?: string;
  state_name?: string;
  unit_name?: string;
  unit_cnes?: string;
}

export interface CredentialUpdate {
  username?: string;
  password?: string;
  profile_id?: string;
  state?: string;
  state_name?: string;
  unit_name?: string;
  unit_cnes?: string;
  is_active?: boolean;
}

export interface CredentialState {
  state: string;
  stateName: string;
}

export interface CredentialProfile {
  name: string;
  description: string;
}

export interface CredentialListResponse {
  items: Credential[];
  total: number;
}

export interface CredentialValidation {
  username: string;
  valid: boolean;
  error: string | null;
}

export interface ValidateLoginResult {
  username: string;
  valid: boolean;
  error: string | null;
  unitCnes: string | null;
  unitName: string | null;
  profileType: string | null;
  state: string | null;
  stateName: string | null;
}
