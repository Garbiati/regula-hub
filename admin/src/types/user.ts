export interface RegulaHubUser {
  id: string;
  name: string;
  email: string;
  login: string;
  cpf: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
  createdBy: string | null;
  updatedBy: string | null;
}

export interface UserSelection {
  id: string;
  userId: string;
  system: string;
  profileType: string;
  state: string;
  stateName: string;
  selectedUsers: string[];
  createdAt: string;
  updatedAt: string | null;
}

export interface UpsertSelectionRequest {
  system: string;
  profile_type: string;
  state: string;
  state_name: string;
  selected_users: string[];
}

export interface UserListResponse {
  items: RegulaHubUser[];
  total: number;
}

export interface UserSelectionListResponse {
  items: UserSelection[];
  total: number;
}
