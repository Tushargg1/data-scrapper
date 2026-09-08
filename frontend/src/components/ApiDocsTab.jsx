import React, { useState } from "react";
import { 
  Code2, Play, Copy, Check, ExternalLink, 
  Send, Package, AlertCircle, Loader2 
} from "lucide-react";
import { fetchBatchDelivery } from "../api";
import { getApiBaseUrl, ADMIN_API_KEY } from "../config";

export default function ApiDocsTab({ activeProfile }) {
  const [testUserCode, setTestUserCode] = useState("");
  const [batchResult, setBatchResult] = useState(null);
  const [loadingBatch, setLoadingBatch] = useState(false);
  const [batchError, setBatchError] = useState("");

  const [copiedCurl, setCopiedCurl] = useState(false);

  const baseUrl = getApiBaseUrl();
  const slug = activeProfile?.slug || "beauty-saloon";
  const apiKey = activeProfile?.api_key || "YOUR_PROFILE_API_KEY";

  const handleTestBatch = async (e) => {
    e.preventDefault();
    if (!testUserCode.trim()) {
      setBatchError("Please enter an approved user code (e.g. from the User Approvals tab).");
      return;
    }

    setBatchError("");
    setBatchResult(null);
    setLoadingBatch(true);
    try {
      const res = await fetchBatchDelivery(testUserCode.trim());
      setBatchResult(res);
    } catch (err) {
      setBatchError(err.message || "Failed to fetch batch leads.");
    } finally {
      setLoadingBatch(false);
    }
  };

  const curlSnippet = `curl -H "X-User-Code: YOUR_APPROVED_CODE" \\
  "${baseUrl}/api/data/batch"`;

  const copySnippet = (txt) => {
    navigator.clipboard.writeText(txt);
    setCopiedCurl(true);
    setTimeout(() => setCopiedCurl(false), 2000);
  };

  return (
    <div className="space-y-8">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🔌</span> REST API Documentation & 10-Batch Playground
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Test the zero-duplicate 10-batch distribution engine and integrate with mobile apps, CRMs, or automations.
          </p>
        </div>

        <a
          href={`${baseUrl}/docs`}
          target="_blank"
          rel="noreferrer"
          className="bg-slate-800 hover:bg-slate-750 text-white text-xs font-semibold px-4 py-2.5 rounded-xl border border-slate-700 transition flex items-center gap-1.5"
        >
          <ExternalLink className="w-4 h-4" /> Open Swagger UI (/docs)
        </a>
      </div>

      {/* 10-Batch Interactive Tester */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950/30 border border-indigo-500/20 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <Package className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-white">
            Live 10-Batch Delivery Simulator
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Enter an approved user code to request up to 10 un-sent businesses. Each lead is marked as sent atomically to avoid duplicate delivery across telecallers.
        </p>

        <form onSubmit={handleTestBatch} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={testUserCode}
            onChange={(e) => setTestUserCode(e.target.value.toUpperCase())}
            placeholder="ENTER_USER_CODE (e.g. from Users tab)"
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 font-mono uppercase focus:outline-none focus:border-emerald-500"
          />
          <button
            type="submit"
            disabled={loadingBatch}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-6 py-2.5 rounded-xl transition flex items-center justify-center gap-2"
          >
            {loadingBatch ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Request 10 Leads
          </button>
        </form>

        {batchError && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{batchError}</span>
          </div>
        )}

        {batchResult && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-emerald-400">{batchResult.message}</span>
              <span className="font-mono text-slate-400">Delivered: {batchResult.batch_size} businesses</span>
            </div>

            {batchResult.businesses && batchResult.businesses.length > 0 ? (
              <div className="overflow-x-auto max-h-56 border border-slate-800/80 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400">
                    <tr>
                      <th className="p-2">Name</th>
                      <th className="p-2">Phone</th>
                      <th className="p-2">Niche</th>
                      <th className="p-2">Pincode</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {batchResult.businesses.map((b, i) => (
                      <tr key={i} className="hover:bg-slate-900/50">
                        <td className="p-2 font-medium text-white">{b.name}</td>
                        <td className="p-2 font-mono text-emerald-400">{b.phone || "—"}</td>
                        <td className="p-2">{b.niche}</td>
                        <td className="p-2 text-slate-400">{b.pincode}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500">All available leads for this profile have already been distributed!</p>
            )}
          </div>
        )}
      </div>

      {/* Code Snippets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* cURL Request */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Code2 className="w-4 h-4 text-emerald-400" /> 10-Batch Distribution (cURL)
            </h4>
            <button
              onClick={() => copySnippet(curlSnippet)}
              className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1"
            >
              {copiedCurl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedCurl ? "Copied" : "Copy"}</span>
            </button>
          </div>
          <pre className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-emerald-400 font-mono overflow-x-auto">
            {curlSnippet}
          </pre>
        </div>

        {/* Python Request */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Code2 className="w-4 h-4 text-indigo-400" /> Python Integration
            </h4>
          </div>
          <pre className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-indigo-300 font-mono overflow-x-auto">{`import requests

res = requests.get(
    "${baseUrl}/api/data/batch",
    headers={"X-User-Code": "YOUR_CODE"}
)
data = res.json()
print("Batch received:", len(data["businesses"]))`}</pre>
        </div>

      </div>

    </div>
  );
}
