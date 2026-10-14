export const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function fetchJson(url, options) {
  const response = await fetch(url, options);

  if (!response.ok) {
    let detail;

    try {
      const body = await response.json();
      detail = body.detail ? `: ${body.detail}` : "";
    } catch {
      detail = "";
    }

    throw new Error(`${response.status} ${response.statusText}${detail}`);
  }

  return response.json();
}
