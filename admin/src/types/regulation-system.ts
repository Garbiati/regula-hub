export interface RegulationSystem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  baseUrl: string | null;
  routeSegment: string | null;
  icon: string | null;
  tablePrefix: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
  createdBy: string | null;
  updatedBy: string | null;
}

export interface RegulationSystemListResponse {
  items: RegulationSystem[];
  total: number;
}

export interface SystemProfile {
  id: string;
  scope: string;
  regulationSystemId: string | null;
  integrationSystemId: string | null;
  systemCode: string | null;
  profileName: string;
  description: string | null;
  level: number;
  sortOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export interface SystemProfileListResponse {
  items: SystemProfile[];
  total: number;
}
