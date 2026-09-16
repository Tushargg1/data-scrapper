import React from "react";
import { 
  Building2, Phone, Globe, PackageCheck, Play, 
  ArrowUpRight, Database, ShieldCheck, TrendingUp, Target, Zap
} from "lucide-react";

export default function DashboardTab({ stats, activeProfile, onNavigateTab }) {
  const total = stats?.total_businesses || 0;
  const phones = stats?.businesses_with_phone || 0;
  const webs = stats?.businesses_with_website || 0;
  const phoneRate = total > 0 ? Math.round((phones / total) * 100) : 0;
  const webRate = total > 0 ? Math.round((webs / total) * 100) : 0;

  return (
    <div className="space-y-7">
      
      {/* Hero Welcome Banner */}
      <div className="relative bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border border-slate-800 rounded-3xl p-7 sm:p-9 overflow-hidden">
        {/* Glow blobs */}
        <div className="absolute -top-20 -right-20 w-80 h-80 bg-emerald-500/8 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-64 h-64 bg-teal-500/6 rounded-full blur-3xl pointer-events-none" />
        
        {/* Thin accent bar */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-7">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-bold tracking-wider uppercase">
              <Zap className="w-3 h-3 fill-current" /> Live Lead Engine
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight leading-tight">
              B2B Lead Intelligence
              <br />
              <span className="text-emerald-400">Dashboard</span>
            </h1>
            <p className="text-slate-400 text-sm max-w-xl leading-relaxed">
              Extract targeted business records with verified phone numbers and websites across all Indian pincodes. Every lead is saved to your cloud database in real time.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigateTab("scrape")}
              className="bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-extrabold text-sm px-6 py-3.5 rounded-2xl shadow-xl shadow-emerald-500/20 transition-all flex items-center gap-2 hover:shadow-emerald-500/30 hover:-translate-y-0.5"
            >
              <Play className="w-4 h-4 fill-current" />
              Launch Scraper
            </button>
            <button
              onClick={() => onNavigateTab("data")}
              className="bg-slate-800 hover:bg-slate-750 text-white font-semibold text-sm px-5 py-3.5 rounded-2xl border border-slate-700 hover:border-slate-600 transition flex items-center gap-2"
            >
              View Leads
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <KpiCard
          label="Total Leads"
          value={total.toLocaleString()}
          sub={<><Database className="w-3 h-3 text-emerald-400 inline mr-1" />Stored in cloud database</>}
          color="emerald"
          icon={<Building2 className="w-4 h-4" />}
        />
        <KpiCard
          label="Phone Verified"
          value={phones.toLocaleString()}
          sub={<><strong className="text-emerald-400">{phoneRate}%</strong> have direct call numbers</>}
          color="blue"
          icon={<Phone className="w-4 h-4" />}
        />
        <KpiCard
          label="Websites Found"
          value={webs.toLocaleString()}
          sub={<><strong className="text-purple-400">{webRate}%</strong> available for outreach</>}
          color="purple"
          icon={<Globe className="w-4 h-4" />}
        />
        <KpiCard
          label="Lead Delivery"
          value="10-Batch"
          sub="Zero-duplicate batch dispatch API"
          color="amber"
          icon={<PackageCheck className="w-4 h-4" />}
          highlight
        />
      </div>

      {/* Feature Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        <FeatureCard
          onClick={() => onNavigateTab("scrape")}
          icon={<Target className="w-5 h-5" />}
          iconBg="bg-emerald-500/10 text-emerald-400"
          hoverBorder="hover:border-emerald-500/40"
          hoverText="group-hover:text-emerald-400"
          title="Scraper Studio"
          desc="Scrape pincodes across any niche — salons, clinics, lawyers, retailers — with real-time live feed."
        />
        <FeatureCard
          onClick={() => onNavigateTab("leads")}
          icon={<Phone className="w-5 h-5" />}
          iconBg="bg-blue-500/10 text-blue-400"
          hoverBorder="hover:border-blue-500/40"
          hoverText="group-hover:text-blue-400"
          title="Leads CRM"
          desc="Organize leads by status, update notes, filter by sent/unsent, and click-to-call business owners directly."
        />
        <FeatureCard
          onClick={() => onNavigateTab("jobs")}
          icon={<TrendingUp className="w-5 h-5" />}
          iconBg="bg-violet-500/10 text-violet-400"
          hoverBorder="hover:border-violet-500/40"
          hoverText="group-hover:text-violet-400"
          title="Coverage Tracker"
          desc="See every scraped pincode, its delivery progress, lead status breakdown, and re-scrape on demand."
        />
      </div>

    </div>
  );
}

function KpiCard({ label, value, sub, color, icon, highlight }) {
  const colors = {
    emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "group-hover:border-emerald-500/30" },
    blue:    { bg: "bg-blue-500/10",    text: "text-blue-400",    border: "group-hover:border-blue-500/30" },
    purple:  { bg: "bg-purple-500/10",  text: "text-purple-400",  border: "group-hover:border-purple-500/30" },
    amber:   { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "group-hover:border-amber-500/30" },
  };
  const c = colors[color] || colors.emerald;
  return (
    <div className={`group bg-slate-900 border border-slate-800 ${c.border} rounded-2xl p-5 transition-all space-y-2.5`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
        <div className={`w-8 h-8 rounded-xl ${c.bg} ${c.text} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <div className={`text-3xl font-black tracking-tight ${highlight ? "text-emerald-400" : "text-white"}`}>{value}</div>
      <div className="text-[11px] text-slate-500">{sub}</div>
    </div>
  );
}

function FeatureCard({ onClick, icon, iconBg, hoverBorder, hoverText, title, desc }) {
  return (
    <div
      onClick={onClick}
      className={`bg-slate-900 border border-slate-800 ${hoverBorder} rounded-2xl p-6 cursor-pointer group transition-all hover:-translate-y-0.5 space-y-3`}
    >
      <div className={`w-10 h-10 rounded-xl ${iconBg} flex items-center justify-center group-hover:scale-105 transition-transform`}>
        {icon}
      </div>
      <h3 className={`text-base font-bold text-white ${hoverText} transition-colors flex items-center justify-between`}>
        <span>{title}</span>
        <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-current transition-colors" />
      </h3>
      <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
    </div>
  );
}
