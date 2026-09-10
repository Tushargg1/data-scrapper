import React, { useState, useEffect } from "react";
import { 
  FolderPlus, Trash2, Key, Copy, Check, ExternalLink, 
  Sparkles, Layers, Tag, AlertCircle, Loader2 
} from "lucide-react";
import { getTemplates, createProfile, deleteProfile } from "../api";

export default function ProfilesTab({ profiles, onProfileCreated, onProfileDeleted }) {
  const [templates, setTemplates] = useState({});
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [icon, setIcon] = useState("💼");
  const [customNichesText, setCustomNichesText] = useState("");
  const [selectedTemplateNiches, setSelectedTemplateNiches] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [copiedKeySlug, setCopiedKeySlug] = useState(null);

  useEffect(() => {
    setLoadingTemplates(true);
    getTemplates()
      .then((data) => setTemplates(data || {}))
      .catch((err) => console.error("Could not load templates:", err))
      .finally(() => setLoadingTemplates(false));
  }, []);

  const handleApplyTemplate = (tmplName, tmplData) => {
    setName(tmplName);
    setDescription(tmplData.description || "");
    setIcon(tmplData.icon || "📁");
    setSelectedTemplateNiches(tmplData.niches || []);
    setCustomNichesText((tmplData.niches || []).join("\n"));
  };

  const handleCreateProfile = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!name.trim()) {
      setErrorMsg("Profile name is required.");
      return;
    }

    const niches = customNichesText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);

    if (niches.length === 0) {
      setErrorMsg("Add at least one niche or category.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await createProfile({
        name: name.trim(),
        description: description.trim(),
        icon: icon.trim() || "📁",
        niches: niches
      });

      setSuccessMsg(`Profile "${name}" created successfully with API Key: ${res.profile?.api_key || ""}`);
      setName("");
      setDescription("");
      setCustomNichesText("");
      if (onProfileCreated) onProfileCreated(res.profile);
    } catch (err) {
      setErrorMsg(err.message || "Failed to create profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (slug, profileName) => {
    const enteredPassword = window.prompt(
      `🔒 SECURITY VERIFICATION REQUIRED\n\nPermanently deleting profile "${profileName}" and all its scraped business records.\n\nEnter the deletion password to authorize:`
    );
    if (!enteredPassword) return;

    try {
      await deleteProfile(slug, enteredPassword.trim());
      if (onProfileDeleted) onProfileDeleted(slug);
      alert(`✅ Profile "${profileName}" was deleted successfully.`);
    } catch (err) {
      alert("❌ Deletion Failed: " + (err.message || "Incorrect deletion password."));
    }
  };


  const copyKey = (slug, key) => {
    navigator.clipboard.writeText(key);
    setCopiedKeySlug(slug);
    setTimeout(() => setCopiedKeySlug(null), 2000);
  };

  return (
    <div className="space-y-8">
      
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <span>🗂️</span> Profile & Industry Workspaces
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Create separate workspaces with dedicated niche lists, API keys, and isolated database records.
        </p>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <Check className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Grid: Create Form + Templates */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Create Profile Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 lg:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <FolderPlus className="w-4 h-4 text-emerald-400" /> Create New Workspace
          </h3>

          <form onSubmit={handleCreateProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="sm:col-span-1">
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Icon Emoji</label>
                <input
                  type="text"
                  value={icon}
                  onChange={(e) => setIcon(e.target.value)}
                  placeholder="💼"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-center text-lg focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="sm:col-span-3">
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Workspace Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Car Dealers, Beauty & Saloon, Real Estate..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Description (Optional)</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of target businesses..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Niches & Categories (One per line or comma-separated)
              </label>
              <textarea
                value={customNichesText}
                onChange={(e) => setCustomNichesText(e.target.value)}
                placeholder={"Hair Salon\nBeauty Parlour\nBridal Makeup Artist\nSpa & Massage"}
                rows={5}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-5 py-2.5 rounded-xl transition flex items-center gap-2"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderPlus className="w-4 h-4" />}
              Create Isolated Profile
            </button>
          </form>
        </div>

        {/* Quick Industry Templates Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sparkles className="w-4 h-4 text-indigo-400" /> Industry Templates
          </h3>
          <p className="text-[11px] text-slate-400">Click a template to auto-fill the form with curated niche keywords:</p>

          <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
            {Object.entries(templates).map(([tName, tData]) => (
              <button
                key={tName}
                type="button"
                onClick={() => handleApplyTemplate(tName, tData)}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 hover:bg-slate-850 border border-slate-800/80 hover:border-slate-700 transition space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>{tData.icon || "📁"}</span> {tName}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                    {tData.niche_count || (tData.niches ? tData.niches.length : 0)} niches
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 truncate">{tData.description}</p>
              </button>
            ))}
          </div>
        </div>

      </div>

      {/* Existing Profiles List */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
          <Layers className="w-4 h-4 text-emerald-400" /> Active Profiles ({profiles.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((p) => (
            <div key={p.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4.5 space-y-3 hover:border-slate-700 transition">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="text-2xl">{p.icon || "📁"}</span>
                  <div>
                    <h4 className="text-sm font-bold text-white">{p.name}</h4>
                    <span className="text-[11px] text-slate-400 font-mono">slug: {p.slug}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(p.slug, p.name)}
                  title="Delete Profile"
                  className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs text-slate-400 line-clamp-2">{p.description || "No description provided."}</p>

              <div className="space-y-1.5 pt-1">
                <div className="text-[11px] font-semibold text-slate-300">
                  Niches ({p.niches ? p.niches.length : 0}):
                </div>
                <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                  {p.niches && p.niches.map((n, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-850 text-slate-300 border border-slate-800">
                      {n}
                    </span>
                  ))}
                </div>
              </div>

              {/* API Key Box */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-mono text-slate-400">
                  <Key className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[11px] truncate max-w-[170px]">{p.api_key}</span>
                </div>
                <button
                  onClick={() => copyKey(p.slug, p.api_key)}
                  className="p-1 text-slate-400 hover:text-emerald-400 rounded transition"
                  title="Copy API Key"
                >
                  {copiedKeySlug === p.slug ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
