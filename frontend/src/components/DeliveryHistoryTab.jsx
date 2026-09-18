import React, { useState, useEffect } from "react";
import { Loader2, Calendar, User, Phone, CheckCircle, RefreshCw, Send, Users } from "lucide-react";
import { getDeliveryHistory } from "../api";

export default function DeliveryHistoryTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getDeliveryHistory(1000);
      setHistory(data);
    } catch (err) {
      console.error(err);
      alert("Failed to fetch delivery history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatDate = (isoString) => {
    if (!isoString) return "N/A";
    const d = new Date(isoString);
    return isNaN(d.getTime()) ? isoString : d.toLocaleString();
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto min-h-screen">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Send className="w-8 h-8 text-emerald-400" />
            Delivery History
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            Track which telecallers requested data and the specific leads sent to them.
          </p>
        </div>
        <button
          onClick={fetchHistory}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm transition font-medium shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-400" />
            Recent Deliveries
          </h2>
          <span className="text-xs font-mono text-slate-500 bg-slate-900 px-2 py-1 rounded border border-slate-800">
            {history.length} records found
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/50 text-slate-400 text-xs border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-medium">Timestamp</th>
                <th className="px-6 py-4 font-medium">Requested By</th>
                <th className="px-6 py-4 font-medium">Business Sent</th>
                <th className="px-6 py-4 font-medium">Niche</th>
                <th className="px-6 py-4 font-medium">Business Phone</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
                    Loading history...
                  </td>
                </tr>
              ) : history.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-slate-500">
                    <CheckCircle className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                    No deliveries recorded yet.
                  </td>
                </tr>
              ) : (
                history.map((record) => (
                  <tr key={record.history_id} className="hover:bg-slate-800/30 transition">
                    <td className="px-6 py-4 text-xs font-mono text-slate-400">
                      {formatDate(record.sent_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-emerald-400 font-medium">
                          {record.username || "Unknown"}
                        </span>
                        <span className="text-xs font-mono bg-slate-950 px-1.5 py-0.5 rounded text-slate-500 w-max border border-slate-800">
                          {record.user_code}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-medium text-white truncate max-w-[250px]">
                      {record.business_name || "N/A"}
                    </td>
                    <td className="px-6 py-4 text-xs">
                      {record.niche ? (
                        <span className="px-2 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700">
                          {record.niche}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-300 font-mono text-xs">
                      {record.business_phone || "N/A"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
