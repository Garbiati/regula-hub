"use client";

import { useCallback, useReducer, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { snakelizeKeys } from "@/lib/utils";
import type {
  CachedExportResponse,
  CadsusEnrichResponse,
  CadsusPatientEnrichment,
  EnrichedExportRow,
  OperatorExportResponse,
  PersistExportResponse,
  ScheduleExportFilters,
  ScheduleExportRow,
} from "@/types/schedule-export";
import type { OperatorPipelineState, PipelineState } from "@/types/pipeline";

// ── Reducer types ──

type Action =
  | { type: "START"; usernames: string[] }
  | { type: "CONNECTING"; username: string }
  | { type: "SEARCHING"; username: string }
  | { type: "SUCCESS"; username: string; total: number }
  | { type: "ERROR"; username: string; error: string }
  | { type: "MERGE"; uniqueCount: number; droppedCount: number }
  | { type: "ENRICH_START"; total: number }
  | { type: "ENRICH_BATCH"; done: number; found: number; failed: number }
  | { type: "ENRICH_DONE" }
  | { type: "ENRICH_ERROR"; error: string }
  | { type: "ENRICH_SKIP" }
  | { type: "CACHE_START" }
  | { type: "CACHE_DONE"; count: number }
  | { type: "CACHE_SKIP" }
  | { type: "FILTER_DONE"; filteredCount: number }
  | { type: "PERSIST_START" }
  | { type: "PERSIST_DONE" }
  | { type: "PERSIST_ERROR" }
  | { type: "COMPLETE" }
  | { type: "CANCEL" }
  | { type: "RESET" };

const initialState: PipelineState = {
  operators: [],
  mergeStatus: "idle",
  filterStatus: "idle",
  enrichStatus: "idle",
  cacheStatus: "idle",
  cachedCount: 0,
  persistStatus: "idle",
  uniqueCount: 0,
  droppedCount: 0,
  filteredCount: 0,
  enrichedCount: 0,
  enrichFailedCount: 0,
  enrichProgress: { done: 0, total: 0 },
  isComplete: false,
  isCancelled: false,
};

function updateOperator(
  operators: OperatorPipelineState[],
  username: string,
  update: Partial<OperatorPipelineState>,
): OperatorPipelineState[] {
  return operators.map((op) => (op.username === username ? { ...op, ...update } : op));
}

function reducer(state: PipelineState, action: Action): PipelineState {
  switch (action.type) {
    case "START":
      return {
        ...initialState,
        operators: action.usernames.map((username) => ({
          username,
          status: "idle",
          itemCount: 0,
        })),
      };
    case "CONNECTING":
      return {
        ...state,
        operators: updateOperator(state.operators, action.username, { status: "connecting" }),
      };
    case "SEARCHING":
      return {
        ...state,
        operators: updateOperator(state.operators, action.username, { status: "searching" }),
      };
    case "SUCCESS":
      return {
        ...state,
        operators: updateOperator(state.operators, action.username, {
          status: "success",
          itemCount: action.total,
        }),
      };
    case "ERROR":
      return {
        ...state,
        operators: updateOperator(state.operators, action.username, {
          status: "error",
          error: action.error,
        }),
      };
    case "MERGE":
      return {
        ...state,
        mergeStatus: "success",
        uniqueCount: action.uniqueCount,
        droppedCount: action.droppedCount,
      };
    case "ENRICH_START":
      return {
        ...state,
        enrichStatus: "active",
        enrichedCount: 0,
        enrichFailedCount: 0,
        enrichProgress: { done: 0, total: action.total },
        isComplete: false,
      };
    case "ENRICH_BATCH":
      return {
        ...state,
        enrichProgress: { ...state.enrichProgress, done: action.done },
        enrichedCount: state.enrichedCount + action.found,
        enrichFailedCount: state.enrichFailedCount + action.failed,
      };
    case "ENRICH_DONE":
      return {
        ...state,
        enrichStatus: state.enrichFailedCount > 0 ? "partial" : "success",
      };
    case "ENRICH_ERROR":
      return { ...state, enrichStatus: "partial", enrichedCount: 0, enrichFailedCount: state.uniqueCount };
    case "ENRICH_SKIP":
      return { ...state, enrichStatus: "skipped" };
    case "CACHE_START":
      return { ...state, cacheStatus: "loading" };
    case "CACHE_DONE":
      return { ...state, cacheStatus: "done", cachedCount: action.count };
    case "CACHE_SKIP":
      return { ...state, cacheStatus: "skipped" };
    case "FILTER_DONE":
      return { ...state, filterStatus: "success", filteredCount: action.filteredCount };
    case "PERSIST_START":
      return { ...state, persistStatus: "saving" };
    case "PERSIST_DONE":
      return { ...state, persistStatus: "done" };
    case "PERSIST_ERROR":
      return { ...state, persistStatus: "error" };
    case "COMPLETE":
      return { ...state, isComplete: true };
    case "CANCEL":
      return {
        ...state,
        operators: state.operators.map((op) =>
          op.status === "idle" || op.status === "connecting" || op.status === "searching"
            ? { ...op, status: "cancelled" as const }
            : op,
        ),
        enrichStatus: state.enrichStatus === "idle" ? "skipped" : state.enrichStatus,
        isComplete: true,
        isCancelled: true,
      };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

// ── Delay for visual "connecting" phase ──
const CONNECTING_DELAY_MS = 800;

function buildRequestBody(filters: ScheduleExportFilters, username: string): Record<string, unknown> {
  return {
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    profile_type: filters.profileType,
    usernames: [username],
    procedure_filter: filters.procedureFilter || null,
    enrich: false,
  };
}

type AnyExportRow = ScheduleExportRow | EnrichedExportRow;

function deduplicateBySolicitacao(items: AnyExportRow[]): AnyExportRow[] {
  const seen = new Map<string, AnyExportRow>();
  for (const item of items) {
    if (!item.solicitacao) continue;
    const existing = seen.get(item.solicitacao);
    if (!existing) {
      seen.set(item.solicitacao, item);
    } else if ("cpfPaciente" in item && (item as EnrichedExportRow).cpfPaciente && !("cpfPaciente" in existing && (existing as EnrichedExportRow).cpfPaciente)) {
      // Prefer enriched version over non-enriched
      seen.set(item.solicitacao, item);
    }
  }
  return [...seen.values()];
}

// ── Hook ──

export interface UseExportPipelineReturn {
  pipelineState: PipelineState;
  results: (ScheduleExportRow | EnrichedExportRow)[];
  isModalOpen: boolean;
  isConfirmed: boolean;
  startExport: (filters: ScheduleExportFilters) => void;
  retryOperator: (username: string) => void;
  retryEnrichment: () => void;
  confirmResults: () => void;
  cancel: () => void;
  reset: () => void;
  isExporting: boolean;
}

export function useExportPipeline(): UseExportPipelineReturn {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const resultsRef = useRef<Map<string, ScheduleExportRow[]>>(new Map());
  const enrichedRef = useRef<(ScheduleExportRow | EnrichedExportRow)[]>([]);
  const cachedRef = useRef<(ScheduleExportRow | EnrichedExportRow)[]>([]);
  const enrichResultsAccRef = useRef<Record<string, CadsusPatientEnrichment>>({});
  const failedCnsRef = useRef<Set<string>>(new Set());
  const filtersRef = useRef<ScheduleExportFilters | null>(null);
  const pendingRef = useRef<Set<string>>(new Set());
  const abortRef = useRef<AbortController | null>(null);

  const computeResults = useCallback((): AnyExportRow[] => {
    const allItems: AnyExportRow[] = Array.from(resultsRef.current.values()).flat();
    return deduplicateBySolicitacao(allItems);
  }, []);

  const enrichResults = useCallback(async (rows: AnyExportRow[], targetCns?: string[]) => {
    // Separate rows already enriched from cache vs rows needing CADSUS lookup
    const alreadyEnrichedByCns = new Map<string, CadsusPatientEnrichment>();
    for (const row of rows) {
      if (row.cns && "cpfPaciente" in row && (row as EnrichedExportRow).cpfPaciente) {
        const enriched = row as EnrichedExportRow;
        alreadyEnrichedByCns.set(row.cns, {
          cpf: enriched.cpfPaciente,
          phone: enriched.telefoneCadsus,
          email: enriched.emailPaciente,
        });
      }
    }

    const allUniqueCns = [...new Set(rows.map((r) => r.cns).filter(Boolean))];
    // Only send CNS that aren't already enriched (unless retrying specific CNS)
    const cnsList = targetCns ?? allUniqueCns.filter((cns) => !alreadyEnrichedByCns.has(cns));
    const preEnrichedCount = alreadyEnrichedByCns.size;

    // Total = CNS to fetch from CADSUS + already enriched from cache
    dispatch({ type: "ENRICH_START", total: cnsList.length + preEnrichedCount });

    // Pre-report already-enriched rows as done immediately
    if (preEnrichedCount > 0 && !targetCns) {
      dispatch({ type: "ENRICH_BATCH", done: preEnrichedCount, found: preEnrichedCount, failed: 0 });
    }

    if (cnsList.length === 0) {
      // All rows already enriched from cache — no CADSUS calls needed
      enrichedRef.current = rows;
      enrichResultsAccRef.current = Object.fromEntries(alreadyEnrichedByCns);
      dispatch({ type: "ENRICH_DONE" });
      // Persist with existing enrichment
      if (filtersRef.current?.persist && rows.length > 0) {
        dispatch({ type: "PERSIST_START" });
        try {
          await apiClient.post<PersistExportResponse>(
            "/api/admin/sisreg/schedule-export/persist",
            { items: snakelizeKeys(rows) },
            { signal: abortRef.current?.signal },
          );
          dispatch({ type: "PERSIST_DONE" });
        } catch {
          dispatch({ type: "PERSIST_ERROR" });
        }
      }
      dispatch({ type: "COMPLETE" });
      return;
    }

    // Start with accumulated results from prior runs + pre-enriched from cache
    const allResults: Record<string, CadsusPatientEnrichment> = targetCns
      ? { ...enrichResultsAccRef.current }
      : Object.fromEntries(alreadyEnrichedByCns);
    const filters = filtersRef.current;
    const BATCH_SIZE = 20;

    // Clear failed tracking for this run's target CNS
    for (const cns of cnsList) {
      failedCnsRef.current.delete(cns);
    }

    try {
      for (let i = 0; i < cnsList.length; i += BATCH_SIZE) {
        if (abortRef.current?.signal.aborted) return;

        const batch = cnsList.slice(i, i + BATCH_SIZE);
        const phoneFallbacks: Record<string, string> = {};
        for (const cns of batch) {
          const row = rows.find((r) => r.cns === cns);
          if (row?.telefone) phoneFallbacks[cns] = row.telefone;
        }
        const response = await apiClient.post<CadsusEnrichResponse>(
          "/api/admin/sisreg/schedule-export/enrich",
          {
            cns_list: batch,
            phone_fallbacks: phoneFallbacks,
            sisreg_username: filters?.usernames[0] || null,
            sisreg_profile_type: filters?.profileType || null,
          },
          { signal: abortRef.current?.signal },
        );

        // Accumulate results and track failures
        Object.assign(allResults, response.results);
        for (const cns of batch) {
          if (!response.results[cns]) {
            failedCnsRef.current.add(cns);
          }
        }
        const done = preEnrichedCount + Math.min(i + BATCH_SIZE, cnsList.length);
        dispatch({ type: "ENRICH_BATCH", done, found: response.found, failed: response.failed });
      }

      // Persist accumulated results for future retries
      enrichResultsAccRef.current = allResults;

      // Merge enrichment data into rows
      enrichedRef.current = rows.map((row) => {
        const patient = row.cns ? allResults[row.cns] : undefined;
        if (patient) {
          return { ...row, cpfPaciente: patient.cpf, telefoneCadsus: patient.phone };
        }
        return row;
      });

      dispatch({ type: "ENRICH_DONE" });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      enrichResultsAccRef.current = allResults;
      enrichedRef.current = rows.map((row) => {
        const patient = row.cns ? allResults[row.cns] : undefined;
        if (patient) {
          return { ...row, cpfPaciente: patient.cpf, telefoneCadsus: patient.phone };
        }
        return row;
      });
      dispatch({ type: "ENRICH_ERROR", error: err instanceof Error ? err.message : "Unknown error" });
    }

    // Persist AFTER enrichment — saves enriched data to cache
    // Skip persist if enrichment was enabled but completely failed (0 enriched) to avoid
    // overwriting previously enriched data with null values
    const hasAnyEnrichment = enrichedRef.current.some(
      (r) => "cpfPaciente" in r && (r as EnrichedExportRow).cpfPaciente,
    );
    if (filtersRef.current?.persist && enrichedRef.current.length > 0 && hasAnyEnrichment) {
      dispatch({ type: "PERSIST_START" });
      try {
        await apiClient.post<PersistExportResponse>(
          "/api/admin/sisreg/schedule-export/persist",
          { items: snakelizeKeys(enrichedRef.current) },
          { signal: abortRef.current?.signal },
        );
        dispatch({ type: "PERSIST_DONE" });
      } catch {
        dispatch({ type: "PERSIST_ERROR" });
      }
    } else if (filtersRef.current?.persist && enrichedRef.current.length > 0 && !hasAnyEnrichment) {
      dispatch({ type: "PERSIST_DONE" });
    }

    dispatch({ type: "COMPLETE" });
  }, []);

  const exportOperator = useCallback(async (filters: ScheduleExportFilters, username: string) => {
    const startTime = Date.now();
    dispatch({ type: "CONNECTING", username });

    try {
      const fetchPromise = apiClient.post<OperatorExportResponse>(
        "/api/admin/sisreg/schedule-export/operator",
        buildRequestBody(filters, username),
        { signal: abortRef.current?.signal },
      );

      const elapsed = Date.now() - startTime;
      if (elapsed < CONNECTING_DELAY_MS) {
        await new Promise((r) => setTimeout(r, CONNECTING_DELAY_MS - elapsed));
      }

      dispatch({ type: "SEARCHING", username });

      const data = await fetchPromise;
      resultsRef.current.set(username, data.items);
      dispatch({ type: "SUCCESS", username, total: data.total });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const message = err instanceof Error ? err.message : "Unknown error";
      resultsRef.current.set(username, []);
      dispatch({ type: "ERROR", username, error: message });
    } finally {
      pendingRef.current.delete(username);
      if (pendingRef.current.size === 0 && !abortRef.current?.signal.aborted) {
        // Merge SisReg results + cached rows (enriched cached rows win in dedup)
        const sisregItems = computeResults();
        const allItems: AnyExportRow[] = [...sisregItems, ...cachedRef.current];
        const unique = deduplicateBySolicitacao(allItems);
        const droppedCount = allItems.length - unique.length;
        dispatch({ type: "MERGE", uniqueCount: unique.length, droppedCount });
        dispatch({ type: "FILTER_DONE", filteredCount: unique.length });

        // If enrichment enabled, enrich first — persist happens AFTER enrich (inside enrichResults)
        if (filtersRef.current?.enrich && unique.length > 0) {
          enrichResults(unique);
        } else {
          // No enrichment — persist raw data now
          if (filtersRef.current?.persist && unique.length > 0) {
            dispatch({ type: "PERSIST_START" });
            try {
              await apiClient.post<PersistExportResponse>(
                "/api/admin/sisreg/schedule-export/persist",
                { items: snakelizeKeys(unique) },
                { signal: abortRef.current?.signal },
              );
              dispatch({ type: "PERSIST_DONE" });
            } catch {
              dispatch({ type: "PERSIST_ERROR" });
            }
          }
          if (filtersRef.current?.enrich) {
            dispatch({ type: "ENRICH_SKIP" });
          }
          dispatch({ type: "COMPLETE" });
        }
      }
    }
  }, [computeResults, enrichResults]);

  const startExport = useCallback(
    (filters: ScheduleExportFilters) => {
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const usernames = filters.usernames;
      filtersRef.current = filters;
      resultsRef.current = new Map();
      enrichedRef.current = [];
      cachedRef.current = [];
      pendingRef.current = new Set(usernames);
      setIsModalOpen(true);
      setIsConfirmed(false);
      dispatch({ type: "START", usernames });

      // Pre-fetch cache if persist enabled, then start operators
      const runPipeline = async () => {
        if (filters.persist) {
          dispatch({ type: "CACHE_START" });
          try {
            const cached = await apiClient.post<CachedExportResponse>(
              "/api/admin/sisreg/schedule-export/cached",
              {
                date_from: filters.dateFrom,
                date_to: filters.dateTo,
                procedure_filter: filters.procedureFilter || null,
              },
              { signal: abortRef.current?.signal },
            );
            cachedRef.current = cached.items;
            dispatch({ type: "CACHE_DONE", count: cached.items.length });
          } catch {
            dispatch({ type: "CACHE_DONE", count: 0 });
          }
        } else {
          dispatch({ type: "CACHE_SKIP" });
        }

        for (const username of usernames) {
          exportOperator(filters, username);
        }
      };

      runPipeline();
    },
    [exportOperator],
  );

  const retryOperator = useCallback(
    (username: string) => {
      if (!filtersRef.current) return;
      if (abortRef.current?.signal.aborted) {
        abortRef.current = new AbortController();
      }
      pendingRef.current.add(username);
      dispatch({ type: "START", usernames: state.operators.map((op) => op.username) });
      for (const op of state.operators) {
        if (op.status === "success" && op.username !== username) {
          dispatch({ type: "SUCCESS", username: op.username, total: op.itemCount });
        }
      }
      exportOperator(filtersRef.current, username);
    },
    [exportOperator, state.operators],
  );

  const retryEnrichment = useCallback(() => {
    const failedCns = [...failedCnsRef.current];
    if (failedCns.length === 0) return;

    const unique = computeResults();
    if (unique.length === 0) return;

    if (!abortRef.current || abortRef.current.signal.aborted) {
      abortRef.current = new AbortController();
    }
    // Retry only the failed CNS subset — preserves existing enrichment results
    enrichResults(unique, failedCns);
  }, [computeResults, enrichResults]);

  const confirmResults = useCallback(() => {
    setIsModalOpen(false);
    setIsConfirmed(true);
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    pendingRef.current.clear();
    dispatch({ type: "CANCEL" });
    setIsModalOpen(false);
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    resultsRef.current = new Map();
    enrichedRef.current = [];
    cachedRef.current = [];
    enrichResultsAccRef.current = {};
    failedCnsRef.current = new Set();
    filtersRef.current = null;
    pendingRef.current = new Set();
    setIsModalOpen(false);
    setIsConfirmed(false);
    dispatch({ type: "RESET" });
  }, []);

  const results = isConfirmed
    ? (enrichedRef.current.length > 0 ? enrichedRef.current : computeResults())
    : [];
  const isExporting = state.operators.length > 0 && !state.isComplete;

  return {
    pipelineState: state,
    results,
    isModalOpen,
    isConfirmed,
    startExport,
    retryOperator,
    retryEnrichment,
    confirmResults,
    cancel,
    reset,
    isExporting,
  };
}
