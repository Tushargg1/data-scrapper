import React, { useState, useEffect } from "react";
import { 
  Users, CheckCircle2, XCircle, Clock, UserPlus, 
  ShieldCheck, AlertCircle, Loader2, Key, RefreshCw 
} from "lucide-react";

import { getApiUsers, updateUserStatus, registerUser } from "../api";

export default function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");

  // Registration modal / form
  const [showAddUser, setShowAddUser] = useState(false);
  const [username, setUsername] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [userCode, setUserCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState({ text: "", isError: false });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await getApiUsers(statusFilter || undefined);
      setUsers(data || []);
    } catch (err) {
      console.error("Failed to load users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [statusFilter]);

  const handleUpdateStatus = async (code, newStatus) => {
    try {
      await updateUserStatus(code, newStatus);
      setUsers((prev) =>
        prev.map((u) => (u.user_code === code ? { ...u, status: newStatus } : u))
      );
      setMsg({ text: `User ${code} marked as ${newStatus}`, isError: false });
    } catch (err) {
      setMsg({ text: err.message || "Failed to update user", isError: true });
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!username || !phoneNumber || !userCode) {
      setMsg({ text: "All fields are required.", isError: true });
      return;
    }

    setSubmitting(true);
    try {
      await registerUser({
        username: username.trim(),
        phone_number: phoneNumber.trim(),
        user_code: userCode.trim()
      });
      setMsg({ text: `User "${username}" registered successfully! Status: PENDING`, isError: false });
      setUsername("");
      setPhoneNumber("");
      setUserCode("");
      setShowAddUser(false);
      fetchUsers();
    } catch (err) {
      setMsg({ text: err.message || "Registration failed.", isError: true });
    } finally {
      setSubmitting(false);
    }
  };

  const pendingCount = users.filter((u) => u.status === "PENDING").length;

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span>👥</span> User Access & Approval Control
            </h2>
            {pendingCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold animate-pulse">
                {pendingCount} Pending Approval
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Review user registration requests before allowing access to the 10-batch lead distribution API.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Users</option>
            <option value="PENDING">Pending Only</option>
            <option value="APPROVED">Approved Only</option>
            <option value="REJECTED">Rejected Only</option>
          </select>

          <button
            onClick={fetchUsers}
            title="Refresh users list"
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={() => setShowAddUser(true)}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5"
          >
            <UserPlus className="w-4 h-4" /> Register New User
          </button>
        </div>
      </div>


      {msg.text && (
        <div className={`p-4 rounded-xl text-xs flex items-center gap-2 ${
          msg.isError ? "bg-rose-500/10 border border-rose-500/30 text-rose-400" : "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
        }`}>
          {msg.isError ? <AlertCircle className="w-4 h-4 shrink-0" /> : <CheckCircle2 className="w-4 h-4 shrink-0" />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Users List */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
            Loading API users...
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No API users registered yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3.5 font-semibold">User Details</th>
                  <th className="p-3.5 font-semibold">Unique Access Code</th>
                  <th className="p-3.5 font-semibold">Current Status</th>
                  <th className="p-3.5 font-semibold">Registration Date</th>
                  <th className="p-3.5 font-semibold text-right">Approval Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {users.map((u) => {
                  const isPending = u.status === "PENDING";
                  const isApproved = u.status === "APPROVED";
                  const isRejected = u.status === "REJECTED";

                  return (
                    <tr key={u.id} className="hover:bg-slate-850/50 transition">
                      <td className="p-3.5 space-y-0.5">
                        <div className="font-bold text-white text-sm">{u.username}</div>
                        <div className="text-slate-400 font-mono text-[11px]">📱 {u.phone_number}</div>
                      </td>

                      <td className="p-3.5">
                        <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-emerald-400 font-bold">
                          {u.user_code}
                        </span>
                      </td>

                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                          isApproved ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                          isPending ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                          "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${
                            isApproved ? "bg-emerald-400" : isPending ? "bg-amber-400" : "bg-rose-400"
                          }`}></span>
                          {u.status}
                        </span>
                      </td>

                      <td className="p-3.5 text-slate-400 font-mono text-[11px]">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>

                      <td className="p-3.5 text-right space-x-2">
                        {isPending ? (
                          <>
                            <button
                              onClick={() => handleUpdateStatus(u.user_code, "APPROVED")}
                              className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition"
                            >
                              ✓ Approve
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(u.user_code, "REJECTED")}
                              className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold transition"
                            >
                              ✕ Reject
                            </button>
                          </>
                        ) : isApproved ? (
                          <button
                            onClick={() => handleUpdateStatus(u.user_code, "REJECTED")}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 text-[11px] transition"
                          >
                            Revoke Access
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpdateStatus(u.user_code, "APPROVED")}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-emerald-500/20 text-slate-400 hover:text-emerald-300 text-[11px] transition"
                          >
                            Re-Approve
                          </button>
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

      {/* Registration Modal */}
      {showAddUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-emerald-400" />
                Register API User
              </h3>
              <button onClick={() => setShowAddUser(false)} className="text-slate-400 hover:text-white text-sm">
                ✕
              </button>
            </div>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Username / Client Name</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Phone Number</label>
                <input
                  type="text"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="e.g. +91 9876543210"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Custom User Code</label>
                <input
                  type="text"
                  value={userCode}
                  onChange={(e) => setUserCode(e.target.value.toUpperCase())}
                  placeholder="e.g. RAHUL_01"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-white font-mono uppercase focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddUser(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition flex items-center gap-1.5"
                >
                  {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  Submit Registration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
