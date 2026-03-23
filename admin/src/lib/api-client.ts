import { ApiError } from "./api-error";
import { camelizeKeys } from "./utils";

const REQUEST_TIMEOUT_MS = 30_000;

class ApiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const key = process.env.NEXT_PUBLIC_API_KEY;
    if (!key) {
      throw new Error("NEXT_PUBLIC_API_KEY is required but was not provided");
    }
    this.apiKey = key;
  }

  private headers(): HeadersInit {
    return {
      "X-API-Key": this.apiKey,
      "Content-Type": "application/json",
    };
  }

  private buildUrl(path: string, params?: Record<string, string | undefined>): string {
    const url = new URL(path, this.baseUrl);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== "") {
          url.searchParams.set(key, value);
        }
      }
    }
    return url.toString();
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let detail: string | undefined;
      try {
        const body = await response.json();
        const rawDetail = body.detail ?? body.message;
        if (typeof rawDetail === "string") {
          detail = rawDetail;
        } else if (Array.isArray(rawDetail)) {
          detail = rawDetail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ");
        }
      } catch {
        // ignore parse errors
      }
      throw new ApiError(response.status, `HTTP ${response.status}`, detail);
    }
    const json = await response.json();
    return camelizeKeys<T>(json);
  }

  async get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
    const url = this.buildUrl(path, params);
    const response = await fetch(url, {
      method: "GET",
      headers: this.headers(),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(path: string, body?: unknown, options?: { signal?: AbortSignal }): Promise<T> {
    const url = this.buildUrl(path);
    const timeoutSignal = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
    const combinedSignal = options?.signal
      ? AbortSignal.any([options.signal, timeoutSignal])
      : timeoutSignal;
    const response = await fetch(url, {
      method: "POST",
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      signal: combinedSignal,
    });
    return this.handleResponse<T>(response);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "PUT",
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    return this.handleResponse<T>(response);
  }

  async delete(path: string): Promise<void> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "DELETE",
      headers: this.headers(),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}`);
    }
  }

  async postBlob(path: string, body?: unknown): Promise<Blob> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "POST",
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}`);
    }
    return response.blob();
  }

  async getBlob(path: string, params?: Record<string, string | undefined>): Promise<Blob> {
    const url = this.buildUrl(path, params);
    const response = await fetch(url, {
      method: "GET",
      headers: { "X-API-Key": this.apiKey },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}`);
    }
    return response.blob();
  }
}

export const apiClient = new ApiClient();
