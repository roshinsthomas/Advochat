const ACCESS_KEY = "advocate_access";
const REFRESH_KEY = "advocate_refresh";

let refreshPromise = null;

export function clearSession() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function hasSession() {
  return Boolean(sessionStorage.getItem(REFRESH_KEY));
}

async function readResponse(response) {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || (
      data
        ? Object.entries(data)
            .map(([field, value]) =>
              `${field}: ${Array.isArray(value) ? value.join(" ") : value}`
            )
            .join("\n")
        : "Request failed. Check that Django is running."
    );

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

async function publicPost(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return readResponse(response);
}

export async function login(username, password) {
  const tokens = await publicPost("auth/login/", { username, password });

  sessionStorage.setItem(ACCESS_KEY, tokens.access);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function register(details) {
  return publicPost("auth/register/", details);
}

async function refreshAccessToken() {
  const refresh = sessionStorage.getItem(REFRESH_KEY);

  if (!refresh) {
    const error = new Error("Please sign in again.");
    error.status = 401;
    throw error;
  }

  try {
    const tokens = await publicPost("auth/refresh/", { refresh });
    sessionStorage.setItem(ACCESS_KEY, tokens.access);

    if (tokens.refresh) {
      sessionStorage.setItem(REFRESH_KEY, tokens.refresh);
    }
  } catch (error) {
    if (error.status === 401) clearSession();
    throw error;
  }
}

export async function apiRequest(path, options = {}, retry = true) {
  const access = sessionStorage.getItem(ACCESS_KEY);

  const response = await fetch(`/api/${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
  });

  if (response.status === 401 && retry && hasSession()) {
    // Concurrent requests share one token-refresh operation.
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }

    await refreshPromise;
    return apiRequest(path, options, false);
  }

  return readResponse(response);
}

export const getCurrentUser = () => apiRequest("auth/me/");

export const listConversations = (page = 1) =>
  apiRequest(`conversations/?page=${page}`);

export const getConversation = (id) =>
  apiRequest(`conversations/${id}/`);

export const sendQuestion = (query, conversationId) =>
  apiRequest("chat/", {
    method: "POST",
    body: JSON.stringify({
      query,
      limit: 3,
      conversation_id: conversationId,
    }),
  });