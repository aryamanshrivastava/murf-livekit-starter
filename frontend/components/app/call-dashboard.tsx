'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle,
  Clock,
  Filter,
  PhoneCall,
  PhoneIncoming,
  PhoneOutgoing,
  RefreshCw,
  Search,
  ShieldCheck,
  Store,
  TrendingUp,
  X,
  XCircle,
} from 'lucide-react';

export interface CallRecord {
  call_id: string;
  room_name: string;
  seller_id?: string | null;
  outbound?: number | boolean;
  outcome: 'SUCCESS' | 'FAILED' | string;
  reason?: string | null;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
}

export interface CallMetrics {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  recent_calls: CallRecord[];
}

interface CallDashboardProps {
  onBackToAgent?: () => void;
}

export function CallDashboard({ onBackToAgent }: CallDashboardProps) {
  const [metrics, setMetrics] = useState<CallMetrics>({
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
    recent_calls: [],
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedOutcome, setSelectedOutcome] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  // Detail Modal
  const [activeCall, setActiveCall] = useState<CallRecord | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/calls', { cache: 'no-store' });
      const data = await res.json();
      if (data.success && data.metrics) {
        setMetrics(data.metrics);
      } else {
        setMetrics({
          total_calls: 0,
          successful_calls: 0,
          failed_calls: 0,
          recent_calls: [],
        });
      }
    } catch (err) {
      console.error('Error loading call metrics:', err);
      setError('Unable to load call metrics. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const { total_calls, successful_calls, failed_calls, recent_calls } = metrics;
  const successRate = total_calls > 0 ? Math.round((successful_calls / total_calls) * 100) : 0;

  // Filter Logic
  const filteredCalls = recent_calls.filter((call) => {
    const outcomeMatch =
      selectedOutcome === 'ALL' || (call.outcome || '').toUpperCase() === selectedOutcome;

    const isOutbound = Boolean(call.outbound);
    const typeMatch =
      selectedType === 'ALL' ||
      (selectedType === 'OUTBOUND' && isOutbound) ||
      (selectedType === 'INBOUND' && !isOutbound);

    const searchLower = searchQuery.toLowerCase().trim();
    const searchMatch =
      !searchLower ||
      (call.call_id || '').toLowerCase().includes(searchLower) ||
      (call.seller_id || '').toLowerCase().includes(searchLower) ||
      (call.reason || '').toLowerCase().includes(searchLower) ||
      (call.room_name || '').toLowerCase().includes(searchLower);

    return outcomeMatch && typeMatch && searchMatch;
  });

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds <= 0) return '0s';
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    if (m === 0) return `${s}s`;
    return `${m}m ${s}s`;
  };

  const formatTimestamp = (isoStr: string) => {
    if (!isoStr) return 'N/A';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="bg-background text-foreground flex min-h-svh w-full flex-col p-4 sm:p-6 lg:p-8">
      {/* Header with Controls */}
      <div className="border-border/40 mb-6 flex flex-col gap-4 border-b pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Call Analytics Dashboard</h1>
            <span className="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
              Live Voice Call Outcomes
            </span>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Real-time performance & outcome tracking for Priya (Daily Bazaar Assistant).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {onBackToAgent ? (
            <button
              onClick={onBackToAgent}
              className="border-border/60 bg-muted/40 text-foreground hover:bg-muted inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-all"
            >
              ← Return to Agent
            </button>
          ) : (
            <a
              href="/"
              className="border-border/60 bg-muted/40 text-foreground hover:bg-muted inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-all"
            >
              ← Return to Home
            </a>
          )}

          <a
            href="/escalations"
            className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-all"
          >
            ⚠️ Escalations →
          </a>

          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-amber-600/20 transition-all hover:scale-[1.02] hover:bg-amber-700 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs font-semibold text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Metrics Row (4 Cards) */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {/* Total Calls */}
        <div className="flex flex-col justify-between rounded-2xl border border-blue-500/20 bg-blue-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-blue-600 dark:text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Calls</span>
            <PhoneCall className="size-5" />
          </div>
          <div className="text-foreground mt-3 text-3xl font-extrabold">{total_calls}</div>
          <div className="text-muted-foreground mt-1 text-[11px]">Logged to database</div>
        </div>

        {/* Successful */}
        <div className="flex flex-col justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-emerald-600 dark:text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Successful</span>
            <CheckCircle className="size-5" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
            {successful_calls}
          </div>
          <div className="text-muted-foreground mt-1 text-[11px]">Enquiry completed</div>
        </div>

        {/* Failed */}
        <div className="flex flex-col justify-between rounded-2xl border border-red-500/20 bg-red-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-red-600 dark:text-red-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Failed</span>
            <XCircle className="size-5" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-red-600 dark:text-red-400">
            {failed_calls}
          </div>
          <div className="text-muted-foreground mt-1 text-[11px]">Condition not met</div>
        </div>

        {/* Success Rate */}
        <div className="flex flex-col justify-between rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-amber-600 dark:text-amber-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Success Rate</span>
            <TrendingUp className="size-5" />
          </div>
          <div className="text-foreground mt-3 text-3xl font-extrabold">{successRate}%</div>
          <div className="text-muted-foreground mt-1 text-[11px]">Completion average</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="border-border/60 bg-muted/20 mb-6 flex flex-col gap-3 rounded-2xl border p-3.5 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by Call ID, Shop Name, Reason, or Details..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-background text-foreground border-border/60 placeholder:text-muted-foreground w-full rounded-xl border py-2 pr-3 pl-9 text-xs font-medium focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="text-muted-foreground flex items-center gap-1.5 font-semibold">
            <Filter className="size-3.5" /> Filters:
          </div>

          {/* Outcome Filter */}
          <select
            value={selectedOutcome}
            onChange={(e) => setSelectedOutcome(e.target.value)}
            className="bg-background text-foreground border-border/60 rounded-xl border px-3 py-2 text-xs font-medium focus:border-amber-500 focus:outline-none"
          >
            <option value="ALL">All Outcomes</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="FAILED">FAILED</option>
          </select>

          {/* Call Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-background text-foreground border-border/60 rounded-xl border px-3 py-2 text-xs font-medium focus:border-amber-500 focus:outline-none"
          >
            <option value="ALL">All Call Types</option>
            <option value="INBOUND">Inbound</option>
            <option value="OUTBOUND">Outbound</option>
          </select>

          {(selectedOutcome !== 'ALL' || selectedType !== 'ALL' || searchQuery) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedOutcome('ALL');
                setSelectedType('ALL');
              }}
              className="text-amber-600 hover:text-amber-700 dark:text-amber-400 font-semibold px-2 py-1 transition-all"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table View */}
      <div className="border-border/60 bg-card overflow-hidden rounded-2xl border shadow-sm flex-1">
        {loading && recent_calls.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center justify-center p-12 text-center text-xs">
            <RefreshCw className="mb-2 size-6 animate-spin text-amber-500" />
            Loading call outcome records...
          </div>
        ) : filteredCalls.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center justify-center p-12 text-center text-xs">
            <PhoneCall className="mb-2 size-8 text-amber-500/40" />
            No call records match your selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 text-muted-foreground border-border/40 border-b text-[11px] font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3.5">Outcome</th>
                  <th className="px-4 py-3.5">Type</th>
                  <th className="px-4 py-3.5">Shop / Seller</th>
                  <th className="px-4 py-3.5">Duration</th>
                  <th className="px-4 py-3.5">Reason / Details</th>
                  <th className="px-4 py-3.5">Time</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-border/40 divide-y font-medium">
                {filteredCalls.map((call) => {
                  const isSuccess = (call.outcome || '').toUpperCase() === 'SUCCESS';
                  const isOutbound = Boolean(call.outbound);

                  return (
                    <tr
                      key={call.call_id}
                      className="hover:bg-muted/30 cursor-pointer transition-colors"
                      onClick={() => setActiveCall(call)}
                    >
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                            isSuccess
                              ? 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30 dark:text-emerald-400'
                              : 'bg-red-500/15 text-red-600 border-red-500/30 dark:text-red-400'
                          }`}
                        >
                          {isSuccess ? <CheckCircle className="size-3" /> : <XCircle className="size-3" />}
                          {call.outcome}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {isOutbound ? (
                          <span className="inline-flex items-center gap-1 font-semibold text-blue-600 dark:text-blue-400">
                            <PhoneOutgoing className="size-3" /> Outbound
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                            <PhoneIncoming className="size-3" /> Inbound
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 whitespace-nowrap text-foreground">
                        <span className="inline-flex items-center gap-1.5 font-bold">
                          <Store className="text-muted-foreground size-3.5" />
                          {call.seller_id || 'Unidentified Shop'}
                        </span>
                      </td>

                      <td className="text-muted-foreground px-4 py-3.5 whitespace-nowrap">
                        {formatDuration(call.duration_seconds)}
                      </td>

                      <td className="text-muted-foreground max-w-xs truncate px-4 py-3.5">
                        {call.reason || (isSuccess ? 'Completed enquiry' : 'Condition not met')}
                      </td>

                      <td className="text-muted-foreground px-4 py-3.5 whitespace-nowrap font-mono text-[11px]">
                        {formatTimestamp(call.started_at)}
                      </td>

                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveCall(call);
                          }}
                          className="border-border/60 bg-muted/40 text-foreground hover:bg-muted rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-all"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Step 6 Caller Privacy Banner */}
      <div className="border-amber-500/20 bg-amber-500/5 mt-6 flex items-center gap-3 rounded-2xl border p-4 text-xs text-muted-foreground">
        <ShieldCheck className="size-5 text-amber-500 flex-shrink-0" />
        <div>
          <strong className="text-foreground">Privacy Protection Enforced:</strong> Caller passwords,
          OTPs, PINs, bank details, and full conversation transcripts are strictly excluded from
          storage and public dashboard display.
        </div>
      </div>

      {/* Call Details Modal */}
      {activeCall && (
        <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="border-border/60 bg-card text-foreground relative w-full max-w-lg rounded-2xl border p-6 shadow-2xl">
            <button
              onClick={() => setActiveCall(null)}
              className="text-muted-foreground hover:text-foreground absolute top-4 right-4 rounded-lg p-1 transition-colors"
            >
              <X className="size-5" />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <PhoneCall className="size-5 text-amber-500" />
              <h3 className="text-lg font-bold">Call Outcome Details</h3>
            </div>

            <div className="space-y-4 text-xs">
              <div className="border-border/40 grid grid-cols-2 gap-3 border-b pb-3">
                <div>
                  <span className="text-muted-foreground font-semibold">Call ID:</span>
                  <div className="font-mono text-foreground font-bold">{activeCall.call_id}</div>
                </div>
                <div>
                  <span className="text-muted-foreground font-semibold">Outcome:</span>
                  <div>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                        (activeCall.outcome || '').toUpperCase() === 'SUCCESS'
                          ? 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30 dark:text-emerald-400'
                          : 'bg-red-500/15 text-red-600 border-red-500/30 dark:text-red-400'
                      }`}
                    >
                      {activeCall.outcome}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-muted-foreground font-semibold">Shop / Seller:</span>
                  <div className="text-foreground font-bold">{activeCall.seller_id || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-muted-foreground font-semibold">Call Type:</span>
                  <div className="text-foreground font-bold">
                    {activeCall.outbound ? 'Outbound' : 'Inbound'}
                  </div>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground font-semibold">Outcome Details & Reason:</span>
                <div className="border-border/40 bg-muted/30 text-foreground mt-1 rounded-xl border p-3 font-medium">
                  {activeCall.reason || 'No additional details logged.'}
                </div>
              </div>

              <div className="border-border/40 grid grid-cols-2 gap-3 border-t pt-3 text-[11px] text-muted-foreground">
                <div>Duration: {formatDuration(activeCall.duration_seconds)}</div>
                <div>Time: {formatTimestamp(activeCall.started_at)}</div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setActiveCall(null)}
                className="rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:bg-amber-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
