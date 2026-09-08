import React, { useState, useEffect } from "react";
import { 
  Download, Search, Filter, Database, FileSpreadsheet, 
  Phone, Globe, Star, ExternalLink, Loader2, RefreshCw 
} from "lucide-react";
import { getBusinesses, getExportCsvUrl, getStates } from "../api";

export default function DataTab({ activeProfile }) {
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState("");
  const [selectedNiche, setSelectedNiche] = useState("");

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

        <div className="flex items-center gap-3">
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
