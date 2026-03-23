export interface IntegrationAppointment {
  id: string;
  integrationSystemId: string;
  executionId: string | null;
  regulationCode: string;
  confirmationKey: string | null;
  externalId: string | null;
  patientName: string;
  patientCpf: string | null;
  patientCns: string | null;
  patientBirthDate: string | null;
  patientPhone: string | null;
  patientMotherName: string | null;
  appointmentDate: string;
  appointmentTime: string | null;
  procedureName: string;
  departmentExecutor: string | null;
  departmentExecutorCnes: string | null;
  departmentSolicitor: string | null;
  departmentSolicitorCnes: string | null;
  doctorName: string | null;
  doctorCpf: string | null;
  status: AppointmentStatus;
  errorMessage: string | null;
  errorCategory: string | null;
  integrationData: Record<string, unknown> | null;
  sourceData: Record<string, unknown> | null;
  referenceDate: string;
  createdAt: string | null;
  updatedAt: string | null;
}

export type AppointmentStatus =
  | "pending"
  | "patient_registered"
  | "integrated"
  | "skipped"
  | "patient_error"
  | "appointment_error"
  | "mapping_error"
  | "data_error"
  | "cancelled"
  | "completed"
  | "no_show";

export interface AppointmentListResponse {
  items: IntegrationAppointment[];
  total: number;
}

export interface AppointmentStatusCounts {
  pending: number;
  integrated: number;
  skipped: number;
  patientError: number;
  appointmentError: number;
  mappingError: number;
  dataError: number;
  cancelled: number;
  completed: number;
  noShow: number;
}

export interface AppointmentUpdateRequest {
  patientName?: string;
  patientCpf?: string;
  patientCns?: string;
  patientBirthDate?: string;
  patientPhone?: string;
  doctorName?: string;
  doctorCpf?: string;
  departmentExecutor?: string;
  departmentExecutorCnes?: string;
}
