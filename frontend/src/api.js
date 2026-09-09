import { getApiBaseUrl, ADMIN_API_KEY } from "./config";

async function request(path, options = {}) {
  const base = getApiBaseUrl();
  const url = `${base}${path}`;
  const headers = {
    "Accept": "application/json",
    ...(options.headers || {})
  };

  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = jsonSafeStringify(options.body);
  }

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errDetail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errJson.error || errDetail;
      } catch (_) {}
      throw new Error(errDetail);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${url}:`, err);
    throw err;
  }
}

function jsonSafeStringify(obj) {
  return JSON.stringify(obj);
}

// ── Health & Stats ──────────────────────────────────────────────────────────
export async function getRootInfo() {
  return request("/api/info");
}

export async function getGlobalStats() {
  return request("/api/stats", {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
}

export async function getProfileStats(slug, apiKey) {
  return request(`/api/profiles/${slug}/stats`, {
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
}

// ── Profiles ────────────────────────────────────────────────────────────────
export async function getProfiles() {
  const res = await request("/api/profiles", {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
  return res.profiles || [];
}

export async function createProfile(data) {
  return request("/api/profiles", {
    method: "POST",
    headers: { "X-API-Key": ADMIN_API_KEY },
    body: data
  });
}

export async function deleteProfile(slug) {
  return request(`/api/profiles/${slug}`, {
    method: "DELETE",
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
}

export async function clearProfileData(slug, apiKey) {
  return request(`/api/profiles/${slug}/data`, {
    method: "DELETE",
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
}

export async function getTemplates() {
  const res = await request("/api/profiles/templates", {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
  return res.templates || {};
}

// ── Geo Reference ───────────────────────────────────────────────────────────
export async function getStates() {
  const res = await request("/api/states", {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
  return res.all_states || [];
}

export async function getPincodes(state) {
  const res = await request(`/api/states/${encodeURIComponent(state)}/pincodes`, {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
  return res.pincodes || [];
}

// ── Businesses / Leads ──────────────────────────────────────────────────────
export async function getBusinesses(slug, apiKey, params = {}) {
  const query = new URLSearchParams();
  if (params.state) query.append("state", params.state);
  if (params.pincode) query.append("pincode", params.pincode);
  if (params.niche) query.append("niche", params.niche);
  if (params.has_phone !== undefined && params.has_phone !== null) query.append("has_phone", params.has_phone);
  if (params.has_website !== undefined && params.has_website !== null) query.append("has_website", params.has_website);
  if (params.lead_status) query.append("lead_status", params.lead_status);
  query.append("page", params.page || 1);
  query.append("limit", params.limit || 50);

  return request(`/api/profiles/${slug}/businesses?${query.toString()}`, {
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
}

export async function updateLeadStatus(slug, businessId, status, notes, apiKey) {
  const query = new URLSearchParams();
  query.append("lead_status", status);
  if (notes !== undefined && notes !== null) query.append("notes", notes);

  return request(`/api/profiles/${slug}/businesses/${businessId}/status?${query.toString()}`, {
    method: "PATCH",
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
}

// ── Scraping Engine ─────────────────────────────────────────────────────────
export async function startScraping(data) {
  return request("/api/scrape/start", {
    method: "POST",
    body: data
  });
}

export async function getScrapeStatus() {
  return request("/api/scrape/status");
}

export async function stopScraping() {
  return request("/api/scrape/stop", {
    method: "POST"
  });
}

// ── Phone Enrichment ─────────────────────────────────────────────────────────
export async function startPhoneEnrichment(slug, apiKey, businessIds = null) {
  return request(`/api/profiles/${slug}/enrich-phones`, {
    method: "POST",
    headers: { "X-API-Key": apiKey },
    body: businessIds ? { business_ids: businessIds } : {}
  });
}

export async function getEnrichmentStatus(slug, apiKey) {
  return request(`/api/profiles/${slug}/enrich-phones/status`, {
    headers: { "X-API-Key": apiKey }
  });
}

export async function stopEnrichment(slug, apiKey) {
  return request(`/api/profiles/${slug}/enrich-phones/stop`, {
    method: "POST",
    headers: { "X-API-Key": apiKey }
  });
}

// ── Users & Approvals ───────────────────────────────────────────────────────
export async function getApiUsers(status) {
  const query = status ? `?status=${status}` : "";
  const res = await request(`/api/admin/users${query}`, {
    headers: { "X-API-Key": ADMIN_API_KEY }
  });
  return res.users || [];
}

export async function updateUserStatus(userCode, status) {
  return request(`/api/admin/users/${userCode}/status`, {
    method: "PATCH",
    headers: { "X-API-Key": ADMIN_API_KEY },
    body: { status }
  });
}

export async function registerUser(data) {
  return request("/api/users/register", {
    method: "POST",
    body: data
  });
}

export async function checkUserStatus(userCode) {
  return request(`/api/users/status/${userCode}`);
}

export async function fetchBatchDelivery(userCode) {
  return request("/api/data/batch", {
    headers: { "X-User-Code": userCode }
  });
}

// ── Job History ─────────────────────────────────────────────────────────────
export async function getJobHistory(slug, apiKey) {
  const res = await request(`/api/profiles/${slug}/jobs`, {
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
  return res.jobs || [];
}

export async function getProfileCoverage(slug, apiKey) {
  return request(`/api/profiles/${slug}/coverage`, {
    headers: { "X-API-Key": apiKey || ADMIN_API_KEY }
  });
}

export function getExportCsvUrl(slug, apiKey, state, niche) {
  const base = getApiBaseUrl();
  const query = new URLSearchParams();
  if (state) query.append("state", state);
  if (niche) query.append("niche", niche);
  return `${base}/api/profiles/${slug}/export/csv?${query.toString()}`;
}
