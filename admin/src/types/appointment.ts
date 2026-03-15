export interface AppointmentListing {
  code: string;
  requestDate: string;
  risk: number;
  patientName: string;
  phone: string;
  municipality: string;
  age: string;
  procedure: string;
  cid: string;
  deptSolicitation: string;
  deptExecute: string;
  executionDate: string;
  status: string;
}

export interface BestPhone {
  raw: string;
  ddd: string;
  number: string;
  phoneType: string;
}

export interface AppointmentDetail {
  reqUnitName: string | null;
  reqUnitCnes: string | null;
  patientCns: string | null;
  patientName: string | null;
  patientBirthDate: string | null;
  patientPhone: string | null;
  doctorName: string | null;
  doctorCrm: string | null;
  solCode: string | null;
  solStatus: string | null;
  solRisk: string | null;
  solCid: string | null;
  procedureName: string | null;
  procedureCode: string | null;
  appointmentDate: string | null;
  confirmationKey: string | null;
  videocallOperator: string | null;
  solicitationOperator: string | null;
  regulatoryCenter: string | null;
  department: string | null;
  cnes: string | null;
  priority: string | null;
  observations: string | null;
  bestPhone: BestPhone | null;
}

export interface SearchFilters {
  // Identification
  solCode?: string;
  patientCns?: string;
  patientName?: string;
  cnesSolicitation?: string;
  cnesExecute?: string;
  // Procedure
  procedureUnifiedCode?: string;
  procedureInternalCode?: string;
  procedureDescription?: string;
  // Date/Period
  searchType: string;
  dateFrom: string;
  dateTo: string;
  // Status
  situation: string;
  itemsPerPage: string;
  // Auth context
  profileType: string;
  usernames: string[];
}

export interface SearchResponse {
  items: AppointmentListing[];
  total: number;
}
