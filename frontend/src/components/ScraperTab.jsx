import React, { useState, useEffect, useRef } from "react";
import { 
  Play, Square, Compass, MapPin, Tag, Sliders, 
  Phone, Globe, Star, ExternalLink, AlertCircle, CheckCircle2, 
  Loader2, RefreshCw, Layers 
} from "lucide-react";
import { 
  getStates, getPincodes, startScraping, getScrapeStatus, stopScraping, 
  getProfileCoverage, getScrapeSession, resumeScrape 
} from "../api";

export default function ScraperTab({ activeProfile, onDataChanged, onNavigateTab }) {
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState("");
  const [pincodes, setPincodes] = useState([]);
  const [selectedPincodes, setSelectedPincodes] = useState([]);
  const [loadingPincodes, setLoadingPincodes] = useState(false);

  // Niches
  const [selectedNiches, setSelectedNiches] = useState([]);
  const [customNichesText, setCustomNichesText] = useState("");

  // Scraper Settings
  const [maxScrolls, setMaxScrolls] = useState(3);

  // Job Monitoring State
  const [jobStatus, setJobStatus] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [savedSession, setSavedSession] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Coverage tracking
  const [coverage, setCoverage] = useState({ covered_pincodes: [], pincode_niches: {}, total_jobs: 0 });
  const [rescanCovered, setRescanCovered] = useState(false);
  const [loadingCoverage, setLoadingCoverage] = useState(false);

  const pollIntervalRef = useRef(null);


  // Load States on mount
  useEffect(() => {
    getStates()
      .then((res) => setStates(res || []))
      .catch((err) => console.error("Could not load states:", err));

    // Check existing scraper status immediately
    fetchStatus();
  }, []);

  // Sync profile niches when activeProfile changes
  useEffect(() => {
    if (activeProfile && activeProfile.niches) {
      setSelectedNiches(activeProfile.niches);
    } else {
      setSelectedNiches([]);
    }
  }, [activeProfile]);

  // Load Pincodes when state changes
  useEffect(() => {
    if (!selectedState) {
      setPincodes([]);
      setSelectedPincodes([]);
      setCoverage({ covered_pincodes: [], pincode_niches: {}, total_jobs: 0 });
      return;
    }

    setLoadingPincodes(true);
    getPincodes(selectedState)
      .then((pcs) => {
        setPincodes(pcs || []);
        // Select first 5 by default for convenience
        setSelectedPincodes((pcs || []).slice(0, 5));
      })
      .catch((err) => {
        console.error("Could not load pincodes:", err);
        setPincodes([]);
      })
      .finally(() => setLoadingPincodes(false));

    // Fetch coverage data for this profile
    if (activeProfile) {
      setLoadingCoverage(true);
      getProfileCoverage(activeProfile.slug, activeProfile.api_key)
        .then((data) => setCoverage(data || { covered_pincodes: [], pincode_niches: {}, total_jobs: 0 }))
        .catch(() => {})
        .finally(() => setLoadingCoverage(false));
    }
  }, [selectedState, activeProfile]);

  // Polling loop
  const fetchStatus = async () => {
    try {
      const st = await getScrapeStatus();
      setJobStatus(st);
      if (st.status === "running") {
        if (!pollIntervalRef.current) {
          pollIntervalRef.current = setInterval(fetchStatus, 1500);
        }
      } else {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err) {
      console.error("Error polling scrape status:", err);
    }
  };

  const checkSavedSession = async () => {
    if (!activeProfile) return;
    try {
      const s = await getScrapeSession(activeProfile.slug, activeProfile.api_key);
      setSavedSession(s && s.has_session && s.remaining_jobs > 0 ? s : null);
    } catch (e) {
      setSavedSession(null);
    }
  };

  useEffect(() => {
    pollIntervalRef.current = setInterval(fetchStatus, 2000);
    checkSavedSession();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeProfile]);

  const handleResumeScrape = async () => {
    if (!activeProfile) return;
    setIsResuming(true);
    setErrorMsg("");
    try {
      await resumeScrape(activeProfile.slug, activeProfile.api_key);
      setSavedSession(null);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(fetchStatus, 1200);
      fetchStatus();
    } catch (err) {
      setErrorMsg(err.message || "Failed to resume scraper.");
    } finally {
      setIsResuming(false);
    }
  };


  const handleTogglePincode = (pc) => {
    setSelectedPincodes((prev) =>
      prev.includes(pc) ? prev.filter((p) => p !== pc) : [...prev, pc]
    );
  };

  const handleSelectAllPincodes = () => {
    if (selectedPincodes.length === pincodes.length) {
      setSelectedPincodes([]);
    } else {
      setSelectedPincodes([...pincodes]);
    }
  };

  const handleToggleNiche = (niche) => {
    setSelectedNiches((prev) =>
      prev.includes(niche) ? prev.filter((n) => n !== niche) : [...prev, niche]
    );
  };

  const getCombinedNiches = () => {
    const custom = customNichesText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    return Array.from(new Set([...selectedNiches, ...custom]));
  };

  const handleStartScrape = async () => {
    if (!activeProfile) {
      setErrorMsg("Please select an active profile in the top navigation bar.");
      return;
    }
    if (!selectedState) {
      setErrorMsg("Please select a state to scrape.");
      return;
    }
    if (selectedPincodes.length === 0) {
      setErrorMsg("Please select at least one pincode.");
      return;
    }

    const allNiches = getCombinedNiches();
    if (allNiches.length === 0) {
      setErrorMsg("Please select or type at least one niche.");
      return;
    }

    setErrorMsg("");
    setIsStarting(true);

    try {
      await startScraping({
        profile_id: activeProfile.id,
        state: selectedState,
        pincodes: selectedPincodes,
        niches: allNiches,
        max_scrolls: Number(maxScrolls),
        rescan_covered: rescanCovered
      });
      // Start fast polling
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(fetchStatus, 1200);
      fetchStatus();
    } catch (err) {
      if (err.message && err.message.includes("already running")) {
        setErrorMsg("Connected to active running scrape job.");
        fetchStatus();
      } else {
        setErrorMsg(err.message || "Failed to start scraper.");
      }
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopScrape = async () => {
    setIsStopping(true);
    try {
      await stopScraping();
      fetchStatus();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setErrorMsg(err.message || "Failed to stop scraper.");
    } finally {
      setIsStopping(false);
    }
  };

  const isRunning = jobStatus?.status === "running";
  const combinedNiches = getCombinedNiches();

  return (
    <div className="space-y-8">
      
      {/* Active Profile Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">{activeProfile?.icon || "📁"}</span>
            <h2 className="text-xl font-bold text-white">
              {activeProfile?.name || "Select a Profile"}
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
              slug: {activeProfile?.slug || "none"}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            {activeProfile?.description || "Select a profile to customize niches and target pincodes."}
          </p>
          <div className="pt-2">
            <button
              onClick={() => onNavigateTab && onNavigateTab("profiles")}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-750 text-emerald-400 border border-slate-700 font-semibold transition inline-flex items-center gap-1.5"
            >
              <span>⚙️ Add / Change Scraper Profile</span>
            </button>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-3">
          {!isRunning && savedSession && savedSession.remaining_jobs > 0 && (
            <button
              onClick={handleResumeScrape}
              disabled={isResuming || isStarting}
              title={`Resume unfinished scrape in ${savedSession.state}: ${savedSession.remaining_jobs} jobs remaining out of ${savedSession.total_jobs}`}
              className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 text-xs font-extrabold px-4 py-2.5 rounded-xl shadow-xl shadow-amber-500/25 transition flex items-center gap-2 border border-amber-400"
            >
              {isResuming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              <span>Resume ({savedSession.remaining_jobs} left)</span>
            </button>
          )}

          {isRunning ? (
            <button
              onClick={handleStopScrape}
              disabled={isStopping}
              className="bg-rose-500 hover:bg-rose-600 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-rose-500/20 transition flex items-center gap-2"
            >
              {isStopping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
              Stop Scraping
            </button>
          ) : (
            <button
              onClick={handleStartScrape}
              disabled={isStarting}
              className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50 text-slate-950 text-xs font-extrabold px-6 py-2.5 rounded-xl shadow-xl shadow-emerald-500/25 transition flex items-center gap-2"
            >
              {isStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              Start Playwright Scrape
            </button>
          )}
        </div>
      </div>

      {/* Unfinished Session Banner */}
      {!isRunning && savedSession && savedSession.remaining_jobs > 0 && (
        <div className="bg-amber-950/40 border border-amber-500/40 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-200">
          <div className="flex items-center gap-3">
            <span className="text-xl">⚡</span>
            <div>
              <strong className="text-white">Interrupted Scrape Session Detected ({savedSession.state})</strong>
              <p className="text-slate-400 text-[11px] mt-0.5">
                {savedSession.done_jobs} done, <span className="text-amber-300 font-semibold">{savedSession.remaining_jobs} remaining</span>. You can continue right where it broke.
              </p>
            </div>
          </div>
          <button
            onClick={handleResumeScrape}
            disabled={isResuming || isStarting}
            className="shrink-0 bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 text-xs"
          >
            {isResuming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>▶ Continue Extraction</span>}
          </button>
        </div>
      )}


      {errorMsg && (
        <div className={`p-4 rounded-xl text-xs flex items-center justify-between gap-2 ${
          errorMsg.includes("Connected") ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300" : "bg-rose-500/10 border border-rose-500/30 text-rose-400"
        }`}>
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg("")} className="text-slate-400 hover:text-white text-xs">✕</button>
        </div>
      )}

      {/* Live Monitor Widget (ALWAYS SHOWN) */}
      {jobStatus && (
        <div className={`bg-gradient-to-b from-slate-900 to-slate-950 border rounded-2xl p-6 shadow-2xl space-y-6 relative overflow-hidden transition-all ${
          isRunning ? "border-emerald-500/50 shadow-emerald-500/10" : "border-slate-800"
        }`}>
          <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <span className={`flex h-3.5 w-3.5 relative ${isRunning ? "animate-pulse" : ""}`}>
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isRunning ? "bg-emerald-400" : "bg-transparent"}`}></span>
                <span className={`relative inline-flex rounded-full h-3.5 w-3.5 ${isRunning ? "bg-emerald-500" : "bg-slate-600"}`}></span>
              </span>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  Engine Status:{" "}
                  <span className={`capitalize font-mono ${isRunning ? "text-emerald-400 font-bold" : "text-slate-400"}`}>
                    {jobStatus.status === "running" ? "⚡ Actively Scraping Google Maps Live" : jobStatus.status}
                  </span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {isRunning 
                    ? `Current Target: "${jobStatus.current_niche}" in Pincode: ${jobStatus.current_pincode} (${jobStatus.state})`
                    : "Zero-data-loss active: Every business is instantly committed to Aiven MySQL."
                  }
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
              <span>Time: <strong className="text-white">{jobStatus.elapsed_seconds || 0}s</strong></span>
              <span>Progress: <strong className="text-emerald-400">{jobStatus.done_jobs || 0} / {jobStatus.total_jobs || 0} ({jobStatus.progress_percent || 0}%)</strong></span>
              <button
                onClick={fetchStatus}
                title="Refresh Live Status"
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-teal-400 h-2 rounded-full transition-all duration-500"
              style={{ width: `${jobStatus.progress_percent || 0}%` }}
            ></div>
          </div>

          {/* KPI Mini-Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">Businesses Found</span>
              <div className="text-2xl font-black text-white mt-1">{jobStatus.scraped || 0}</div>
            </div>
            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">Instant MySQL Commits</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">{jobStatus.saved || 0}</div>
            </div>
            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">With Contact Phone</span>
              <div className="text-2xl font-black text-blue-400 mt-1">{jobStatus.phones || 0}</div>
            </div>
            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">With Website Link</span>
              <div className="text-2xl font-black text-purple-400 mt-1">{jobStatus.webs || 0}</div>
            </div>
          </div>

          {/* Live Stream of Scraped Items */}
          {jobStatus.recent_items && jobStatus.recent_items.length > 0 && (
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                ⚡ Real-Time Scraping Feed (Last {jobStatus.recent_items.length} Extracted)
              </h4>
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                {jobStatus.recent_items.map((it, idx) => (
                  <div key={idx} className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-2.5 flex items-center justify-between text-xs hover:border-slate-700 transition">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{it.name}</span>
                        {it.rating && it.rating !== "N/A" && (
                          <span className="text-amber-400 text-[10px]">★ {it.rating}</span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2">
                        <span>{it.niche}</span>
                        <span>•</span>
                        <span>PIN: {it.pincode}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {it.phone && it.phone !== "N/A" ? (
                        <span className="font-mono text-emerald-400 font-medium">{it.phone}</span>
                      ) : (
                        <span className="text-slate-600">No phone</span>
                      )}
                      {it.website && it.website !== "N/A" && (
                        <a href={it.website} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                          🔗
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Scraper Configuration Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Step 1: Location & Pincodes */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <div className="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xs font-bold">1</div>
            <h3 className="text-sm font-bold text-white">Target Geography</h3>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Select State / Region
            </label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="">-- Choose State --</option>
              {states.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          {selectedState && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Select Pincodes ({selectedPincodes.length}/{pincodes.length})
                </span>
                <button
                  type="button"
                  onClick={handleSelectAllPincodes}
                  className="text-[11px] text-emerald-400 hover:underline"
                >
                  {selectedPincodes.length === pincodes.length ? "Deselect All" : "Select All"}
                </button>
              </div>

              {loadingPincodes ? (
                <div className="p-4 text-center text-slate-500 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1" />
                  Loading pincodes...
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-1.5 max-h-56 overflow-y-auto p-1 bg-slate-950 border border-slate-800 rounded-lg">
                  {pincodes.map((pc) => {
                    const isCovered = coverage.covered_pincodes?.includes(pc);
                    const nicheCount = isCovered ? (coverage.pincode_niches?.[pc] || []).length : 0;
                    return (
                      <label
                        key={pc}
                        className={`flex items-center gap-2 p-1.5 rounded text-xs cursor-pointer transition ${
                          selectedPincodes.includes(pc)
                            ? isCovered
                              ? "bg-amber-500/10 text-amber-300 border border-amber-500/30"
                              : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                            : "text-slate-400 hover:bg-slate-900"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedPincodes.includes(pc)}
                          onChange={() => handleTogglePincode(pc)}
                          className="rounded border-slate-700 text-emerald-500 focus:ring-0"
                        />
                        <span className="font-mono">{pc}</span>
                        {isCovered && (
                          <span className="ml-auto text-[9px] bg-amber-500/20 text-amber-400 px-1 py-0.5 rounded border border-amber-500/30 shrink-0">
                            ✓{nicheCount}
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}

              {/* Rescan covered toggle — only show when there are covered pincodes */}
              {coverage.covered_pincodes?.length > 0 && selectedState && (
                <div className="mt-2 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl space-y-2">
                  <p className="text-[11px] text-amber-300 font-semibold">
                    ⚠️ {coverage.covered_pincodes.length} pincode{coverage.covered_pincodes.length > 1 ? "s" : ""} already scraped ({coverage.total_jobs} job{coverage.total_jobs !== 1 ? "s" : ""} total)
                  </p>
                  <p className="text-[10px] text-slate-400">How should the scraper handle already-covered pincode+niche combos?</p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setRescanCovered(false)}
                      className={`flex-1 text-[11px] px-2 py-1.5 rounded-lg border font-semibold transition ${
                        !rescanCovered
                          ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
                          : "bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600"
                      }`}
                    >
                      ⏭ Skip & Continue
                    </button>
                    <button
                      type="button"
                      onClick={() => setRescanCovered(true)}
                      className={`flex-1 text-[11px] px-2 py-1.5 rounded-lg border font-semibold transition ${
                        rescanCovered
                          ? "bg-amber-500/20 border-amber-500/50 text-amber-300"
                          : "bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600"
                      }`}
                    >
                      🔁 Re-scrape All
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}


          {/* Depth Slider */}
          <div className="pt-2 border-t border-slate-800">
            <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1.5">
              <span>Scroll Depth (Pagination)</span>
              <span className="text-emerald-400 font-mono font-bold">{maxScrolls}x scrolls</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={maxScrolls}
              onChange={(e) => setMaxScrolls(e.target.value)}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Higher depth scrolls Google Maps feed further to extract more businesses per pincode.
            </p>
          </div>
        </div>

        {/* Step 2: Niches Selection & Custom Typing */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 lg:col-span-2">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <div className="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xs font-bold">2</div>
            <h3 className="text-sm font-bold text-white">Target Niches & Categories</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Preset Niches Checkboxes */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Profile Niches ({selectedNiches.length})
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (selectedNiches.length === (activeProfile?.niches?.length || 0)) {
                      setSelectedNiches([]);
                    } else {
                      setSelectedNiches(activeProfile?.niches || []);
                    }
                  }}
                  className="text-[11px] text-emerald-400 hover:underline"
                >
                  Toggle All
                </button>
              </div>

              <div className="space-y-1 max-h-56 overflow-y-auto p-2 bg-slate-950 border border-slate-800 rounded-lg">
                {activeProfile?.niches && activeProfile.niches.length > 0 ? (
                  activeProfile.niches.map((niche) => (
                    <label
                      key={niche}
                      className={`flex items-center gap-2 p-1.5 rounded text-xs cursor-pointer transition ${
                        selectedNiches.includes(niche) ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30" : "text-slate-400 hover:bg-slate-900"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedNiches.includes(niche)}
                        onChange={() => handleToggleNiche(niche)}
                        className="rounded border-slate-700 text-emerald-500 focus:ring-0"
                      />
                      <span>{niche}</span>
                    </label>
                  ))
                ) : (
                  <p className="text-slate-500 text-xs p-2">No niches in this profile. Type custom niches on the right!</p>
                )}
              </div>
            </div>

            {/* Custom Niches Typing / Pasting */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-300">
                Type / Paste Custom Niches
              </span>
              <textarea
                value={customNichesText}
                onChange={(e) => setCustomNichesText(e.target.value)}
                placeholder={"Hair Color Studio\nBridal Makeup Artist\nUnisex Salon\nLaser Clinic"}
                rows={7}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono resize-none"
              />
              <p className="text-[11px] text-slate-500">
                Enter custom search keywords (one per line or comma-separated).
              </p>
            </div>
          </div>

          {/* Summary Box */}
          <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs bg-slate-950 p-3.5 rounded-xl border border-slate-800">
            <div>
              <span className="text-slate-400">Total Scraping Jobs:</span>{" "}
              <strong className="text-emerald-400 font-mono text-sm">
                {selectedPincodes.length * combinedNiches.length}
              </strong>{" "}
              <span className="text-slate-500">
                ({selectedPincodes.length} pincodes × {combinedNiches.length} niches)
              </span>
            </div>

            <div className="text-[11px] text-slate-400">
              ⚡ Results are saved to Aiven MySQL per business with zero data loss.
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
