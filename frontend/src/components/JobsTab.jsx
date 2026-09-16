import React, { useState, useEffect, useCallback } from "react";
import {
  History, RefreshCw, Loader2, MapPin, Phone, Globe,
  Send, ChevronDown, ChevronRight, RotateCcw, AlertCircle, CheckCircle2
} from "lucide-react";
import { getPincodeStats, rescrapePin } from "../api";

export default function JobsTab({ activeProfile }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedStates, setExpandedStates] = useState({});
  const [rescrapingPin, setRescrapingPin] = useState(null);
  const [rescrapeMsgs, setRescrapeMsgs] = useState({});
  const [error, setError] = useState("");

  const fetchStats = useCallback(async () => {
    if (!activeProfile) return;
    setLoading(true);
    setError("");
    try {
      const res = await getPincodeStats(activeProfile.slug, activeProfile.api_key);
      setData(res);
      // Auto-expand all states on first load
      if (res?.states) {
        const expanded = {};
        Object.keys(res.states).forEach(s => { expanded[s] = true; });
        setExpandedStates(expanded);
      }
    } catch (err) {
      setError("Failed to load pincode stats: " + err.message);
    } finally {
      setLoading(false);
    }
  }, [activeProfile]);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const toggleState = (state) => {
    setExpandedStates(prev => ({ ...prev, [state]: !prev[state] }));
  };

  const handleRescrape = async (pincode) => {
    if (!activeProfile) return;
    setRescrapingPin(pincode);
    setRescrapeMsgs(prev => ({ ...prev, [pincode]: null }));
    try {
      const res = await rescrapePin(activeProfile.slug, activeProfile.api_key, pincode);
      setRescrapeMsgs(prev => ({ ...prev, [pincode]: { ok: res.success, msg: res.message } }));
    } catch (err) {
      setRescrapeMsgs(prev => ({ ...prev, [pincode]: { ok: false, msg: err.message } }));
    } finally {
      setRescrapingPin(null);
    }
  };

  const states = data?.states ? Object.entries(data.states) : [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            Coverage Tracker — State-wise Pincode Report
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Live breakdown of every scraped pincode — businesses, phones, websites, sent/unsent, lead status & re-scrape.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data && (
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="text-white font-bold">{data.total_pincodes}</span> pincodes
              <span className="text-white font-bold">{data.total_businesses?.toLocaleString()}</span> total businesses
            </div>
          )}
          <button
            onClick={fetchStats}
            className="text-xs px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-slate-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
          Loading pincode stats...
        </div>
      ) : !activeProfile ? (
        <div className="py-20 text-center text-slate-500 text-xs">Select a profile to view coverage.</div>
      ) : states.length === 0 ? (
        <div className="py-20 text-center text-slate-500 text-xs">No scraped data yet for this profile.</div>
      ) : (
        <div className="space-y-4">
          {states.map(([stateName, pincodes]) => {
            const stateTotal = pincodes.reduce((a, p) => a + (p.total || 0), 0);
            const stateSent = pincodes.reduce((a, p) => a + (p.sent_count || 0), 0);
            const statePhone = pincodes.reduce((a, p) => a + (p.with_phone || 0), 0);
            const isOpen = expandedStates[stateName];

            return (
              <div key={stateName} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                {/* State Header Row */}
                <button
                  className="w-full flex items-center justify-between p-4 hover:bg-slate-800/60 transition text-left"
                  onClick={() => toggleState(stateName)}
                >
                  <div className="flex items-center gap-3">
                    {isOpen ? <ChevronDown className="w-4 h-4 text-emerald-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                    <MapPin className="w-4 h-4 text-emerald-400" />
                    <span className="font-bold text-white text-sm">{stateName}</span>
                    <span className="text-[11px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                      {pincodes.length} pincodes
                    </span>
                  </div>
                  <div className="hidden sm:flex items-center gap-5 text-xs text-slate-400">
                    <span><span className="text-white font-bold">{stateTotal.toLocaleString()}</span> businesses</span>
                    <span><span className="text-emerald-400 font-bold">{statePhone.toLocaleString()}</span> with phone</span>
                    <span><span className="text-blue-400 font-bold">{stateSent.toLocaleString()}</span> sent</span>
                  </div>
                </button>

                {/* Pincode Cards */}
                {isOpen && (
                  <div className="border-t border-slate-800 divide-y divide-slate-800/60">
                    {pincodes.map((pc) => {
                      const sentPct = pc.total > 0 ? Math.round((pc.sent_count / pc.total) * 100) : 0;
                      const phonePct = pc.total > 0 ? Math.round((pc.with_phone / pc.total) * 100) : 0;
                      const msg = rescrapeMsgs[pc.pincode];

                      return (
                        <div key={pc.pincode} className="p-4 hover:bg-slate-800/30 transition">
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                            {/* Left: Pincode + metrics */}
                            <div className="flex-1 space-y-3">
                              <div className="flex items-center gap-3 flex-wrap">
                                <span className="font-mono font-bold text-emerald-400 text-sm">{pc.pincode}</span>
                                <span className="text-[11px] text-slate-400">
                                  Last scraped: {pc.last_scraped ? new Date(pc.last_scraped).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                                </span>
                              </div>

                              {/* Stat Pills */}
                              <div className="flex flex-wrap gap-2">
                                <StatPill label="Total" value={pc.total} color="slate" />
                                <StatPill icon={<Phone className="w-3 h-3" />} label="With Phone" value={`${pc.with_phone} (${phonePct}%)`} color="emerald" />
                                <StatPill icon={<Globe className="w-3 h-3" />} label="With Website" value={pc.with_website} color="blue" />
                                <StatPill icon={<Send className="w-3 h-3" />} label="Sent" value={`${pc.sent_count} (${sentPct}%)`} color="violet" />
                                <StatPill label="Unsent" value={pc.unsent_count} color="amber" />
                              </div>

                              {/* Sent progress bar */}
                              {pc.total > 0 && (
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden max-w-xs">
                                    <div
                                      className="h-full bg-violet-500 rounded-full transition-all"
                                      style={{ width: `${sentPct}%` }}
                                    />
                                  </div>
                                  <span className="text-[10px] text-slate-500">{sentPct}% delivered</span>
                                </div>
                              )}

                              {/* Lead Status Breakdown */}
                              {pc.lead_status_breakdown && Object.keys(pc.lead_status_breakdown).length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mt-1">
                                  {Object.entries(pc.lead_status_breakdown).map(([status, cnt]) => (
                                    <span
                                      key={status}
                                      className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300"
                                    >
                                      {status}: <strong>{cnt}</strong>
                                    </span>
                                  ))}
                                </div>
                              )}

                              {/* Scraped Niches */}
                              {pc.scraped_niches && pc.scraped_niches.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {pc.scraped_niches.slice(0, 6).map((n) => (
                                    <span key={n} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                                      {n}
                                    </span>
                                  ))}
                                  {pc.scraped_niches.length > 6 && (
                                    <span className="text-[10px] text-slate-500">+{pc.scraped_niches.length - 6} more</span>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Right: Re-scrape button */}
                            <div className="flex flex-col items-end gap-2 shrink-0">
                              <button
                                onClick={() => handleRescrape(pc.pincode)}
                                disabled={rescrapingPin === pc.pincode}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition disabled:opacity-50"
                              >
                                {rescrapingPin === pc.pincode ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <RotateCcw className="w-3.5 h-3.5" />
                                )}
                                Re-Scrape
                              </button>
                              {msg && (
                                <div className={`flex items-center gap-1 text-[11px] font-medium ${msg.ok ? "text-emerald-400" : "text-rose-400"}`}>
                                  {msg.ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                  {msg.msg}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatPill({ icon, label, value, color }) {
  const colors = {
    slate: "bg-slate-800 text-slate-300 border-slate-700",
    emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    blue: "bg-blue-500/10 text-blue-300 border-blue-500/30",
    violet: "bg-violet-500/10 text-violet-300 border-violet-500/30",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  };
  return (
    <div className={`flex items-center gap-1 px-2 py-1 rounded-lg border text-[11px] font-medium ${colors[color] || colors.slate}`}>
      {icon}
      <span className="text-slate-400">{label}:</span>
      <span className="font-bold">{value}</span>
    </div>
  );
}
