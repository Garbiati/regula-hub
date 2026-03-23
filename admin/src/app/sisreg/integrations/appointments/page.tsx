"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  SkipForward,
  Ban,
  Loader2,
  RefreshCw,
  Eye,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Toaster, toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import {
  useIntegrationAppointments,
  useAppointmentStatusCounts,
  useRetryAppointment,
  useCancelAppointment,
} from "@/hooks/use-integration-appointments";
import type { IntegrationAppointment, AppointmentStatus } from "@/types/integration-appointment";

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string; label: string }> = {
  pending: { icon: <Clock className="w-3.5 h-3.5" />, color: "text-gray-400", bg: "bg-gray-500/10", label: "Pendente" },
  integrated: { icon: <CheckCircle2 className="w-3.5 h-3.5" />, color: "text-emerald-400", bg: "bg-emerald-500/10", label: "Integrado" },
  skipped: { icon: <SkipForward className="w-3.5 h-3.5" />, color: "text-blue-400", bg: "bg-blue-500/10", label: "Já existia" },
  patient_error: { icon: <XCircle className="w-3.5 h-3.5" />, color: "text-red-400", bg: "bg-red-500/10", label: "Erro paciente" },
  appointment_error: { icon: <XCircle className="w-3.5 h-3.5" />, color: "text-red-400", bg: "bg-red-500/10", label: "Erro agendamento" },
  mapping_error: { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: "text-amber-400", bg: "bg-amber-500/10", label: "Sem mapeamento" },
  data_error: { icon: <AlertTriangle className="w-3.5 h-3.5" />, color: "text-amber-400", bg: "bg-amber-500/10", label: "Dados incompletos" },
  cancelled: { icon: <Ban className="w-3.5 h-3.5" />, color: "text-gray-500", bg: "bg-gray-500/10", label: "Cancelado" },
  completed: { icon: <CheckCircle2 className="w-3.5 h-3.5" />, color: "text-emerald-500", bg: "bg-emerald-500/10", label: "Atendido" },
  no_show: { icon: <XCircle className="w-3.5 h-3.5" />, color: "text-orange-400", bg: "bg-orange-500/10", label: "Não compareceu" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { icon: <Clock className="w-3.5 h-3.5" />, color: "text-gray-400", bg: "bg-gray-500/10", label: status };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${cfg.bg} ${cfg.color} border-current/20`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function CountCard({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="text-center px-3 py-2">
      <p className={`text-xl font-bold tabular-nums ${color}`}>{count}</p>
      <p className="text-[11px] text-[var(--text-tertiary)]">{label}</p>
    </div>
  );
}

function DetailModal({ appointment, onClose }: { appointment: IntegrationAppointment; onClose: () => void }) {
  const t = useTranslations();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative z-10 w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto rounded-2xl bg-[var(--glass-surface-strong)] border border-[var(--glass-border)] shadow-[var(--glass-shadow-floating)] p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-[var(--text-primary)]">
            {t("appointments.detail_title")} — {appointment.regulationCode}
          </h3>
          <StatusBadge status={appointment.status} />
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_patient")}:</span> <span className="font-medium">{appointment.patientName}</span></div>
          <div><span className="text-[var(--text-tertiary)]">CPF:</span> <span className="font-mono">{appointment.patientCpf || "—"}</span></div>
          <div><span className="text-[var(--text-tertiary)]">CNS:</span> <span className="font-mono">{appointment.patientCns || "—"}</span></div>
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_phone")}:</span> <span>{appointment.patientPhone || "—"}</span></div>
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_date")}:</span> <span>{appointment.appointmentDate} {appointment.appointmentTime || ""}</span></div>
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_procedure")}:</span> <span>{appointment.procedureName}</span></div>
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_executor")}:</span> <span>{appointment.departmentExecutor || "—"}</span></div>
          <div><span className="text-[var(--text-tertiary)]">{t("appointments.col_doctor")}:</span> <span>{appointment.doctorName || "—"}</span></div>
        </div>

        {appointment.errorMessage && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
            <p className="text-xs font-medium text-red-400">{t("appointments.error_label")}</p>
            <p className="text-sm text-red-300 mt-1">{appointment.errorMessage}</p>
          </div>
        )}

        {appointment.integrationData && Object.keys(appointment.integrationData).length > 0 && (
          <div>
            <p className="text-xs font-medium text-[var(--text-tertiary)] mb-1">{t("appointments.integration_data")}</p>
            <pre className="text-[11px] bg-[var(--bg-secondary)] rounded-lg p-3 overflow-x-auto">
              {JSON.stringify(appointment.integrationData, null, 2)}
            </pre>
          </div>
        )}

        <button onClick={onClose} className="w-full py-2 rounded-xl bg-[var(--glass-surface)] border border-[var(--glass-border)] text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors">
          {t("common.close")}
        </button>
      </div>
    </div>
  );
}

const PAGE_SIZE = 20;

export default function IntegrationAppointmentsPage() {
  const t = useTranslations();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const skip = page * PAGE_SIZE;
  const { data, isLoading } = useIntegrationAppointments(statusFilter || undefined, undefined, undefined, skip, PAGE_SIZE);
  const { data: counts } = useAppointmentStatusCounts();
  const retryMutation = useRetryAppointment();
  const cancelMutation = useCancelAppointment();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const selectedAppointment = items.find((i) => i.id === selectedId);

  const isErrorStatus = (s: string) => s.includes("error");

  return (
    <div className="space-y-6">
      <PageHeader title={t("appointments.page_title")} />

      {/* Summary cards */}
      {counts && (
        <div className="animate-fadeInUp-2">
          <Card className="glass-specular">
            <CardContent className="py-3">
              <div className="grid grid-cols-5 sm:grid-cols-10 divide-x divide-[var(--glass-border)]">
                <CountCard label={t("appointments.status_integrated")} count={counts.integrated} color="text-emerald-400" />
                <CountCard label={t("appointments.status_skipped")} count={counts.skipped} color="text-blue-400" />
                <CountCard label={t("appointments.status_pending")} count={counts.pending} color="text-gray-400" />
                <CountCard label="Pac. Erro" count={counts.patientError} color="text-red-400" />
                <CountCard label="Agend. Erro" count={counts.appointmentError} color="text-red-400" />
                <CountCard label="Mapeamento" count={counts.mappingError} color="text-amber-400" />
                <CountCard label="Dados" count={counts.dataError} color="text-amber-400" />
                <CountCard label={t("appointments.status_cancelled")} count={counts.cancelled} color="text-gray-500" />
                <CountCard label={t("appointments.status_completed")} count={counts.completed} color="text-emerald-500" />
                <CountCard label="No Show" count={counts.noShow} color="text-orange-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter + Table */}
      <div className="animate-fadeInUp-3">
        <Card className="glass-specular">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t("appointments.list_title")} {total > 0 && `(${total})`}</CardTitle>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
                className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-surface)] px-3 py-1.5 text-xs text-[var(--text-primary)]"
              >
                <option value="">{t("appointments.filter_all")}</option>
                <option value="integrated">{t("appointments.status_integrated")}</option>
                <option value="skipped">{t("appointments.status_skipped")}</option>
                <option value="pending">{t("appointments.status_pending")}</option>
                <option value="patient_error">Erro Paciente</option>
                <option value="appointment_error">Erro Agendamento</option>
                <option value="mapping_error">Sem Mapeamento</option>
                <option value="data_error">Dados Incompletos</option>
                <option value="cancelled">{t("appointments.status_cancelled")}</option>
                <option value="completed">{t("appointments.status_completed")}</option>
              </select>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-8 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-[var(--text-tertiary)]" /></div>
            ) : items.length === 0 ? (
              <div className="py-8 text-center text-sm text-[var(--text-tertiary)]">{t("appointments.no_results")}</div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] border-b border-[var(--glass-border)]">
                        <th className="pb-2 pr-3">{t("appointments.col_code")}</th>
                        <th className="pb-2 pr-3">{t("appointments.col_patient")}</th>
                        <th className="pb-2 pr-3">{t("appointments.col_procedure")}</th>
                        <th className="pb-2 pr-3">{t("appointments.col_date")}</th>
                        <th className="pb-2 pr-3">{t("appointments.col_executor")}</th>
                        <th className="pb-2 pr-3">{t("appointments.col_status")}</th>
                        <th className="pb-2">{t("appointments.col_actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((appt: IntegrationAppointment) => (
                        <tr key={appt.id} className="border-b border-[var(--glass-border-subtle)] last:border-0 hover:bg-[var(--bg-secondary)]/40 transition-colors">
                          <td className="py-2.5 pr-3 font-mono text-xs">{appt.regulationCode}</td>
                          <td className="py-2.5 pr-3 text-[var(--text-primary)] max-w-[150px] truncate">{appt.patientName}</td>
                          <td className="py-2.5 pr-3 text-[var(--text-secondary)] text-xs max-w-[120px] truncate">{appt.procedureName?.replace("TELECONSULTA EM ", "")}</td>
                          <td className="py-2.5 pr-3 text-xs tabular-nums">{appt.appointmentDate} {appt.appointmentTime?.slice(0, 5) || ""}</td>
                          <td className="py-2.5 pr-3 text-xs text-[var(--text-secondary)] max-w-[120px] truncate">{appt.departmentExecutor || "—"}</td>
                          <td className="py-2.5 pr-3"><StatusBadge status={appt.status} /></td>
                          <td className="py-2.5">
                            <div className="flex items-center gap-1">
                              <button onClick={() => setSelectedId(appt.id)} className="p-1 rounded hover:bg-[var(--bg-secondary)] transition-colors" title="Detalhes">
                                <Eye className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
                              </button>
                              {isErrorStatus(appt.status) && (
                                <button
                                  onClick={() => retryMutation.mutate(appt.id)}
                                  disabled={retryMutation.isPending}
                                  className="p-1 rounded hover:bg-[var(--accent-indigo-bg)] transition-colors"
                                  title="Retry"
                                >
                                  <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-indigo)]" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-3 border-t border-[var(--glass-border-subtle)]">
                    <span className="text-xs text-[var(--text-tertiary)]">
                      {t("integrations.page_info", { current: page + 1, total: totalPages })}
                    </span>
                    <div className="flex gap-1">
                      <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="p-1.5 rounded-lg hover:bg-[var(--bg-secondary)] disabled:opacity-30">
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="p-1.5 rounded-lg hover:bg-[var(--bg-secondary)] disabled:opacity-30">
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detail modal */}
      {selectedAppointment && <DetailModal appointment={selectedAppointment} onClose={() => setSelectedId(null)} />}

      <Toaster />
    </div>
  );
}
