"use client";

import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MetadataField } from "@/components/shared/metadata-field";
import { useAppointmentDetail } from "@/hooks/use-appointment-detail";

export interface DetailDialogProps {
  code: string | null;
  username: string;
  profileType: string;
  open: boolean;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
        {title}
      </h3>
      <div className="grid grid-cols-1 gap-y-2 sm:grid-cols-2 sm:gap-x-4">{children}</div>
    </section>
  );
}

export function DetailDialog({ code, username, profileType, open, onClose }: DetailDialogProps) {
  const t = useTranslations();
  const { data, isLoading, isError } = useAppointmentDetail(
    open ? code : null,
    username,
    profileType,
  );

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {t("consulta.detail_title")} {code && `#${code}`}
          </DialogTitle>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-[var(--text-tertiary)]" />
          </div>
        )}

        {isError && (
          <p className="py-4 text-center text-sm text-[var(--status-danger)]">
            {t("consulta.detail_error")}
          </p>
        )}

        {data && (
          <div className="space-y-5">
            <Section title={t("consulta.section_req_unit")}>
              <MetadataField label={t("consulta.field_unit_name")} value={data.reqUnitName ?? "\u2014"} />
              <MetadataField label={t("common.cnes")} value={data.reqUnitCnes ?? "\u2014"} />
            </Section>

            <Section title={t("consulta.section_patient")}>
              <MetadataField label={t("consulta.field_patient_name")} value={data.patientName ?? "\u2014"} />
              <MetadataField label={t("consulta.field_patient_cns")} value={data.patientCns ?? "\u2014"} />
              <MetadataField label={t("consulta.field_birth_date")} value={data.patientBirthDate ?? "\u2014"} />
              <MetadataField label={t("consulta.field_phone")} value={data.patientPhone ?? "\u2014"} />
            </Section>

            <Section title={t("consulta.section_doctor")}>
              <MetadataField label={t("consulta.field_doctor_name")} value={data.doctorName ?? "\u2014"} />
              <MetadataField label={t("consulta.field_doctor_crm")} value={data.doctorCrm ?? "\u2014"} />
            </Section>

            <Section title={t("consulta.section_solicitation")}>
              <MetadataField label={t("consulta.field_sol_code")} value={data.solCode ?? "\u2014"} />
              <MetadataField label={t("common.status")} value={data.solStatus ?? "\u2014"} />
              <MetadataField label={t("excel.raw_risk")} value={data.solRisk ?? "\u2014"} />
              <MetadataField label={t("excel.raw_cid")} value={data.solCid ?? "\u2014"} />
            </Section>

            <Section title={t("consulta.section_procedure")}>
              <MetadataField label={t("consulta.field_procedure_name")} value={data.procedureName ?? "\u2014"} />
              <MetadataField label={t("consulta.field_procedure_code")} value={data.procedureCode ?? "\u2014"} />
            </Section>

            <Section title={t("consulta.section_scheduling")}>
              <MetadataField label={t("consulta.field_appointment_date")} value={data.appointmentDate ?? "\u2014"} />
              <MetadataField label={t("consulta.field_confirmation_key")} value={data.confirmationKey ?? "\u2014"} />
            </Section>

            {data.observations && (
              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                  {t("consulta.section_observations")}
                </h3>
                <p className="text-sm text-[var(--text-primary)]">{data.observations}</p>
              </section>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
