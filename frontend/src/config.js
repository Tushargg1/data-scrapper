// Configuration for API endpoint
export const DEFAULT_API_URL = "https://data-scrapper-n7ua.onrender.com";
export const ADMIN_API_KEY = "admin-secret-key-change-me-2024";

export function getApiBaseUrl() {
  const saved = localStorage.getItem("custom_api_url");
  if (saved && saved.trim()) {
    return saved.trim().replace(/\/$/, "");
  }
  // Check if running on localhost dev
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    // If local dev, default to localhost:8000 or Render if localhost is not active
    const localPreferred = localStorage.getItem("prefer_local_api");
    if (localPreferred === "1") {
      return "http://localhost:8000";
    }
  }
  return DEFAULT_API_URL;
}

export function setApiBaseUrl(url) {
  if (!url || !url.trim()) {
    localStorage.removeItem("custom_api_url");
  } else {
    localStorage.setItem("custom_api_url", url.trim().replace(/\/$/, ""));
  }
}
