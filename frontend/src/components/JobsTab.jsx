import React, { useState, useEffect } from "react";
import { History, CheckCircle, RefreshCw, Loader2, Calendar, MapPin } from "lucide-react";
import { getJobHistory } from "../api";

export default function JobsTab({ activeProfile }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchJobs = async () => {
    if (!activeProfile) return;
    setLoading(true);
    try {
      const data = await getJobHistory(activeProfile.slug, activeProfile.api_key);
      setJobs(data || []);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [activeProfile]);

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>📜</span> Scraping Job Execution History
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Log of all completed pincode & niche combinations previously extracted.
          </p>
        </div>

        <button
          onClick={fetchJobs}
          className="text-xs px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Log
        </button>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-16 text-center text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
            Loading job logs...
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-16 text-center text-slate-500 text-xs">
            No completed scraping jobs recorded for this profile yet.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-950 text-slate-400 sticky top-0 z-10 border-b border-slate-800">
                <tr>
                  <th className="p-3.5 font-semibold">State / Region</th>
                  <th className="p-3.5 font-semibold">Pincode</th>
                  <th className="p-3.5 font-semibold">Niche Category</th>
                  <th className="p-3.5 font-semibold">Results Scraped</th>
                  <th className="p-3.5 font-semibold">Execution Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-850/50 transition">
                    <td className="p-3.5 font-bold text-white">{j.state}</td>
                    <td className="p-3.5 font-mono text-emerald-400 font-semibold">{j.pincode}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
                        {j.niche}
                      </span>
                    </td>
                    <td className="p-3.5 font-mono text-white">
                      <strong>{j.results_count || 0}</strong> businesses
                    </td>
                    <td className="p-3.5 text-slate-400 font-mono text-[11px]">
                      {j.scraped_at ? new Date(j.scraped_at).toLocaleString() : "—"}
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
