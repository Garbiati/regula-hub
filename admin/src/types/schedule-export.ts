export interface ScheduleExportFilters {
  dateFrom: string; // dd/MM/yyyy
  dateTo: string; // dd/MM/yyyy
  profileType: string;
  usernames: string[];
  procedureFilter?: string;
  enrich?: boolean;
  persist?: boolean;
}

export interface ScheduleExportRow {
  solicitacao: string;
  codigoInterno: string;
  codigoUnificado: string;
  descricaoProcedimento: string;
  nomeProfissionalExecutante: string;
  dataAgendamento: string;
  hrAgendamento: string;
  tipo: string;
  cns: string;
  nome: string;
  dtNascimento: string;
  idade: string;
  nomeMae: string;
  telefone: string;
  municipio: string;
  cnesSolicitante: string;
  unidadeFantasia: string;
  sexo: string;
  dataSolicitacao: string;
  situacao: string;
  cid: string;
  nomeProfissionalSolicitante: string;
}

export interface EnrichedExportRow extends ScheduleExportRow {
  cpfPaciente?: string;
  emailPaciente?: string;
  telefoneCadsus?: string;
  nomePai?: string;
  raca?: string;
  cnsDefinitivo?: string;
}

export interface OperatorExportResponse {
  operator: string;
  items: ScheduleExportRow[];
  total: number;
}

export interface CadsusPatientEnrichment {
  cpf?: string;
  email?: string;
  phone?: string;
  fatherName?: string;
  race?: string;
  cnsDefinitivo?: string;
}

export interface CadsusEnrichResponse {
  results: Record<string, CadsusPatientEnrichment>;
  total: number;
  found: number;
  failed: number;
  fromCache: number;
}

export interface ScheduleExportResponse {
  items: (ScheduleExportRow | EnrichedExportRow)[];
  total: number;
  totalUnfiltered?: number;
  operatorsQueried: number;
  operatorsSucceeded: number;
  enrichedCount?: number;
  procedureFilter?: string;
}

export interface CachedExportResponse {
  items: (ScheduleExportRow | EnrichedExportRow)[];
  total: number;
}

export interface PersistExportResponse {
  persisted: number;
}
