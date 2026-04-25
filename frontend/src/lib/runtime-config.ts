const DEFAULT_API_BASE = "/api";

export function getApiBase() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE;
}

export function getWebSocketUrl() {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured;

  if (typeof window === "undefined") {
    return "ws://localhost:3000/ws";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}
