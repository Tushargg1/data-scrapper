import React, { useState, useEffect } from "react";
import { 
  Search, Filter, Phone, Globe, Star, MapPin, 
  CheckCircle, MessageSquare, ExternalLink, Loader2, Edit3, CheckSquare, Square
} from "lucide-react";
import { getBusinesses, updateLeadStatus, bulkUpdateLeadStatus } from "../api";

const LEAD_STATUS_OPTIONS = [
  "🆕 New Lead",
  "📤 Sent",
  "📞 Contacted",
  "💬 In Discussion",
  "🤝 Closed / Won",
  "❌ Not Interested",
  "🚫 Invalid Number"
];

export default function LeadsTab({ activeProfile }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Bulk Selection
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkUpdating, setBulkUpdating] = useState(false);

  // Filters
  const [hasPhone, setHasPhone] = useState(null);
  const [hasWeb, setHasWeb] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState("");
  // Hide "🆕 New Lead" by default — CRM only shows actioned leads
  const [hideNewLeads, setHideNewLeads] = useState(true);

  // Editing notes modal
  const [editingLead, setEditingLead] = useState(null);
  const [tempNotes, setTempNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

  const fetchLeads = async () => {
    if (!activeProfile) return;
    setLoading(true);
    try {
      const params = {
        limit: 300,
        has_phone: hasPhone,
        has_website: hasWeb,
        lead_status: selectedStatus || undefined
      };
      const res = await getBusinesses(activeProfile.slug, activeProfile.api_key, params);
      setLeads(res.businesses || []);
    } catch (err) {
      console.error("Failed to load leads:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [activeProfile, hasPhone, hasWeb, selectedStatus]);


  const handleStatusChange = async (bizId, newStatus, currentNotes) => {
    try {
      await updateLeadStatus(activeProfile.slug, bizId, newStatus, currentNotes, activeProfile.api_key);
      setLeads((prev) =>
        prev.map((b) => (b.id === bizId ? { ...b, lead_status: newStatus } : b))
      );
    } catch (err) {
      alert("Failed to update status: " + err.message);
    }
  };

  const handleSaveNotes = async () => {
    if (!editingLead) return;
    setSavingNotes(true);
    try {
      await updateLeadStatus(activeProfile.slug, editingLead.id, editingLead.lead_status, tempNotes, activeProfile.api_key);
      setLeads((prev) =>
        prev.map((b) => (b.id === editingLead.id ? { ...b, notes: tempNotes } : b))
      );
      setEditingLead(null);
    } catch (err) {
      alert("Failed to save notes: " + err.message);
    } finally {
      setSavingNotes(false);
    }
  };

  const filteredLeads = leads.filter((b) => {
    // Hide "New Lead" entries by default — they go to batch delivery, not CRM
    if (hideNewLeads && b.lead_status === "🆕 New Lead") return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const txt = [
      b.name, b.niche, b.phone, b.phone_2, b.pincode, b.state, b.notes, b.lead_status
    ].filter(Boolean).join(" ").toLowerCase();
    return txt.includes(q);
  });

  const newLeadCount = leads.filter((b) => b.lead_status === "🆕 New Lead").length;

  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const allVisibleSelected =
    filteredLeads.length > 0 && filteredLeads.every((b) => selectedIds.includes(b.id));

  const handleToggleSelectAll = () => {
    if (allVisibleSelected) {
      const visibleSet = new Set(filteredLeads.map((b) => b.id));
      setSelectedIds((prev) => prev.filter((id) => !visibleSet.has(id)));
    } else {
      const visibleIds = filteredLeads.map((b) => b.id);
      setSelectedIds((prev) => Array.from(new Set([...prev, ...visibleIds])));
    }
  };

  const handleBulkStatus = async (newStatus) => {
    if (!selectedIds.length || !activeProfile) return;
    setBulkUpdating(true);
    try {
      await bulkUpdateLeadStatus(
        activeProfile.slug,
        selectedIds,
        newStatus,
        null,
        activeProfile.api_key
      );
      setLeads((prev) =>
        prev.map((b) => (selectedIds.includes(b.id) ? { ...b, lead_status: newStatus } : b))
      );
      setSelectedIds([]);
    } catch (err) {
      alert("Bulk update failed: " + err.message);
    } finally {
      setBulkUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span>👤</span> Leads CRM & Outreach Management
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Track outreach progress, phone numbers, and communication notes in real time.
            </p>
          </div>

        <div className="flex flex-col items-end gap-1">
            <div className="text-xs text-slate-400 font-mono">
              Showing: <strong className="text-emerald-400">{filteredLeads.length} actioned leads</strong>
            </div>
            {newLeadCount > 0 && (
              <button
                onClick={() => setHideNewLeads(h => !h)}
                className={`text-[10px] px-2.5 py-1 rounded-full border font-semibold transition ${
                  hideNewLeads
                    ? "bg-slate-800 border-slate-600 text-slate-400 hover:border-amber-500 hover:text-amber-300"
                    : "bg-amber-500/20 border-amber-500/50 text-amber-300"
                }`}
              >
                {hideNewLeads
                  ? `+ Show ${newLeadCount} New Lead${newLeadCount !== 1 ? "s" : ""} (queued for delivery)`
                  : `Hide ${newLeadCount} New Lead${newLeadCount !== 1 ? "s" : ""}`}
              </button>
            )}
          </div>

        </div>

        {/* Filters Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2">
          {/* Search Box */}
          <div className="lg:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by business name, phone, niche..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Lead Status Filter */}
          <div>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">All Statuses</option>
              {LEAD_STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          {/* Has Phone Filter */}
          <div>
            <select
              value={hasPhone === null ? "" : hasPhone ? "yes" : "no"}
              onChange={(e) => {
                const val = e.target.value;
                setHasPhone(val === "" ? null : val === "yes");
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Phone: Any</option>
              <option value="yes">📞 Has Phone Only</option>
              <option value="no">No Phone</option>
            </select>
          </div>

          {/* Has Website Filter */}
          <div>
            <select
              value={hasWeb === null ? "" : hasWeb ? "yes" : "no"}
              onChange={(e) => {
                const val = e.target.value;
                setHasWeb(val === "" ? null : val === "yes");
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Website: Any</option>
              <option value="yes">🌐 Has Website Only</option>
              <option value="no">No Website</option>
            </select>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
            Loading leads from Aiven MySQL...
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No leads found matching your filters.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[640px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-950 text-slate-400 sticky top-0 z-10 border-b border-slate-800">
                <tr>
                  <th className="p-3.5 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={allVisibleSelected}
                      onChange={handleToggleSelectAll}
                      className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 cursor-pointer w-4 h-4 accent-emerald-500"
                      title={allVisibleSelected ? "Deselect all visible leads" : "Select all visible leads"}
                    />
                  </th>
                  <th className="p-3.5 font-semibold">Business Info</th>
                  <th className="p-3.5 font-semibold">Lead Status</th>
                  <th className="p-3.5 font-semibold">Phone Contacts</th>
                  <th className="p-3.5 font-semibold">Rating & Web</th>
                  <th className="p-3.5 font-semibold">Notes</th>
                  <th className="p-3.5 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredLeads.map((b) => {
                  const currentStatus = b.lead_status || "🆕 New Lead";
                  const isSelected = selectedIds.includes(b.id);

                  return (
                    <tr
                      key={b.id}
                      className={`transition ${
                        isSelected
                          ? "bg-emerald-950/50 border-l-4 border-l-emerald-400"
                          : b.is_sent || b.lead_status === "📤 Sent"
                          ? "bg-emerald-950/30 hover:bg-emerald-900/40 border-l-4 border-l-emerald-500 shadow-sm shadow-emerald-500/5"
                          : "hover:bg-slate-850/50 border-l-4 border-l-transparent"
                      }`}
                    >
                      {/* Checkbox Column */}
                      <td className="p-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelect(b.id)}
                          className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 cursor-pointer w-4 h-4 accent-emerald-500"
                        />
                      </td>
                      
                      {/* Name & Niche */}
                      <td className="p-3.5 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`font-bold text-sm ${b.is_sent || b.lead_status === "📤 Sent" ? "text-emerald-200" : "text-white"}`}>
                            {b.name}
                          </span>
                          {(b.is_sent || b.lead_status === "📤 Sent") && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-bold text-[10px]">
                              <CheckCircle className="w-3 h-3 text-emerald-400" />
                              <span>Sent {b.sent_to_user_code ? `(${b.sent_to_user_code})` : ''}</span>
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
                            {b.niche}
                          </span>
                          <span className="text-slate-500 text-[11px]">PIN: {b.pincode} ({b.state})</span>
                        </div>
                      </td>

                      {/* Lead Status Dropdown */}
                      <td className="p-3.5">
                        <select
                          value={currentStatus}
                          onChange={(e) => handleStatusChange(b.id, e.target.value, b.notes)}
                          className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
                        >
                          {LEAD_STATUS_OPTIONS.map((st) => (
                            <option key={st} value={st}>{st}</option>
                          ))}
                        </select>
                      </td>

                      {/* Phone Contacts */}
                      <td className="p-3.5 space-y-1">
                        {b.phone && b.phone !== "N/A" ? (
                          <div className="flex items-center gap-2">
                            <a
                              href={`tel:${b.phone}`}
                              className="font-mono text-emerald-400 font-semibold hover:underline flex items-center gap-1"
                            >
                              <Phone className="w-3 h-3 text-emerald-400" />
                              {b.phone}
                            </a>
                          </div>
                        ) : (
                          <span className="text-slate-600 text-xs">No primary phone</span>
                        )}

                        {b.phone_2 && (
                          <div className="font-mono text-slate-400 text-[11px] flex items-center gap-1">
                            <span>📞 {b.phone_2}</span>
                          </div>
                        )}
                        {b.phone_3 && (
                          <div className="font-mono text-slate-400 text-[11px] flex items-center gap-1">
                            <span>📞 {b.phone_3}</span>
                          </div>
                        )}
                      </td>

                      {/* Rating & Web */}
                      <td className="p-3.5 space-y-1">
                        <div className="flex items-center gap-1.5 text-amber-400 font-medium">
                          <Star className="w-3.5 h-3.5 fill-current" />
                          <span>{b.rating || "N/A"}</span>
                          <span className="text-slate-500 font-normal">({b.reviews || 0})</span>
                        </div>

                        {b.website_link && b.website_link !== "N/A" && !b.website_link.includes("google.") && !b.website_link.includes("gstatic.") ? (
                          <a
                            href={b.website_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:underline flex items-center gap-1 text-[11px] truncate max-w-[130px]"
                          >
                            <Globe className="w-3 h-3" />
                            <span>Visit Site</span>
                          </a>
                        ) : (
                          <span className="text-slate-600 text-[11px]">No website</span>
                        )}
                      </td>

                      {/* Notes Column */}
                      <td className="p-3.5">
                        <div
                          onClick={() => {
                            setEditingLead(b);
                            setTempNotes(b.notes || "");
                          }}
                          className="cursor-pointer group flex items-start gap-1.5 max-w-[180px]"
                          title="Click to edit notes"
                        >
                          <span className="text-xs text-slate-300 line-clamp-2">
                            {b.notes || <em className="text-slate-600">Add notes...</em>}
                          </span>
                          <Edit3 className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 shrink-0 mt-0.5" />
                        </div>
                      </td>

                      {/* Maps Link */}
                      <td className="p-3.5">
                        {b.maps_url && b.maps_url.startsWith("http") ? (
                          <a
                            href={b.maps_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-indigo-400 hover:underline text-[11px] flex items-center gap-1"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>Open Maps</span>
                          </a>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Notes Modal */}
      {editingLead && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                Notes for {editingLead.name}
              </h3>
              <button onClick={() => setEditingLead(null)} className="text-slate-400 hover:text-white text-sm">
                ✕
              </button>
            </div>

            <textarea
              value={tempNotes}
              onChange={(e) => setTempNotes(e.target.value)}
              placeholder="e.g. Called owner on Monday, interested in CRM software, callback scheduled for Friday 3 PM..."
              rows={5}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-white focus:outline-none focus:border-emerald-500 font-sans resize-none"
            />

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingLead(null)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveNotes}
                disabled={savingNotes}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition flex items-center gap-1.5"
              >
                {savingNotes ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                Save Notes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Bulk Actions Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 backdrop-blur-md border border-emerald-500/40 rounded-2xl p-3 px-5 shadow-2xl shadow-emerald-950/60 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-3 border-r border-slate-700">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-bold text-white font-mono">
              {selectedIds.length} lead{selectedIds.length > 1 ? "s" : ""} selected
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBulkStatus("📞 Contacted")}
              disabled={bulkUpdating}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
            >
              {bulkUpdating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>📞</span>}
              Mark Contacted
            </button>

            <button
              onClick={() => handleBulkStatus("❌ Not Interested")}
              disabled={bulkUpdating}
              className="bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
            >
              {bulkUpdating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>❌</span>}
              Mark Not Interested
            </button>

            <select
              onChange={(e) => {
                if (e.target.value) {
                  handleBulkStatus(e.target.value);
                  e.target.value = "";
                }
              }}
              disabled={bulkUpdating}
              defaultValue=""
              className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500 cursor-pointer font-medium disabled:opacity-50"
            >
              <option value="" disabled>Change Status to...</option>
              {LEAD_STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setSelectedIds([])}
            className="text-xs text-slate-400 hover:text-white pl-2 transition font-medium underline underline-offset-2"
          >
            Deselect All
          </button>
        </div>
      )}

    </div>
  );
}
