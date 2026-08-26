import { apiUrl } from "@/lib/env";

type ApiErrorPayload = {
  error?: { code?: string; message?: string };
  detail?: string;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiRequestOptions = RequestInit & { token?: string };

/** Central server-side client for the FastAPI application. */
export async function apiRequest<T>(
  path: string,
  { token, ...init }: ApiRequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${apiUrl()}${path}`, {
      ...init,
      headers,
      cache: init.cache ?? "no-store",
      signal: init.signal ?? AbortSignal.timeout(10_000),
    });
  } catch {
    throw new ApiError(503, "A API está indisponível no momento.");
  }

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      // Some infrastructure errors have no JSON body.
    }
    throw new ApiError(
      response.status,
      payload.error?.message ?? payload.detail ?? "Não foi possível concluir a solicitação.",
      payload.error?.code,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
