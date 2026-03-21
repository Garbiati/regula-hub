"use client";

import { useTranslations } from "next-intl";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AppointmentListing } from "@/types/appointment";

export interface ResultsTableProps {
  items: AppointmentListing[];
  total: number;
  onRowClick: (code: string) => void;
}

export function ResultsTable({ items, total, onRowClick }: ResultsTableProps) {
  const t = useTranslations();

  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-[var(--text-tertiary)]">
        {t("consulta.no_results")}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--text-secondary)]">
        {total} {t("consulta.results_count")}
      </p>
      <div className="max-h-[600px] overflow-auto glass-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("excel.raw_code")}</TableHead>
              <TableHead>{t("excel.raw_request_date")}</TableHead>
              <TableHead>{t("excel.raw_risk")}</TableHead>
              <TableHead>{t("excel.raw_patient")}</TableHead>
              <TableHead>{t("excel.raw_age")}</TableHead>
              <TableHead>{t("excel.raw_procedure")}</TableHead>
              <TableHead>{t("excel.raw_cid")}</TableHead>
              <TableHead>{t("excel.raw_dept_solicitation")}</TableHead>
              <TableHead>{t("excel.raw_dept_execute")}</TableHead>
              <TableHead>{t("excel.raw_status")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={item.code}
                className="cursor-pointer hover:bg-[var(--glass-surface-hover)]"
                onClick={() => onRowClick(item.code)}
              >
                <TableCell className="font-mono text-xs">{item.code}</TableCell>
                <TableCell className="text-xs">{item.requestDate}</TableCell>
                <TableCell className="text-xs">{item.risk}</TableCell>
                <TableCell className="text-xs max-w-[100px] sm:max-w-[200px] truncate">{item.patientName}</TableCell>
                <TableCell className="text-xs">{item.age}</TableCell>
                <TableCell className="text-xs max-w-[100px] sm:max-w-[180px] truncate">{item.procedure}</TableCell>
                <TableCell className="text-xs">{item.cid}</TableCell>
                <TableCell className="text-xs max-w-[80px] sm:max-w-[150px] truncate">{item.deptSolicitation}</TableCell>
                <TableCell className="text-xs max-w-[80px] sm:max-w-[150px] truncate">{item.deptExecute}</TableCell>
                <TableCell className="text-xs">{item.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
