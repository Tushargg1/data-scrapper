import React, { useState, useEffect, useRef } from "react";
import { 
  Download, Search, Phone, Globe, Star, ExternalLink,
  Loader2, RefreshCw, Zap, StopCircle, CheckCircle2, XCircle,
  Copy, Check, Trash2
} from "lucide-react";
import { getBusinesses, getExportCsvUrl, getStates,
         startPhoneEnrichment, getEnrichmentStatus, stopEnrichment,
         clearProfileData } from "../api";

export default function DataTab({ activeProfile, onDataChanged }) {
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [clearingData, setClearingData] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [search, setSearch] = useState("");
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState("");
  const [selectedNiche, setSelectedNiche] = useState("");
  const [deliveryFilter, setDeliveryFilter] = useState("all"); // "all" | "sent" | "unsent"

  // Enrichment state
  const [enrichStatus, setEnrichStatus] = useState(null); // null | status object
  const [enrichMsg, setEnrichMsg] = useState("");
  const enrichPollRef = useRef(null);

  const fetchRecords = async () => {
    if (!activeProfile) return;
    setLoading(true);
    try {
      const res = await getBusinesses(activeProfile.slug, activeProfile.api_key, {
        limit: 300,
        state: selectedState || undefined,
        niche: selectedNiche || undefined
      });
      setBusinesses(res.businesses || []);
    } catch (err) {
      console.error("Failed to load businesses:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getStates().then((s) => setStates(s || []));
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [activeProfile, selectedState, selectedNiche]);

  // Poll enrichment status if running
  useEffect(() => {
    if (!activeProfile) return;
    enrichPollRef.current = setInterval(async () => {
      try {
        const st = await getEnrichmentStatus(activeProfile.slug, activeProfile.api_key);
        setEnrichStatus(st);
        if (st && st.status === "completed") {
          fetchRecords(); // refresh records to show newly found phones
        }
      } catch (err) {
        // ignore poll errors
      }
    }, 2000);
    return () => clearInterval(enrichPollRef.current);
  }, [activeProfile]);

  const handleStartEnrich = async () => {
    if (!activeProfile) return;
    setEnrichMsg("");
    try {
      const res = await startPhoneEnrichment(activeProfile.slug, activeProfile.api_key);
      setEnrichMsg(res.message || "Enrichment started.");
    } catch (err) {
      setEnrichMsg(`❌ Error: ${err.message}`);
    }
  };

  const handleStopEnrich = async () => {
    if (!activeProfile) return;
    try {
      await stopEnrichment(activeProfile.slug, activeProfile.api_key);
      setEnrichMsg("⏹ Stop signal sent.");
    } catch (err) {
      setEnrichMsg(`❌ ${err.message}`);
    }
  };

  const handleCopyMap = (url, id) => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearAllData = async () => {
    if (!activeProfile) return;
    if (!window.confirm(`⚠️ Are you sure you want to delete ALL scraped records for profile "${activeProfile.name}"?\n\nThis will permanently wipe all business records and job history so you can start a fresh extraction.`)) {
      return;
    }
    setClearingData(true);
    try {
      await clearProfileData(activeProfile.slug, activeProfile.api_key);
      await fetchRecords();
      if (onDataChanged) onDataChanged();
      alert("✅ All old data deleted successfully. You can now start fresh extraction!");
    } catch (err) {
      alert(err.message || "Failed to delete data.");
    } finally {
      setClearingData(false);
    }
  };

  const filtered = businesses.filter((b) => {
    if (deliveryFilter === "sent" && !b.is_sent) return false;
    if (deliveryFilter === "unsent" && b.is_sent) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    const str = [
      b.name, b.niche, b.phone, b.phone_2, b.pincode, b.state, b.rating, b.sent_to_user_code,
      b.is_sent ? "sent" : "unsent"
    ].filter(Boolean).join(" ").toLowerCase();
    return str.includes(q);
  });

  // Group by pincode: unsent first (sorted by id ASC = oldest first), then sent (id ASC)
  const grouped = {};
  filtered.forEach((b) => {
    const key = `${b.pincode}||${b.state}`;
    if (!grouped[key]) grouped[key] = { pincode: b.pincode, state: b.state, unsent: [], sent: [] };
    if (b.is_sent) grouped[key].sent.push(b);
    else grouped[key].unsent.push(b);
  });
  // Sort each group internally by id ASC (oldest scraped at top for unsent, bottom for sent)
  Object.values(grouped).forEach(g => {
    g.unsent.sort((a, b) => a.id - b.id);
    g.sent.sort((a, b) => a.id - b.id);
  });
  // Sort pincode groups by pincode number
  const groupedList = Object.values(grouped).sort((a, b) => (a.pincode || "").localeCompare(b.pincode || ""));

  const exportUrl = activeProfile 
    ? getExportCsvUrl(activeProfile.slug, activeProfile.api_key, selectedState, selectedNiche)
    : "#";

  return (
    <div className="space-y-6">
      
      {/* Header & Export Actions */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>📋</span> Data Explorer & Export
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Grouped by pincode — unsent leads on top (oldest first), sent leads at bottom.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Clear / Delete All Data button */}
          <button
            onClick={handleClearAllData}
            disabled={clearingData}
            title="Delete all scraped data for this profile to start fresh"
            className="bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800/60 text-rose-300 hover:text-white text-xs font-semibold px-3.5 py-2.5 rounded-xl transition flex items-center gap-2 disabled:opacity-50"
          >
            {clearingData ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4 text-rose-400" />}
            Clear All Data
          </button>

          {/* Find Missing Phones button */}
          {enrichStatus?.status === "running" ? (
            <button
              onClick={handleStopEnrich}
              className="bg-red-600 hover:bg-red-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
            >
              <StopCircle className="w-4 h-4" /> Stop Enrichment
            </button>
          ) : (
            <button
              onClick={handleStartEnrich}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-violet-500/20 transition flex items-center gap-2"
            >
              <Zap className="w-4 h-4" /> Find Missing Phones
            </button>
          )}
          <a
            href={exportUrl}
            target="_blank"
            rel="noreferrer"
            className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-emerald-500/20 transition flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Download Complete CSV
          </a>
        </div>
      </div>

      {/* Phone Enrichment Progress Panel */}
      {(enrichStatus || enrichMsg) && (
        <div className="bg-slate-900 border border-violet-800/50 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-violet-300 flex items-center gap-2">
              <Zap className="w-4 h-4" /> Phone Enrichment
              {enrichStatus?.status === "running" && (
                <Loader2 className="w-3.5 h-3.5 animate-spin ml-1 text-violet-400" />
              )}
              {enrichStatus?.status === "completed" && (
                <CheckCircle2 className="w-3.5 h-3.5 ml-1 text-emerald-400" />
              )}
              {enrichStatus?.status === "stopped" && (
                <XCircle className="w-3.5 h-3.5 ml-1 text-amber-400" />
              )}
            </h3>
            {enrichStatus && (
              <button onClick={() => setEnrichStatus(null)} className="text-slate-500 hover:text-white text-xs">✕</button>
            )}
          </div>

          {enrichMsg && (
            <p className="text-xs text-slate-300">{enrichMsg}</p>
          )}

          {enrichStatus && (
            <>
              {/* Progress bar */}
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-violet-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${enrichStatus.progress_percent || 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>
                  Checked <strong className="text-white">{enrichStatus.done}</strong> / {enrichStatus.total} businesses
                </span>
                <span className="text-emerald-400 font-semibold">
                  ✅ {enrichStatus.found} numbers found
                </span>
              </div>

              {/* Currently searching */}
              {enrichStatus.status === "running" && enrichStatus.current_name && (
                <p className="text-xs text-slate-500">
                  Searching <span className="text-slate-300">{enrichStatus.current_name}</span>
                  {enrichStatus.current_source && (
                    <span className="ml-1 text-violet-400">via {enrichStatus.current_source}</span>
                  )}...
                </p>
              )}

              {/* Recent finds */}
              {enrichStatus.recent_found?.length > 0 && (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Recently found:</p>
                  {enrichStatus.recent_found.map((r, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-1.5 text-xs">
                      <span className="text-slate-300 truncate max-w-[200px]">{r.name}</span>
                      <span className="text-emerald-400 font-mono ml-2">{r.phone}</span>
                      <span className="text-slate-600 ml-2 text-[10px]">{r.source}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Filter Row */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search within loaded records..."
            className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        {/* State Filter */}
        <div>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All States</option>
            {states.map((st) => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>

        {/* Niche Filter */}
        <div>
          <select
            value={selectedNiche}
            onChange={(e) => setSelectedNiche(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Niches</option>
            {activeProfile?.niches && activeProfile.niches.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        {/* Delivery Filter */}
        <div>
          <select
            value={deliveryFilter}
            onChange={(e) => setDeliveryFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-medium"
          >
            <option value="all">All Delivery Statuses</option>
            <option value="sent">🟢 Sent Only</option>
            <option value="unsent">⚪ Unsent Only</option>
          </select>
        </div>
      </div>

      {/* Summary bar */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          <strong className="text-white">{filtered.length}</strong> records across{" "}
          <strong className="text-white">{groupedList.length}</strong> pincode{groupedList.length !== 1 ? "s" : ""}
          {" · "}
          <span className="text-slate-500">{filtered.filter(b => !b.is_sent).length} unsent</span>
          {" · "}
          <span className="text-emerald-400">{filtered.filter(b => b.is_sent).length} sent</span>
        </span>
        <button onClick={fetchRecords} className="hover:text-white flex items-center gap-1">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Pincode-grouped Data */}
      {loading ? (
        <div className="p-16 text-center text-slate-400 text-xs bg-slate-900 border border-slate-800 rounded-2xl">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
          Loading business data...
        </div>
      ) : groupedList.length === 0 ? (
        <div className="p-16 text-center text-slate-500 text-xs bg-slate-900 border border-slate-800 rounded-2xl">
          No businesses found matching your criteria.
        </div>
      ) : (
        <div className="space-y-4">
          {groupedList.map(({ pincode, state, unsent, sent }) => (
            <div key={`${pincode}-${state}`} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              {/* Pincode Header */}
              <div className="px-5 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-white font-mono">📍 {pincode}</span>
                  <span className="text-xs text-slate-400">{state}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-400">{unsent.length} unsent</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-emerald-400">{sent.length} sent</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-slate-300 font-semibold">{unsent.length + sent.length} total</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3 font-semibold">Status</th>
                      <th className="p-3 font-semibold">Business Name</th>
                      <th className="p-3 font-semibold">Niche</th>
                      <th className="p-3 font-semibold">Phone</th>
                      <th className="p-3 font-semibold">Rating</th>
                      <th className="p-3 font-semibold">Website</th>
                      <th className="p-3 font-semibold">Maps</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {/* UNSENT ROWS — top, white background */}
                    {unsent.map((b) => (
                      <BusinessRow key={b.id} b={b} copiedId={copiedId} onCopy={handleCopyMap} />
                    ))}
                    {/* Divider between unsent and sent */}
                    {unsent.length > 0 && sent.length > 0 && (
                      <tr>
                        <td colSpan={7} className="px-3 py-1.5 bg-emerald-950/30 border-y border-emerald-800/30 text-[10px] text-emerald-400/70 font-semibold tracking-wider uppercase">
                          ↓ Sent leads — already delivered to telecallers
                        </td>
                      </tr>
                    )}
                    {/* SENT ROWS — bottom, green tinted */}
                    {sent.map((b) => (
                      <BusinessRow key={b.id} b={b} copiedId={copiedId} onCopy={handleCopyMap} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

function BusinessRow({ b, copiedId, onCopy }) {
  return (
    <tr
      className={`transition ${
        b.is_sent
          ? "bg-emerald-950/20 hover:bg-emerald-900/30 border-l-4 border-l-emerald-500"
          : "hover:bg-slate-850/50 border-l-4 border-l-transparent"
      }`}
    >
      <td className="p-3 whitespace-nowrap">
        {b.is_sent ? (
          <span
            title={b.sent_to_user_code ? `Delivered to ${b.sent_to_user_code}` : "Delivered"}
            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-bold text-[10px]"
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>Sent</span>
            {b.sent_to_user_code && (
              <span className="text-[9px] font-mono text-emerald-300/80 bg-emerald-900/60 px-1 py-0.5 rounded">
                {b.sent_to_user_code}
              </span>
            )}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
            <span>Unsent</span>
          </span>
        )}
      </td>
      <td className={`p-3 font-bold max-w-[200px] truncate ${b.is_sent ? "text-emerald-200" : "text-white"}`}>{b.name}</td>
      <td className="p-3">
        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">{b.niche}</span>
      </td>
      <td className="p-3 font-mono">
        {b.phone && b.phone !== "N/A" ? (
          <a href={`tel:${b.phone}`} className="text-emerald-400 hover:underline">{b.phone}</a>
        ) : (
          <span className="text-slate-600">—</span>
        )}
        {b.phone_2 && b.phone_2 !== "N/A" &&
         (b.phone?.replace(/\D/g, '').slice(-10) !== b.phone_2?.replace(/\D/g, '').slice(-10)) && (
          <div className="text-[10px] text-teal-400 mt-0.5">
            <a href={`tel:${b.phone_2}`} className="hover:underline">{b.phone_2}</a>
          </div>
        )}
      </td>
      <td className="p-3 text-amber-400 whitespace-nowrap">
        ★ {b.rating || "N/A"} <span className="text-slate-500 font-normal">({b.reviews || 0})</span>
      </td>
      <td className="p-3">
        {b.website_link && b.website_link !== "N/A" && !b.website_link.includes("google.") && !b.website_link.includes("gstatic.") ? (
          <a href={b.website_link} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline flex items-center gap-1">
            <Globe className="w-3 h-3 shrink-0" /><span>Visit</span>
          </a>
        ) : (
          <span className="text-slate-600">—</span>
        )}
      </td>
      <td className="p-3">
        {b.maps_url && b.maps_url.startsWith("http") ? (
          <div className="flex items-center gap-1.5">
            <a
              href={b.maps_url}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 hover:text-indigo-300 hover:underline text-[11px] flex items-center gap-1"
            >
              <ExternalLink className="w-3 h-3 shrink-0" /><span>Maps</span>
            </a>
            <button
              onClick={() => onCopy(b.maps_url, b.id)}
              title="Copy Google Maps URL"
              className="p-1 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-200 transition"
            >
              {copiedId === b.id ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </button>
          </div>
        ) : (
          <span className="text-slate-600">—</span>
        )}
      </td>
    </tr>
  );
}
