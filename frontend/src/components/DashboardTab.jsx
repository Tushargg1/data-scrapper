import React from "react";
import { 
  Building2, Phone, Globe, PackageCheck, Play, 
  ArrowUpRight, Database, ShieldCheck, Sparkles, TrendingUp 
} from "lucide-react";

export default function DashboardTab({ stats, activeProfile, onNavigateTab }) {
  const total = stats?.total_businesses || 0;
  const phones = stats?.businesses_with_phone || 0;
  const webs = stats?.businesses_with_website || 0;
  const phoneRate = total > 0 ? Math.round((phones / total) * 100) : 0;
  const webRate = total > 0 ? Math.round((webs / total) * 100) : 0;

  return (
    <div className="space-y-8">
      
      {/* Hero Welcome Banner */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-emerald-950/40 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" /> Google Maps Playwright Lead Engine
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white tracking-tight">
              High-Precision B2B Lead Scraper
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm max-w-2xl leading-relaxed">
              Extract targeted business records with full phone verification, websites, and Google Maps reviews across all Indian pincodes. Directly synchronized into your persistent Aiven MySQL Cloud Database.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigateTab("scrape")}
              className="bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-extrabold text-xs sm:text-sm px-6 py-3.5 rounded-2xl shadow-xl shadow-emerald-500/25 transition-all flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              Launch Scraper Studio
            </button>
            <button
              onClick={() => onNavigateTab("leads")}
              className="bg-slate-800/80 hover:bg-slate-750 text-white font-semibold text-xs sm:text-sm px-5 py-3.5 rounded-2xl border border-slate-700 transition flex items-center gap-2"
            >
              View Verified Leads
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Businesses */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Leads in DB</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white tracking-tight">{total}</div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <Database className="w-3 h-3 text-emerald-400" /> Synced with Aiven MySQL Cloud
          </div>
        </div>

        {/* Phone Verified */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Phone Verified</span>
            <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Phone className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white tracking-tight">{phones}</div>
          <div className="text-[11px] text-slate-400">
            <strong className="text-emerald-400">{phoneRate}%</strong> of database has direct calling numbers
          </div>
        </div>

        {/* With Website */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Websites Found</span>
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Globe className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white tracking-tight">{webs}</div>
          <div className="text-[11px] text-slate-400">
            <strong className="text-purple-400">{webRate}%</strong> websites available for outreach
          </div>
        </div>

        {/* Distribution Rate */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Lead Delivery</span>
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <PackageCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-emerald-400 tracking-tight">10-Batch API</div>
          <div className="text-[11px] text-slate-400">
            Zero-duplicate automated distribution
          </div>
        </div>

      </div>

      {/* Feature Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        <div
          onClick={() => onNavigateTab("scrape")}
          className="bg-slate-900 border border-slate-800 hover:border-emerald-500/50 rounded-2xl p-6 cursor-pointer group transition space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center group-hover:scale-110 transition">
            <Play className="w-5 h-5 fill-current" />
          </div>
          <h3 className="text-base font-bold text-white group-hover:text-emerald-400 transition flex items-center justify-between">
            <span>Playwright Scraper</span>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition" />
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Run headless Chromium element-based scraping across all Indian pincodes and custom niches with real-time feedback.
          </p>
        </div>

        <div
          onClick={() => onNavigateTab("leads")}
          className="bg-slate-900 border border-slate-800 hover:border-blue-500/50 rounded-2xl p-6 cursor-pointer group transition space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center group-hover:scale-110 transition">
            <Phone className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white group-hover:text-blue-400 transition flex items-center justify-between">
            <span>Leads CRM & Notes</span>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition" />
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Organize leads by contact status, update communication notes, and click-to-call owners directly.
          </p>
        </div>

        <div
          onClick={() => onNavigateTab("api_docs")}
          className="bg-slate-900 border border-slate-800 hover:border-purple-500/50 rounded-2xl p-6 cursor-pointer group transition space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center group-hover:scale-110 transition">
            <PackageCheck className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-white group-hover:text-purple-400 transition flex items-center justify-between">
            <span>10-Batch API Simulator</span>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition" />
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Test the automated batch distribution endpoint to safely dispatch 10 non-repeating leads to telecallers.
          </p>
        </div>

      </div>

    </div>
  );
}
