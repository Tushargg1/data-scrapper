import React, { useState, useEffect, useRef } from "react";
import { 
  Play, Square, Compass, MapPin, Tag, Sliders, 
  Phone, Globe, Star, ExternalLink, AlertCircle, CheckCircle2, 
  Loader2, RefreshCw, Layers, RotateCcw, FastForward, Check,
  ChevronDown, ChevronUp, Search, Sparkles
} from "lucide-react";
import { 
  getStates, getPincodes, startScraping, getScrapeStatus, stopScraping, 
  getProfileCoverage, getScrapeSession, resumeScrape 
} from "../api";

const SCRAPER_PLATFORMS = [
  {
    id: "google_maps",
    name: "Google Maps",
    icon: "🗺️",
    badge: "Active",
    badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    description: "Extract local business listings, verified phone numbers, websites, star ratings & addresses.",
    status: "ready"
  },
  {
    id: "indiamart",
    name: "IndiaMART",
    icon: "🏭",
    badge: "Coming Soon",
    badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/40",
    description: "B2B wholesale suppliers, direct manufacturers, GST numbers & verified seller inquiries.",
    status: "coming_soon"
  },
  {
    id: "instagram",
    name: "Instagram Business",
    icon: "📸",
    badge: "Coming Soon",
    badgeColor: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/40",
    description: "Creator & business bios, public WhatsApp/call buttons, follower counts & location tags.",
    status: "coming_soon"
  },
  {
    id: "justdial",
    name: "JustDial",
    icon: "📞",
    badge: "Coming Soon",
    badgeColor: "bg-blue-500/20 text-blue-300 border-blue-500/40",
    description: "Local directory listings, verified mobile contacts, ratings & operational hours.",
    status: "coming_soon"
  }
];

export default function ScraperTab({ activeProfile, onDataChanged, onNavigateTab }) {
  const [selectedPlatform, setSelectedPlatform] = useState("google_maps");
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState("");
  const [pincodes, setPincodes] = useState([]);
  const [selectedPincodes, setSelectedPincodes] = useState([]);
  const [loadingPincodes, setLoadingPincodes] = useState(false);

  // Scrape Mode: "continue" (skip done, resume next) | "rescrape" (re-extract previous)
  const [scrapeMode, setScrapeMode] = useState("continue");

  // Pincode filtering & search
  const [pincodeFilter, setPincodeFilter] = useState("all"); // "all" | "done" | "pending"
  const [pincodeSearch, setPincodeSearch] = useState("");
  const [showAllDoneList, setShowAllDoneList] = useState(false);

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
  const [coverage, setCoverage] = useState({ covered_pincodes: [], pincode_niches: {}, pincode_counts: {}, total_jobs: 0 });
  const [loadingCoverage, setLoadingCoverage] = useState(false);

  const pollIntervalRef = useRef(null);

  // Reload coverage for active profile
  const reloadCoverage = async () => {
    if (!activeProfile) return;
    setLoadingCoverage(true);
    try {
      const data = await getProfileCoverage(activeProfile.slug, activeProfile.api_key);
      setCoverage(data || { covered_pincodes: [], pincode_niches: {}, pincode_counts: {}, total_jobs: 0 });
    } catch (err) {
      console.error("Could not load coverage:", err);
    } finally {
      setLoadingCoverage(false);
    }
  };

  // Load States on mount
  useEffect(() => {
    getStates()
      .then((res) => setStates(res || []))
      .catch((err) => console.error("Could not load states:", err));

    fetchStatus();
  }, []);

  // Sync profile niches & coverage when activeProfile changes
  useEffect(() => {
    if (activeProfile && activeProfile.niches) {
      setSelectedNiches(activeProfile.niches);
    } else {
      setSelectedNiches([]);
    }
    if (activeProfile) {
      reloadCoverage();
    }
  }, [activeProfile]);

  // Load Pincodes when state changes
  useEffect(() => {
    if (!selectedState) {
      setPincodes([]);
      setSelectedPincodes([]);
      return;
    }

    setLoadingPincodes(true);
    getPincodes(selectedState)
      .then((pcs) => {
        const pinList = pcs || [];
        setPincodes(pinList);
        // Automatically pre-select first 5 pending pincodes if available, else first 5
        const pending = pinList.filter((pc) => !coverage.covered_pincodes?.includes(pc));
        if (pending.length > 0) {
          setSelectedPincodes(pending.slice(0, 5));
        } else {
          setSelectedPincodes(pinList.slice(0, 5));
        }
      })
      .catch((err) => {
        console.error("Could not load pincodes:", err);
        setPincodes([]);
        setSelectedPincodes([]);
      })
      .finally(() => setLoadingPincodes(false));

    reloadCoverage();
  }, [selectedState]);

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
          reloadCoverage();
          if (onDataChanged) onDataChanged();
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

  const handleSelectPendingOnly = () => {
    setSelectedPincodes([...pendingInState]);
  };

  const handleSelectDoneOnly = () => {
    setSelectedPincodes([...doneInState]);
    setScrapeMode("rescrape");
  };

  const handleDeselectAll = () => {
    setSelectedPincodes([]);
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

  // Helper metrics
  const doneInState = pincodes.filter((pc) => coverage.covered_pincodes?.includes(pc));
  const pendingInState = pincodes.filter((pc) => !coverage.covered_pincodes?.includes(pc));

  const filteredPincodes = pincodes.filter((pc) => {
    const isDone = coverage.covered_pincodes?.includes(pc);
    if (pincodeFilter === "done" && !isDone) return false;
    if (pincodeFilter === "pending" && isDone) return false;
    if (pincodeSearch && !pc.includes(pincodeSearch.trim())) return false;
    return true;
  });

  const selectedDone = selectedPincodes.filter((pc) => coverage.covered_pincodes?.includes(pc));
  const selectedPending = selectedPincodes.filter((pc) => !coverage.covered_pincodes?.includes(pc));

  // Determine where scraping will continue from
  const nextPincodeToScrape = scrapeMode === "continue"
    ? (selectedPending.length > 0 ? selectedPending[0] : null)
    : (selectedPincodes.length > 0 ? selectedPincodes[0] : null);

  const skippedInSelection = scrapeMode === "continue" ? selectedDone : [];

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

    if (scrapeMode === "continue" && selectedPending.length === 0) {
      setErrorMsg("All selected pincodes are already completed! Switch to '🔁 Re-Scrape Previous Pincodes' mode above to re-extract fresh data from them.");
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
        rescan_covered: scrapeMode === "rescrape",
        source: selectedPlatform
      });
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
          ) : scrapeMode === "rescrape" ? (
            <button
              onClick={handleStartScrape}
              disabled={isStarting || selectedPincodes.length === 0}
              className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 disabled:opacity-50 text-slate-950 text-xs font-extrabold px-6 py-2.5 rounded-xl shadow-xl shadow-cyan-500/25 transition flex items-center gap-2"
            >
              {isStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              Re-Scrape Selected ({selectedPincodes.length})
            </button>
          ) : selectedPincodes.length > 0 && selectedPending.length === 0 ? (
            <button
              onClick={() => setScrapeMode("rescrape")}
              className="bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-extrabold px-5 py-2.5 rounded-xl shadow-xl shadow-amber-500/25 transition flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              All Done — Switch to Re-Scrape
            </button>
          ) : (
            <button
              onClick={handleStartScrape}
              disabled={isStarting || selectedPincodes.length === 0}
              className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:opacity-50 text-slate-950 text-xs font-extrabold px-6 py-2.5 rounded-xl shadow-xl shadow-emerald-500/25 transition flex items-center gap-2"
            >
              {isStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {nextPincodeToScrape ? `Continue Scrape (From ${nextPincodeToScrape})` : "Start Scraper"}
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

      {/* Scraping Source / Platform Selection */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-sm font-bold">
              🌐
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                Scraping Source & Platform Selection
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  Multi-Source Ready
                </span>
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Choose the target platform. Google Maps is actively running; B2B and social platforms are prepared for seamless plug-in.
              </p>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-3 py-1 rounded-xl self-start sm:self-auto flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Active: {SCRAPER_PLATFORMS.find((p) => p.id === selectedPlatform)?.name || "Google Maps"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SCRAPER_PLATFORMS.map((platform) => {
            const isSelected = selectedPlatform === platform.id;
            return (
              <button
                key={platform.id}
                type="button"
                onClick={() => setSelectedPlatform(platform.id)}
                className={`text-left p-3.5 rounded-xl border transition flex flex-col justify-between group ${
                  isSelected
                    ? "bg-slate-800/90 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/40"
                    : "bg-slate-950/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-2xl group-hover:scale-110 transition-transform">{platform.icon}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${platform.badgeColor}`}>
                      {platform.badge}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                    {platform.name}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {platform.description}
                  </p>
                </div>

                <div className="pt-3 mt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[10px]">
                  <span className={isSelected ? "text-emerald-400 font-bold" : "text-slate-500"}>
                    {isSelected ? "● Selected" : "Click to select"}
                  </span>
                  {platform.status === "ready" ? (
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <Check className="w-3 h-3" /> Live Runner
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">Adapter Ready</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {selectedPlatform !== "google_maps" && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-base">ℹ️</span>
              <span>
                <strong>{SCRAPER_PLATFORMS.find((p) => p.id === selectedPlatform)?.name}</strong> platform option selected. The engine runner currently extracts from Google Maps; this option is structured for the upcoming platform adapter without requiring interface changes.
              </span>
            </div>
            <button
              type="button"
              onClick={() => setSelectedPlatform("google_maps")}
              className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-bold rounded-lg text-[11px] transition shrink-0 self-start sm:self-auto"
            >
              Switch to Google Maps
            </button>
          </div>
        )}
      </div>

      {/* Scraper Configuration Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Step 1: Location & Pincodes */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xs font-bold">1</div>
              <h3 className="text-sm font-bold text-white">Target Geography</h3>
            </div>
            {loadingCoverage && (
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> Checking done pincodes...
              </span>
            )}
          </div>

          {/* MODE SELECTOR: Continue vs Re-Scrape */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-300">
              Scraping Mode
            </label>
            <div className="grid grid-cols-2 gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={() => setScrapeMode("continue")}
                className={`py-2 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                  scrapeMode === "continue"
                    ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <FastForward className="w-3.5 h-3.5" />
                <span>⏭️ Continue (Skip Done)</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setScrapeMode("rescrape");
                  if (doneInState.length > 0 && selectedDone.length === 0) {
                    setSelectedPincodes([...doneInState]);
                  }
                }}
                className={`py-2 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                  scrapeMode === "rescrape"
                    ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>🔁 Re-Scrape Previous</span>
              </button>
            </div>
          </div>

          {/* QUEUE CONTINUATION INDICATOR / STATUS */}
          {selectedState && (
            <div>
              {scrapeMode === "continue" ? (
                nextPincodeToScrape ? (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                        <FastForward className="w-3.5 h-3.5" />
                        Next in Continuation Queue:
                      </span>
                      <span className="font-mono bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-black text-xs border border-emerald-500/30">
                        PIN: {nextPincodeToScrape}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300">
                      Scraper will continue starting from <strong className="text-white font-mono">{nextPincodeToScrape}</strong>.
                      {skippedInSelection.length > 0 ? (
                        <span> Skipping <strong className="text-amber-400 font-semibold">{skippedInSelection.length} completed pincode{skippedInSelection.length > 1 ? "s" : ""}</strong> ({skippedInSelection.slice(0, 3).join(", ")}{skippedInSelection.length > 3 ? "..." : ""}).</span>
                      ) : (
                        <span> All selected pincodes are pending.</span>
                      )}
                    </p>
                  </div>
                ) : selectedPincodes.length > 0 && selectedPending.length === 0 ? (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs space-y-2">
                    <div className="flex items-center gap-1.5 font-bold text-amber-400">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>All {selectedPincodes.length} selected pincodes are already done!</span>
                    </div>
                    <p className="text-[11px] text-slate-300">
                      Nothing new to scrape in Continue Mode. Choose an option:
                    </p>
                    <div className="flex flex-col gap-1.5 pt-1">
                      <button
                        type="button"
                        onClick={() => setScrapeMode("rescrape")}
                        className="w-full py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition shadow"
                      >
                        <RotateCcw className="w-3.5 h-3.5" /> Switch to "Re-Scrape Previous" Mode
                      </button>
                      <button
                        type="button"
                        onClick={handleSelectPendingOnly}
                        disabled={pendingInState.length === 0}
                        className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 font-semibold rounded-lg text-xs transition"
                      >
                        Select Unscraped Pincodes ({pendingInState.length} left)
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-[11px] text-slate-400">
                    Select pincodes below to queue up extraction.
                  </div>
                )
              ) : (
                <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-cyan-400 flex items-center gap-1.5">
                      <RotateCcw className="w-3.5 h-3.5" />
                      Re-Scrape Mode Active
                    </span>
                    <span className="text-[11px] font-mono text-cyan-300 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-500/30">
                      {selectedPincodes.length} queued
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300">
                    Will re-extract selected pincodes starting from <strong className="text-white font-mono">{selectedPincodes[0] || "none"}</strong>. Existing records will be updated and fresh businesses added with zero duplicates.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ALL DONE PINCODES SUMMARY CARD (Across this profile) */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-white">
                  Completed Pincodes: <strong className="text-emerald-400">{coverage.covered_pincodes?.length || 0} Done</strong>
                </span>
              </div>
              {coverage.covered_pincodes?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowAllDoneList(!showAllDoneList)}
                  className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1 font-medium"
                >
                  <span>{showAllDoneList ? "Hide List" : "Show All Done"}</span>
                  {showAllDoneList ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              )}
            </div>

            {showAllDoneList && coverage.covered_pincodes?.length > 0 && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <p className="text-[10px] text-slate-400">
                  All completed pincodes across this profile. Click any to toggle or select for re-scraping:
                </p>
                <div className="flex flex-wrap gap-1 max-h-36 overflow-y-auto pr-1">
                  {coverage.covered_pincodes.map((pc) => {
                    const cnt = coverage.pincode_counts?.[pc] || 0;
                    const isSel = selectedPincodes.includes(pc);
                    return (
                      <button
                        key={pc}
                        type="button"
                        onClick={() => handleTogglePincode(pc)}
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border transition flex items-center gap-1 ${
                          isSel
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold"
                            : "bg-slate-900 text-emerald-400 border-emerald-500/30 hover:bg-slate-850"
                        }`}
                        title={`Pincode ${pc}: ${cnt} leads. Click to toggle selection.`}
                      >
                        <span>✓ {pc}</span>
                        {cnt > 0 && <span className="text-[9px] text-slate-400">({cnt})</span>}
                      </button>
                    );
                  })}
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPincodes([...coverage.covered_pincodes]);
                      setScrapeMode("rescrape");
                    }}
                    className="text-cyan-400 hover:underline font-semibold"
                  >
                    🔁 Select All Done Pincodes
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedPincodes([])}
                    className="text-slate-400 hover:text-white"
                  >
                    Clear Selection
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* State / Region Select */}
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
            <div className="space-y-2.5">
              {/* State Pincode Summary Bar */}
              <div className="flex items-center justify-between text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-400">
                  In <strong className="text-white">{selectedState}</strong>:
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-emerald-400 font-semibold">✓ {doneInState.length} Done</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-slate-300">⏳ {pendingInState.length} Pending</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-slate-400">{pincodes.length} Total</span>
                </div>
              </div>

              {/* Pincode Filter Tabs */}
              <div className="flex gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px]">
                <button
                  type="button"
                  onClick={() => setPincodeFilter("all")}
                  className={`flex-1 py-1 rounded transition font-medium ${
                    pincodeFilter === "all" ? "bg-slate-800 text-white font-semibold" : "text-slate-400 hover:text-white"
                  }`}
                >
                  All ({pincodes.length})
                </button>
                <button
                  type="button"
                  onClick={() => setPincodeFilter("done")}
                  className={`flex-1 py-1 rounded transition font-medium ${
                    pincodeFilter === "done" ? "bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-semibold" : "text-slate-400 hover:text-white"
                  }`}
                >
                  ✓ Done ({doneInState.length})
                </button>
                <button
                  type="button"
                  onClick={() => setPincodeFilter("pending")}
                  className={`flex-1 py-1 rounded transition font-medium ${
                    pincodeFilter === "pending" ? "bg-slate-800 text-white font-semibold" : "text-slate-400 hover:text-white"
                  }`}
                >
                  ⏳ Pending ({pendingInState.length})
                </button>
              </div>

              {/* Quick Select Buttons */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 px-0.5">
                <div className="flex items-center gap-1.5">
                  <span>Selected: <strong className="text-white font-mono">{selectedPincodes.length}</strong></span>
                  {selectedDone.length > 0 && (
                    <span className="text-emerald-400 text-[10px]">({selectedDone.length} done)</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <button type="button" onClick={handleSelectAllPincodes} className="hover:underline">
                    All
                  </button>
                  <span>·</span>
                  <button type="button" onClick={handleSelectPendingOnly} className="hover:underline">
                    Pending
                  </button>
                  <span>·</span>
                  <button type="button" onClick={handleSelectDoneOnly} className="hover:underline text-cyan-400 font-semibold">
                    Done
                  </button>
                  <span>·</span>
                  <button type="button" onClick={handleDeselectAll} className="hover:underline text-rose-400">
                    Clear
                  </button>
                </div>
              </div>

              {/* Search Filter */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={pincodeSearch}
                  onChange={(e) => setPincodeSearch(e.target.value)}
                  placeholder="Filter pincodes (e.g. 110001)..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-7 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
                {pincodeSearch && (
                  <button
                    type="button"
                    onClick={() => setPincodeSearch("")}
                    className="absolute right-2.5 top-2 text-slate-500 hover:text-white text-xs"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Pincode Grid */}
              {loadingPincodes ? (
                <div className="p-6 text-center text-slate-500 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1" />
                  Loading pincodes...
                </div>
              ) : filteredPincodes.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-xs bg-slate-950 border border-slate-800 rounded-lg">
                  No pincodes match this filter.
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-1.5 max-h-56 overflow-y-auto p-1.5 bg-slate-950 border border-slate-800 rounded-lg">
                  {filteredPincodes.map((pc) => {
                    const isCovered = coverage.covered_pincodes?.includes(pc);
                    const leadCount = coverage.pincode_counts?.[pc] || 0;
                    const isSelected = selectedPincodes.includes(pc);
                    return (
                      <label
                        key={pc}
                        className={`flex items-center justify-between p-1.5 rounded text-xs cursor-pointer transition border ${
                          isSelected
                            ? isCovered
                              ? "bg-cyan-500/10 text-cyan-300 border-cyan-500/40"
                              : "bg-emerald-500/10 text-emerald-300 border-emerald-500/40"
                            : isCovered
                              ? "bg-emerald-950/20 text-slate-300 border-emerald-500/20 hover:border-emerald-500/40"
                              : "text-slate-400 border-slate-900 hover:bg-slate-900/60"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleTogglePincode(pc)}
                            className="rounded border-slate-700 text-emerald-500 focus:ring-0 shrink-0"
                          />
                          <span className="font-mono truncate">{pc}</span>
                        </div>
                        {isCovered ? (
                          <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1 py-0.5 rounded border border-emerald-500/30 shrink-0 ml-1">
                            ✓ {leadCount > 0 ? `${leadCount} leads` : "Done"}
                          </span>
                        ) : (
                          <span className="text-[9px] text-slate-600 shrink-0 ml-1" title="Pending / Unscraped">
                            ⏳
                          </span>
                        )}
                      </label>
                    );
                  })}
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
