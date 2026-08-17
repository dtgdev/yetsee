export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? API_URL;

export class ApiError extends Error {
  status: number;
  path: string;
  detail: string;

  constructor(status: number, path: string, detail: string) {
    super(`API ${status} for ${path}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.detail = detail;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const baseUrl = typeof window === "undefined" ? INTERNAL_API_URL : API_URL;
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { cache: "no-store" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    throw new ApiError(0, path, `Could not reach YetSee API at ${baseUrl}. ${message}`);
  }
  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      // Preserve status text if the response body is not JSON.
    }
    throw new ApiError(response.status, path, detail);
  }
  return response.json() as Promise<T>;
}
