import React, { useState, useEffect } from "react";
import { 
  Zap, Database, Server, Settings, CheckCircle, 
  ExternalLink, ChevronDown, RefreshCw 
} from "lucide-react";
import { getApiBaseUrl, setApiBaseUrl } from "../config";

export default function Navbar({ 
  profiles, 
  activeProfile, 
  onSelectProfile, 
  onRefresh, 
  dbEngine,
  apiOnline 
}) {
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(getApiBaseUrl());
  const [copiedKey, setCopiedKey] = useState(false);

  const handleSaveUrl = (e) => {
    e.preventDefault();
    setApiBaseUrl(apiUrl);
    setShowSettings(false);
    onRefresh();
  };

  const copyApiKey = () => {
    if (activeProfile?.api_key) {
      navigator.clipboard.writeText(activeProfile.api_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  return (
    <>
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Zap className="h-5 w-5 text-slate-950 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base tracking-tight text-white">Biz Scraper Pro</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold">
                  React 19
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Google Maps Multi-Profile Lead Engine</p>
            </div>
          </div>

          {/* Center: Profile Switcher */}
          <div className="hidden md:flex items-center gap-2">
            <span className="text-xs text-slate-400">Workspace:</span>
            {profiles && profiles.length > 0 ? (
              <div className="relative">
                <select
                  value={activeProfile ? activeProfile.slug : ""}
                  onChange={(e) => {
                    const found = profiles.find((p) => p.slug === e.target.value);
                    if (found) onSelectProfile(found);
                  }}
                  className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 pr-8 appearance-none cursor-pointer hover:border-slate-600 focus:outline-none focus:border-emerald-500 font-medium transition"
                >
                  {profiles.map((p) => (
                    <option key={p.id} value={p.slug}>
                      {p.icon} {p.name} ({p.niches ? p.niches.length : 0} niches)
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            ) : (
              <span className="text-xs text-slate-500">No profiles yet</span>
            )}

            {activeProfile && (
              <button
                onClick={copyApiKey}
                title="Click to copy Profile API Key"
                className="text-[11px] px-2 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-mono transition flex items-center gap-1"
              >
                <span>Key: {activeProfile.api_key ? activeProfile.api_key.slice(0, 8) + "..." : ""}</span>
                {copiedKey && <span className="text-emerald-400 font-sans">✓</span>}
              </button>
            )}

            <button
              onClick={() => onNavigateTab && onNavigateTab("profiles")}
              title="Create or Manage Profiles"
              className="text-xs px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold transition flex items-center gap-1.5"
            >
              <span>+ New Profile</span>
            </button>
          </div>

          {/* Right Status & Controls */}
          <div className="flex items-center space-x-2.5">
            {/* DB Status Badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-950 border border-slate-800 text-slate-300">
              <span className={`h-2 w-2 rounded-full ${apiOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`}></span>
              <span className="hidden sm:inline">DB:</span> {dbEngine.toUpperCase()}
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              title="Refresh Data from API"
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* Backend URL Settings */}
            <button
              onClick={() => setShowSettings(true)}
              title="Configure Backend API URL"
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700 transition"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>

        </div>
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-emerald-400" /> Backend Configuration
              </h3>
              <button
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveUrl} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Backend API URL (Render or Localhost)
                </label>
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="https://data-scrapper-n7ua.onrender.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
                <p className="text-[11px] text-slate-400 mt-1.5">
                  Default Render Backend: <code className="text-emerald-400">https://data-scrapper-n7ua.onrender.com</code>
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setApiUrl("https://data-scrapper-n7ua.onrender.com");
                    setApiBaseUrl("https://data-scrapper-n7ua.onrender.com");
                    setShowSettings(false);
                    onRefresh();
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition"
                >
                  Reset to Render
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition"
                >
                  Save & Apply
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
