"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";
import { X } from "lucide-react";

import { DataTable } from "@/components/shared/data-table";
import { cn } from "@/lib/utils";
import type { EnrichedExportRow, ScheduleExportRow } from "@/types/schedule-export";

export interface ExportResultsTableProps {
  items: (ScheduleExportRow | EnrichedExportRow)[];
  total: number;
  operatorsQueried: number;
  operatorsSucceeded: number;
  enriched?: boolean;
}

function isEnriched(item: ScheduleExportRow | EnrichedExportRow): item is EnrichedExportRow {
  return "cpfPaciente" in item;
}

interface DetailField {
  label: string;
  value: string | undefined;
  mono?: boolean;
  highlight?: boolean;
}

function DetailModal({
  item,
  enriched,
  onClose,
  t,
}: {
  item: ScheduleExportRow | EnrichedExportRow;
  enriched?: boolean;
  onClose: () => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const fields: DetailField[] = [
    { label: t("agendamentos.col_solicitacao"), value: item.solicitacao, mono: true },
    { label: t("agendamentos.col_procedimento"), value: item.descricaoProcedimento },
    { label: t("agendamentos.col_profissional"), value: item.nomeProfissionalExecutante },
    { label: t("agendamentos.col_data_agendamento"), value: item.dataAgendamento },
    { label: t("agendamentos.col_hora"), value: item.hrAgendamento },
    { label: t("agendamentos.col_cns"), value: item.cns, mono: true },
    ...(enriched && isEnriched(item)
      ? [
          { label: t("agendamentos.col_cpf"), value: item.cpfPaciente, mono: true, highlight: true },
          { label: t("agendamentos.col_celular"), value: item.telefoneCadsus, mono: true, highlight: true },
        ]
      : []),
    { label: t("agendamentos.col_paciente"), value: item.nome },
    { label: t("agendamentos.col_nascimento"), value: item.dtNascimento },
    { label: t("agendamentos.col_idade"), value: item.idade },
    { label: t("agendamentos.col_sexo"), value: item.sexo },
    { label: t("agendamentos.col_nome_mae"), value: item.nomeMae },
    { label: t("agendamentos.col_telefone"), value: item.telefone },
    { label: t("agendamentos.col_municipio"), value: item.municipio },
    { label: t("agendamentos.col_unidade"), value: item.unidadeFantasia },
    { label: t("agendamentos.col_situacao"), value: item.situacao },
    { label: t("agendamentos.col_cid"), value: item.cid },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-backdrop-in" onClick={onClose}>
      <div className="absolute inset-0 bg-black/25 [backdrop-filter:blur(8px)]" />
      <div
        className={cn(
          "relative z-10 w-full max-w-lg mx-4 rounded-2xl overflow-hidden animate-slide-in-scale",
          "bg-[var(--glass-surface-strong)] [backdrop-filter:var(--glass-blur-strong)]",
          "border border-[var(--glass-border)] shadow-[var(--glass-shadow-floating)]",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-2">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">{item.nome}</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--glass-surface-hover)] transition-colors"
          >
            <X className="h-4 w-4 text-[var(--text-tertiary)]" />
          </button>
        </div>
        <div className="px-5 pb-5 space-y-2 max-h-[70vh] overflow-y-auto">
          {fields.map((f) => (
            <div key={f.label} className="flex items-baseline gap-3">
              <span className="text-[11px] font-medium text-[var(--text-tertiary)] w-36 shrink-0 text-right">
                {f.label}
              </span>
              <span
                className={cn(
                  "text-sm text-[var(--text-primary)]",
                  f.mono && "font-mono",
                  f.highlight && "text-[var(--accent-indigo)] font-semibold",
                )}
              >
                {f.value || "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

type ExportRow = ScheduleExportRow | EnrichedExportRow;

export function ExportResultsTable({ items, total, operatorsQueried, operatorsSucceeded, enriched }: ExportResultsTableProps) {
  const t = useTranslations();
  const [selectedItem, setSelectedItem] = useState<ExportRow | null>(null);

  const columns = useMemo<ColumnDef<ExportRow, unknown>[]>(() => {
    const cols: ColumnDef<ExportRow, unknown>[] = [
      {
        accessorKey: "solicitacao",
        header: t("agendamentos.col_solicitacao"),
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: "nome",
        header: t("agendamentos.col_paciente"),
        cell: ({ getValue }) => (
          <span className="text-xs max-w-[200px] truncate block">{getValue() as string}</span>
        ),
      },
    ];

    if (enriched) {
      cols.push({
        id: "cpfPaciente",
        accessorFn: (row) => (isEnriched(row) ? row.cpfPaciente ?? "" : ""),
        header: () => (
          <span className="text-[var(--accent-indigo)]">{t("agendamentos.col_cpf")}</span>
        ),
        cell: ({ getValue }) => (
          <span className="font-mono text-xs text-[var(--accent-indigo)]">
            {(getValue() as string) || "—"}
          </span>
        ),
      });
    }

    cols.push({
      accessorKey: "dataAgendamento",
      header: t("agendamentos.col_data_agendamento"),
      cell: ({ getValue }) => (
        <span className="text-xs whitespace-nowrap">{getValue() as string}</span>
      ),
    });

    if (enriched) {
      cols.push({
        id: "telefoneCadsus",
        accessorFn: (row) => (isEnriched(row) ? row.telefoneCadsus ?? "" : ""),
        header: () => (
          <span className="text-[var(--accent-indigo)]">{t("agendamentos.col_celular")}</span>
        ),
        cell: ({ getValue }) => (
          <span className="text-xs text-[var(--accent-indigo)]">
            {(getValue() as string) || "—"}
          </span>
        ),
      });
    }

    cols.push(
      {
        accessorKey: "descricaoProcedimento",
        header: t("agendamentos.col_procedimento"),
        cell: ({ getValue }) => (
          <span className="text-xs max-w-[180px] truncate block">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: "situacao",
        header: t("agendamentos.col_situacao"),
        cell: ({ getValue }) => (
          <span className="text-xs">{getValue() as string}</span>
        ),
      },
    );

    return cols;
  }, [enriched, t]);

  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-[var(--text-tertiary)]">
        {t("consulta.no_results")}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
        <span>
          {total} {t("agendamentos.total_records")}
        </span>
        <span>
          {operatorsSucceeded}/{operatorsQueried} {t("agendamentos.operators_label")}
        </span>
      </div>

      <DataTable
        columns={columns}
        data={items}
        pageSize={50}
        onRowClick={setSelectedItem}
      />

      {selectedItem && (
        <DetailModal
          item={selectedItem}
          enriched={enriched}
          onClose={() => setSelectedItem(null)}
          t={t}
        />
      )}
    </div>
  );
}
