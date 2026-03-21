"use client";

import { useCallback, useReducer, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { deduplicateByCode } from "@/lib/utils";
import type { AppointmentListing, SearchFilters } from "@/types/appointment";
import type { OperatorPipelineState, OperatorSearchResponse, PipelineState } from "@/types/pipeline";

// ── Reducer types ──

type Action =
  | { type: "START"; usernames: string[] }
  | { type: "CONNECTING"; username: string }
  | { type: "SEARCHING"; username: string }
  | { type: "SUCCESS"; username: string; items: AppointmentListing[]; total: number }
  | { type: "ERROR"; username: string; error: string }
  | { type: "MERGE"; uniqueCount: number }
  | { type: "CANCEL" }
  | { type: "RESET" };

const initialState: PipelineState = {
  operators: [],
  mergeStatus: "idle",
  filterStatus: "idle",
  enrichStatus: "skipped",
  cacheStatus: "skipped",
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
        isComplete: true,
      };
    case "CANCEL":
      return {
        ...state,
        operators: state.operators.map((op) =>
          op.status === "idle" || op.status === "connecting" || op.status === "searching"
            ? { ...op, status: "cancelled" as const }
            : op,
        ),
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

function buildRequestBody(filters: SearchFilters, username: string): Record<string, unknown> {
  return {
    sol_code: filters.solCode || null,
    patient_cns: filters.patientCns || null,
    patient_name: filters.patientName || null,
    cnes_solicitation: filters.cnesSolicitation || null,
    cnes_execute: filters.cnesExecute || null,
    procedure_unified_code: filters.procedureUnifiedCode || null,
    procedure_internal_code: filters.procedureInternalCode || null,
    procedure_description: filters.procedureDescription || null,
    search_type: filters.searchType,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    situation: filters.situation,
    items_per_page: filters.itemsPerPage,
    profile_type: filters.profileType,
    usernames: [username],
  };
}

// ── Hook ──

export interface UsePipelineSearchReturn {
  pipelineState: PipelineState;
  results: AppointmentListing[];
  isModalOpen: boolean;
  isConfirmed: boolean;
  startSearch: (filters: SearchFilters) => void;
  retryOperator: (username: string) => void;
  confirmResults: () => void;
  cancel: () => void;
  reset: () => void;
  isSearching: boolean;
}

export function usePipelineSearch(): UsePipelineSearchReturn {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const resultsRef = useRef<Map<string, AppointmentListing[]>>(new Map());
  const filtersRef = useRef<SearchFilters | null>(null);
  const pendingRef = useRef<Set<string>>(new Set());
  const abortRef = useRef<AbortController | null>(null);

  const computeResults = useCallback(() => {
    const allItems = Array.from(resultsRef.current.values()).flat();
    return deduplicateByCode(allItems);
  }, []);

  const searchOperator = useCallback(async (filters: SearchFilters, username: string) => {
    const startTime = Date.now();
    dispatch({ type: "CONNECTING", username });

    try {
      const fetchPromise = apiClient.post<OperatorSearchResponse>(
        "/api/admin/sisreg/search-operator",
        buildRequestBody(filters, username),
        { signal: abortRef.current?.signal },
      );

      // Ensure "connecting" phase is visible for at least CONNECTING_DELAY_MS
      const elapsed = Date.now() - startTime;
      if (elapsed < CONNECTING_DELAY_MS) {
        await new Promise((r) => setTimeout(r, CONNECTING_DELAY_MS - elapsed));
      }

      dispatch({ type: "SEARCHING", username });

      const data = await fetchPromise;
      resultsRef.current.set(username, data.items);
      dispatch({ type: "SUCCESS", username, items: data.items, total: data.total });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const message = err instanceof Error ? err.message : "Unknown error";
      resultsRef.current.set(username, []);
      dispatch({ type: "ERROR", username, error: message });
    } finally {
      pendingRef.current.delete(username);
      // Check if all operators are done (and not aborted)
      if (pendingRef.current.size === 0 && !abortRef.current?.signal.aborted) {
        const unique = computeResults();
        dispatch({ type: "MERGE", uniqueCount: unique.length });
      }
    }
  }, [computeResults]);

  const startSearch = useCallback(
    (filters: SearchFilters) => {
      // Abort any previous search
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const usernames = filters.usernames;
      filtersRef.current = filters;
      resultsRef.current = new Map();
      pendingRef.current = new Set(usernames);
      setIsModalOpen(true);
      setIsConfirmed(false);
      dispatch({ type: "START", usernames });

      for (const username of usernames) {
        searchOperator(filters, username);
      }
    },
    [searchOperator],
  );

  const retryOperator = useCallback(
    (username: string) => {
      if (!filtersRef.current) return;
      // If previous controller was aborted, create a new one
      if (abortRef.current?.signal.aborted) {
        abortRef.current = new AbortController();
      }
      pendingRef.current.add(username);
      // Reset merge status since we're re-searching
      dispatch({ type: "START", usernames: state.operators.map((op) => op.username) });
      // Restore existing successful results
      for (const op of state.operators) {
        if (op.status === "success" && op.username !== username) {
          dispatch({
            type: "SUCCESS",
            username: op.username,
            items: resultsRef.current.get(op.username) ?? [],
            total: op.itemCount,
          });
        }
      }
      searchOperator(filtersRef.current, username);
    },
    [searchOperator, state.operators],
  );

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
    filtersRef.current = null;
    pendingRef.current = new Set();
    setIsModalOpen(false);
    setIsConfirmed(false);
    dispatch({ type: "RESET" });
  }, []);

  const results = isConfirmed ? computeResults() : [];
  const isSearching = state.operators.length > 0 && !state.isComplete;

  return {
    pipelineState: state,
    results,
    isModalOpen,
    isConfirmed,
    startSearch,
    retryOperator,
    confirmResults,
    cancel,
    reset,
    isSearching,
  };
}
