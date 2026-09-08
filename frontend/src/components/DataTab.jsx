import React, { useState, useEffect, useRef } from "react";
import { 
  Download, Search, Phone, Globe, Star, ExternalLink,
  Loader2, RefreshCw, Zap, StopCircle, CheckCircle2, XCircle
} from "lucide-react";
import { getBusinesses, getExportCsvUrl, getStates,
         startPhoneEnrichment, getEnrichmentStatus, stopEnrichment } from "../api";

export default function DataTab({ activeProfile }) {
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState("");
  const [selectedNiche, setSelectedNiche] = useState("");

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

  // Poll enrichment status while running
  const startEnrichPoll = () => {
    if (enrichPollRef.current) return;
    enrichPollRef.current = setInterval(async () => {
      if (!activeProfile) return;
      try {
        const s = await getEnrichmentStatus(activeProfile.slug, activeProfile.api_key);
        setEnrichStatus(s);
        if (s.status !== "running") {
          clearInterval(enrichPollRef.current);
          enrichPollRef.current = null;
          fetchRecords(); // refresh table with newly found numbers
        } else {
          // Refresh table every ~24s during enrichment (every 3 polls)
          if (s.done % 3 === 0) fetchRecords();
        }
      } catch (_) {}
    }, 8000);
  };

  useEffect(() => {
    return () => {
      if (enrichPollRef.current) clearInterval(enrichPollRef.current);
    };
  }, []);

  const handleStartEnrich = async () => {
    if (!activeProfile) return;
    setEnrichMsg("Starting enrichment...");
    try {
      const res = await startPhoneEnrichment(activeProfile.slug, activeProfile.api_key);
      if (res.success) {
        setEnrichMsg(`✅ ${res.message}`);
        setEnrichStatus({ status: "running", total: res.total, done: 0, found: 0, progress_percent: 0 });
        startEnrichPoll();
      } else {
        setEnrichMsg(`⚠️ ${res.message}`);
        // If already running, start polling
        if (res.message?.includes("already running")) {
          setEnrichStatus(res.status || null);
          startEnrichPoll();
        }
      }
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

  const filtered = businesses.filter((b) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const str = [
      b.name, b.niche, b.phone, b.phone_2, b.pincode, b.state, b.rating
    ].filter(Boolean).join(" ").toLowerCase();
    return str.includes(q);
  });

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
            Browse verified business records from Aiven MySQL and download high-resolution CSV datasets.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
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
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                enrichStatus.status === "running" ? "bg-violet-900 text-violet-300" :
                enrichStatus.status === "completed" ? "bg-emerald-900 text-emerald-300" :
                enrichStatus.status === "error" ? "bg-red-900 text-red-300" :
                "bg-slate-800 text-slate-400"
              }`}>
                {enrichStatus.status?.toUpperCase()}
              </span>
            )}
          </div>

          {enrichMsg && (
            <p className="text-xs text-slate-400">{enrichMsg}</p>
          )}

          {enrichStatus && enrichStatus.total > 0 && (
            <>
              {/* Progress bar */}
              <div className="w-full bg-slate-800 rounded-full h-2">
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
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
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
      </div>

      {/* Data Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Showing <strong>{filtered.length}</strong> matching records</span>
          <button onClick={fetchRecords} className="hover:text-white flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-16 text-center text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
            Loading business data...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center text-slate-500 text-xs">
            No businesses found in database matching your criteria.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-950 text-slate-400 sticky top-0 z-10 border-b border-slate-800">
                <tr>
                  <th className="p-3.5 font-semibold">Business Name</th>
                  <th className="p-3.5 font-semibold">Niche</th>
                  <th className="p-3.5 font-semibold">Location</th>
                  <th className="p-3.5 font-semibold">Phone Numbers</th>
                  <th className="p-3.5 font-semibold">Rating / Reviews</th>
                  <th className="p-3.5 font-semibold">Website</th>
                  <th className="p-3.5 font-semibold">Maps</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filtered.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-850/50 transition">
                    <td className="p-3.5 font-bold text-white max-w-[220px] truncate">{b.name}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
                        {b.niche}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-400">
                      {b.pincode} {b.state ? `(${b.state})` : ""}
                    </td>
                    <td className="p-3.5 font-mono">
                      {b.phone && b.phone !== "N/A" ? (
                        <a href={`tel:${b.phone}`} className="text-emerald-400 hover:underline">
                          {b.phone}
                        </a>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                      {b.phone_2 && <div className="text-[10px] text-slate-500">{b.phone_2}</div>}
                    </td>
                    <td className="p-3.5 text-amber-400">
                      ★ {b.rating || "N/A"} <span className="text-slate-500 font-normal">({b.reviews || 0})</span>
                    </td>
                    <td className="p-3.5">
                      {b.website_link && b.website_link !== "N/A" ? (
                        <a href={b.website_link} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                          🔗 Link
                        </a>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="p-3.5">
                      {b.maps_url ? (
                        <a href={b.maps_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                          🗺️ View
                        </a>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
