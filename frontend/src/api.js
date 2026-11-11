export const API_URL_OVERRIDE_KEY = "codelens.apiUrlOverride";

export function getActiveApiUrl() {
  try {
    const override = localStorage.getItem(API_URL_OVERRIDE_KEY);
    if (override && override.trim()) {
      let trimmed = override.trim();
      if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
        trimmed = `https://${trimmed}`;
      }
      return trimmed.replace(/\/+$/, "");
    }
  } catch {
    // Storage access restricted
  }

  let rawApiUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").trim();
  if (!rawApiUrl.startsWith("http://") && !rawApiUrl.startsWith("https://")) {
    rawApiUrl = `https://${rawApiUrl}`;
  }
  return rawApiUrl.replace(/\/+$/, "");
}

export function saveApiUrlOverride(url) {
  try {
    if (url && url.trim()) {
      localStorage.setItem(API_URL_OVERRIDE_KEY, url.trim());
    } else {
      localStorage.removeItem(API_URL_OVERRIDE_KEY);
    }
  } catch {
    // Storage access restricted
  }
}

export const API_URL = getActiveApiUrl();

export const LLM_STORAGE_KEYS = {
  provider: "codelens.llm.provider",
  apiKey: "codelens.llm.apiKey",
  model: "codelens.llm.model",
};

export function getStoredLlmConfig() {
  try {
    return {
      provider: localStorage.getItem(LLM_STORAGE_KEYS.provider) || "",
      apiKey: localStorage.getItem(LLM_STORAGE_KEYS.apiKey) || "",
      model: localStorage.getItem(LLM_STORAGE_KEYS.model) || "",
    };
  } catch {
    return { provider: "", apiKey: "", model: "" };
  }
}

export function saveStoredLlmConfig(config) {
  try {
    if (config.provider !== undefined) {
      localStorage.setItem(LLM_STORAGE_KEYS.provider, config.provider);
    }
    if (config.apiKey !== undefined) {
      localStorage.setItem(LLM_STORAGE_KEYS.apiKey, config.apiKey);
    }
    if (config.model !== undefined) {
      localStorage.setItem(LLM_STORAGE_KEYS.model, config.model);
    }
  } catch {
    // Storage access restricted
  }
}

export async function fetchJson(url, options = {}) {
  const llmConfig = getStoredLlmConfig();
  const headers = new Headers(options.headers || {});

  if (llmConfig.provider && !headers.has("x-llm-provider")) {
    headers.set("x-llm-provider", llmConfig.provider);
  }
  if (llmConfig.apiKey && !headers.has("x-api-key")) {
    headers.set("x-api-key", llmConfig.apiKey);
  }
  if (llmConfig.model && !headers.has("x-llm-model")) {
    headers.set("x-llm-model", llmConfig.model);
  }

  let finalUrl = url;
  const currentBase = getActiveApiUrl();
  if (url.startsWith(API_URL) && API_URL !== currentBase) {
    finalUrl = url.replace(API_URL, currentBase);
  }

  const response = await fetch(finalUrl, { ...options, headers });

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
