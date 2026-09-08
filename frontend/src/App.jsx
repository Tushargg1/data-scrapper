import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import DashboardTab from "./components/DashboardTab";
import ScraperTab from "./components/ScraperTab";
import ProfilesTab from "./components/ProfilesTab";
import LeadsTab from "./components/LeadsTab";
import UsersTab from "./components/UsersTab";
import DataTab from "./components/DataTab";
import JobsTab from "./components/JobsTab";
import ApiDocsTab from "./components/ApiDocsTab";

import { 
  LayoutDashboard, Play, FolderKanban, Users, 
  Database, History, BookOpen, AlertTriangle, Loader2 
} from "lucide-react";
import { getProfiles, getRootInfo, getGlobalStats, getProfileStats } from "./api";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "scrape", label: "Scraper Studio", icon: Play },
  { id: "profiles", label: "Profiles", icon: FolderKanban },
  { id: "leads", label: "Lead Profiles", icon: Users },
  { id: "users", label: "User Approvals", icon: Users },
  { id: "data", label: "Data Explorer", icon: Database },
  { id: "jobs", label: "Job Log", icon: History },
  { id: "api_docs", label: "API Docs", icon: BookOpen }
];

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [dbEngine, setDbEngine] = useState("mysql");
  const [apiOnline, setApiOnline] = useState(true);
  const [loading, setLoading] = useState(true);
  const [connError, setConnError] = useState("");

  const refreshAll = async () => {
    setLoading(true);
    setConnError("");
    try {
      // 1. Root info
      const info = await getRootInfo();
      setDbEngine(info.db_engine || "mysql");
      setApiOnline(true);

      // 2. Profiles
      const pList = await getProfiles();
      setProfiles(pList || []);

      // Set active profile if none or if missing
      const savedSlug = localStorage.getItem("active_profile_slug");
      let selected = pList.find((p) => p.slug === savedSlug);
      if (!selected && pList.length > 0) {
        selected = pList[0];
      }
      setActiveProfile(selected || null);

      // 3. Stats
      if (selected) {
        const pStats = await getProfileStats(selected.slug, selected.api_key);
        setStats(pStats);
      } else {
        const gStats = await getGlobalStats();
        setStats(gStats);
      }
    } catch (err) {
      console.error("Connection error:", err);
      setApiOnline(false);
      setConnError(`Cannot connect to backend: ${err.message}. Check backend URL in top-right Settings.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleSelectProfile = (p) => {
    setActiveProfile(p);
    localStorage.setItem("active_profile_slug", p.slug);
    getProfileStats(p.slug, p.api_key)
      .then((st) => setStats(st))
      .catch((e) => console.error(e));
  };

  const handleProfileCreated = (newProfile) => {
    setProfiles((prev) => [...prev, newProfile]);
    handleSelectProfile(newProfile);
  };

  const handleProfileDeleted = (deletedSlug) => {
    const updated = profiles.filter((p) => p.slug !== deletedSlug);
    setProfiles(updated);
    if (activeProfile?.slug === deletedSlug) {
      if (updated.length > 0) {
        handleSelectProfile(updated[0]);
      } else {
        setActiveProfile(null);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* Navigation Header */}
      <Navbar
        profiles={profiles}
        activeProfile={activeProfile}
        onSelectProfile={handleSelectProfile}
        onRefresh={refreshAll}
        dbEngine={dbEngine}
        apiOnline={apiOnline}
        onNavigateTab={(tab) => setActiveTab(tab)}
      />

      {/* Backend Connection Warning Banner if Offline */}
      {!apiOnline && connError && (
        <div className="bg-rose-500/10 border-b border-rose-500/20 px-4 py-3 text-xs text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-4xl">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{connError}</span>
          </div>
          <button
            onClick={refreshAll}
            className="px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold transition"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Main Tab Navigation */}
      <nav className="border-b border-slate-800/80 bg-slate-900/60 sticky top-16 z-30 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-1 overflow-x-auto py-2.5 no-scrollbar">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                    isActive
                      ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-bold"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-slate-950" : "text-slate-400"}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Tab Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && !stats ? (
          <div className="py-24 text-center text-slate-400 text-xs">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-emerald-400" />
            Connecting to Aiven MySQL Cloud database...
          </div>
        ) : (
          <>
            {activeTab === "dashboard" && (
              <DashboardTab
                stats={stats}
                activeProfile={activeProfile}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}
            {activeTab === "scrape" && (
              <ScraperTab
                activeProfile={activeProfile}
                onDataChanged={refreshAll}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}
            {activeTab === "profiles" && (
              <ProfilesTab
                profiles={profiles}
                onProfileCreated={handleProfileCreated}
                onProfileDeleted={handleProfileDeleted}
              />
            )}
            {activeTab === "leads" && (
              <LeadsTab activeProfile={activeProfile} />
            )}
            {activeTab === "users" && (
              <UsersTab />
            )}
            {activeTab === "data" && (
              <DataTab activeProfile={activeProfile} />
            )}
            {activeTab === "jobs" && (
              <JobsTab activeProfile={activeProfile} />
            )}
            {activeTab === "api_docs" && (
              <ApiDocsTab activeProfile={activeProfile} />
            )}
          </>
        )}
      </main>

      {/* Global Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <p>India Biz Scraper Pro • React 19 + Vite Frontend on Vercel • Playwright + FastAPI Backend on Render • Aiven MySQL</p>
      </footer>

    </div>
  );
}
