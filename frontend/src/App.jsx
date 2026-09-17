import React, { useState, useEffect } from "react";
import DashboardTab from "./components/DashboardTab";
import ScraperTab from "./components/ScraperTab";
import ProfilesTab from "./components/ProfilesTab";
import LeadsTab from "./components/LeadsTab";
import UsersTab from "./components/UsersTab";
import DataTab from "./components/DataTab";
import JobsTab from "./components/JobsTab";
import ApiDocsTab from "./components/ApiDocsTab";
import LoginScreen from "./components/LoginScreen";

import {
  LayoutDashboard, Play, FolderKanban, Users,
  Database, History, BookOpen, AlertTriangle, Loader2,
  Zap, Settings, RefreshCw, LogOut, UserCheck, ChevronDown,
  ExternalLink
} from "lucide-react";
import { getProfiles, getRootInfo, getGlobalStats, getProfileStats, verifyAdminToken } from "./api";
import { getApiBaseUrl, setApiBaseUrl } from "./config";

const TABS = [
  { id: "dashboard",  label: "Dashboard",      icon: LayoutDashboard },
  { id: "scrape",     label: "Scraper Studio",  icon: Play },
  { id: "data",       label: "Data Explorer",   icon: Database },
  { id: "leads",      label: "Lead Profiles",   icon: Users },
  { id: "jobs",       label: "Coverage Tracker",icon: History },
  { id: "profiles",   label: "Profiles",        icon: FolderKanban },
  { id: "users",      label: "User Approvals",  icon: UserCheck },
  { id: "api_docs",   label: "API Docs",        icon: BookOpen },
];

class TabErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error("Tab render error:", error, info); }
  render() {
    if (this.state.hasError) return (
      <div className="p-8 bg-slate-900 border border-rose-500/30 rounded-2xl text-center space-y-3">
        <div className="text-rose-400 font-bold text-sm">Failed to load this tab.</div>
        <div className="text-slate-400 text-xs font-mono">{this.state.error?.message}</div>
        <button onClick={() => this.setState({ hasError: false, error: null })}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 text-xs font-semibold rounded-xl">
          Retry Loading
        </button>
      </div>
    );
    return this.props.children;
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem("active_tab") || "dashboard");
  const [authToken, setAuthToken] = useState(() => localStorage.getItem("admin_auth_token") || "");
  const [authUser, setAuthUser] = useState(() => {
    try { const s = localStorage.getItem("admin_auth_user"); return s ? JSON.parse(s) : null; }
    catch { return null; }
  });
  const [authChecking, setAuthChecking] = useState(true);
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [dbEngine, setDbEngine] = useState("mysql");
  const [apiOnline, setApiOnline] = useState(true);
  const [loading, setLoading] = useState(true);
  const [connError, setConnError] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(getApiBaseUrl());
  const [tabRefreshKey, setTabRefreshKey] = useState(0);

  const refreshAll = async () => {
    setLoading(true); setConnError("");
    try {
      const info = await getRootInfo();
      setDbEngine(info.db_engine || "mysql");
      setApiOnline(true);
      const pList = await getProfiles();
      setProfiles(pList || []);
      const savedSlug = localStorage.getItem("active_profile_slug");
      let selected = pList.find(p => p.slug === savedSlug);
      if (!selected && pList.length > 0) selected = pList[0];
      setActiveProfile(selected || null);
      if (selected) setStats(await getProfileStats(selected.slug, selected.api_key));
      else setStats(await getGlobalStats());
    } catch (err) {
      setApiOnline(false);
      setConnError(`Cannot connect to backend: ${err.message}`);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("admin_auth_token");
      if (!token) { setAuthChecking(false); return; }
      try {
        const res = await verifyAdminToken(token);
        if (res?.valid) {
          setAuthUser(res.user);
          localStorage.setItem("admin_auth_user", JSON.stringify(res.user));
          refreshAll();
        } else {
          setAuthToken(""); setAuthUser(null);
          localStorage.removeItem("admin_auth_token");
          localStorage.removeItem("admin_auth_user");
        }
      } catch { refreshAll(); }
      finally { setAuthChecking(false); }
    };
    checkAuth();
  }, []);

  const handleLoginSuccess = (token, user) => {
    setAuthToken(token); setAuthUser(user);
    localStorage.setItem("admin_auth_token", token);
    localStorage.setItem("admin_auth_user", JSON.stringify(user));
    refreshAll();
  };

  const handleLogout = () => {
    setAuthToken(""); setAuthUser(null);
    localStorage.removeItem("admin_auth_token");
    localStorage.removeItem("admin_auth_user");
  };

  const handleSelectProfile = (p) => {
    setActiveProfile(p);
    localStorage.setItem("active_profile_slug", p.slug);
    getProfileStats(p.slug, p.api_key).then(setStats).catch(console.error);
  };
  const handleProfileCreated = (p) => { setProfiles(prev => [...prev, p]); handleSelectProfile(p); };
  const handleProfileDeleted = (slug) => {
    const updated = profiles.filter(p => p.slug !== slug);
    setProfiles(updated);
    if (activeProfile?.slug === slug) updated.length > 0 ? handleSelectProfile(updated[0]) : setActiveProfile(null);
  };
  const handleTabChange = (tab) => { setActiveTab(tab); localStorage.setItem("active_tab", tab); };

  if (authChecking) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-xs gap-3">
      <Loader2 className="w-6 h-6 animate-spin text-emerald-400" /> Initializing...
    </div>
  );
  if (!authToken) return <LoginScreen onLoginSuccess={handleLoginSuccess} />;

  return (
    <div className="w-full min-h-screen bg-slate-950 text-slate-100 flex">

      {/* ════════════════════════════════════════════
          LEFT SIDEBAR
      ════════════════════════════════════════════ */}
      <aside className="w-60 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col sticky top-0 h-screen overflow-y-auto">
        
        {/* Brand */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
              <Zap className="h-5 w-5 text-slate-950" />
            </div>
            <div className="min-w-0">
              <div className="font-extrabold text-sm text-white tracking-tight">Scraper Pro</div>
              <div className="text-[10px] text-slate-500 truncate">B2B Lead Intelligence</div>
            </div>
          </div>
        </div>

        {/* Profile Switcher */}
        <div className="px-4 py-3 border-b border-slate-800">
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Workspace</div>
          {profiles.length > 0 ? (
            <div className="relative">
              <select
                value={activeProfile?.slug || ""}
                onChange={e => { const p = profiles.find(p => p.slug === e.target.value); if (p) handleSelectProfile(p); }}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 pr-7 appearance-none cursor-pointer hover:border-slate-600 focus:outline-none focus:border-emerald-500 font-medium transition"
              >
                {profiles.map(p => (
                  <option key={p.id} value={p.slug}>{p.icon} {p.name} ({p.niches?.length || 0} niches)</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          ) : (
            <div className="text-xs text-slate-500">No profiles yet</div>
          )}
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all text-left ${
                  isActive
                    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/70"
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-emerald-400" : "text-slate-500"}`} />
                {tab.label}
                {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              </button>
            );
          })}
        </nav>

        {/* Backend & DB Status */}
        <div className="px-4 py-3 border-t border-slate-800 space-y-2">
          <a
            href="https://dashboard.render.com/web/srv-dafqh9ou01pc73bifgj0"
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 hover:border-slate-600 transition text-xs text-slate-400 hover:text-slate-300"
          >
            <span className="w-2 h-2 rounded-full shrink-0 bg-blue-400 animate-pulse" />
            <span>Server: <strong className="text-blue-400">RENDER</strong></span>
            <ExternalLink className="w-3 h-3 ml-auto" />
          </a>
          <a
            href="https://console.aiven.io/account/a5d5eec48744/project/groomitindia/services/data-extractor/overview"
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 hover:border-slate-600 transition text-xs text-slate-400 hover:text-slate-300"
          >
            <span className={`w-2 h-2 rounded-full shrink-0 ${dbEngine === "mysql" ? "bg-emerald-400 animate-pulse" : "bg-rose-500 animate-pulse"}`} />
            <span>DB: <strong className={dbEngine === "mysql" ? "text-emerald-400" : "text-rose-400"}>{dbEngine.toUpperCase()}</strong></span>
            <ExternalLink className="w-3 h-3 ml-auto" />
          </a>
        </div>

        {/* Footer Controls */}
        <div className="px-4 py-4 border-t border-slate-800 space-y-2">
          <button onClick={() => setTabRefreshKey(k => k + 1)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition font-medium">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh Data
          </button>
          <button onClick={() => setShowSettings(true)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition font-medium">
            <Settings className="w-3.5 h-3.5" /> Backend Settings
          </button>
          {authUser && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-500 bg-slate-800/50">
              <UserCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="truncate">{authUser.email}</span>
            </div>
          )}
          {handleLogout && (
            <button onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition font-medium">
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          )}
        </div>
      </aside>

      {/* ════════════════════════════════════════════
          MAIN CONTENT
      ════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-w-0 w-full">

        {/* Top bar — minimal, just title + API key */}
        <header className="h-14 border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30 flex items-center justify-between px-6 w-full">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-white">
              {TABS.find(t => t.id === activeTab)?.label || "Dashboard"}
            </span>
            {activeProfile && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400">
                {activeProfile.icon} {activeProfile.name}
              </span>
            )}
          </div>
          {activeProfile && (
            <button
              onClick={() => { navigator.clipboard.writeText(activeProfile.api_key); }}
              title="Copy API Key"
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-700 font-mono transition"
            >
              Key: {activeProfile.api_key?.slice(0, 8)}…
            </button>
          )}
        </header>

        {/* Connection error banner */}
        {!apiOnline && connError && (
          <div className="bg-rose-500/10 border-b border-rose-500/20 px-6 py-2.5 text-xs text-rose-300 flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{connError}</span>
            </div>
            <button onClick={refreshAll}
              className="px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold transition text-xs">
              Retry
            </button>
          </div>
        )}

        {/* Tab Content */}
        <main className="flex-1 p-6 sm:p-8 overflow-y-auto w-full">
          <TabErrorBoundary>
            {loading && !stats ? (
              <div className="py-24 text-center text-slate-400 text-xs">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-emerald-400" />
                Connecting to database...
              </div>
            ) : (
              <>
                <div className={activeTab === "dashboard" ? "contents" : "hidden"}>
                  <DashboardTab stats={stats} activeProfile={activeProfile} onNavigateTab={handleTabChange} />
                </div>
                <div className={activeTab === "scrape" ? "contents" : "hidden"}>
                  <ScraperTab activeProfile={activeProfile} onDataChanged={refreshAll} onNavigateTab={handleTabChange} />
                </div>
                <div className={activeTab === "profiles" ? "contents" : "hidden"}>
                  <ProfilesTab profiles={profiles} onProfileCreated={handleProfileCreated} onProfileDeleted={handleProfileDeleted} />
                </div>
                <div className={activeTab === "leads" ? "contents" : "hidden"}>
                  <LeadsTab activeProfile={activeProfile} />
                </div>
                <div className={activeTab === "users" ? "contents" : "hidden"}>
                  <UsersTab />
                </div>
                <div className={activeTab === "data" ? "contents" : "hidden"}>
                  <DataTab activeProfile={activeProfile} onDataChanged={refreshAll} />
                </div>
                <div className={activeTab === "jobs" ? "contents" : "hidden"}>
                  <JobsTab activeProfile={activeProfile} />
                </div>
                <div className={activeTab === "api_docs" ? "contents" : "hidden"}>
                  <ApiDocsTab activeProfile={activeProfile} />
                </div>
              </>
            )}
          </TabErrorBoundary>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-900 bg-slate-950 py-3 text-center text-[10px] text-slate-700">
          Scraper Pro &copy; {new Date().getFullYear()}
        </footer>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-emerald-400" /> Backend Configuration
              </h3>
              <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white text-lg">✕</button>
            </div>
            <form onSubmit={e => { e.preventDefault(); setApiBaseUrl(apiUrl); setShowSettings(false); refreshAll(); }} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Backend API URL</label>
                <input
                  type="text" value={apiUrl} onChange={e => setApiUrl(e.target.value)}
                  placeholder="https://data-scrapper-n7ua.onrender.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
                <p className="text-[11px] text-slate-400 mt-1.5">
                  Default: <code className="text-emerald-400">https://data-scrapper-n7ua.onrender.com</code>
                </p>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button"
                  onClick={() => { const d = "https://data-scrapper-n7ua.onrender.com"; setApiUrl(d); setApiBaseUrl(d); setShowSettings(false); refreshAll(); }}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition">
                  Reset Default
                </button>
                <button type="submit"
                  className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition">
                  Save & Apply
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
