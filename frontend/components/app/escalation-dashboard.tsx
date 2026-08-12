'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Clock, Filter, RefreshCw, Search, Users, X } from 'lucide-react';

export interface EscalationTicket {
  escalation_id: string;
  seller_id: string;
  seller_name: string;
  contact_phone?: string | null;
  category: string;
  issue_summary: string;
  agent_findings?: string;
  urgency_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  language?: string;
  contact_method?: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | string;
  created_at: string;
  assigned_to?: string;
}

interface EscalationDashboardProps {
  onBackToAgent?: () => void;
}

export function EscalationDashboard({ onBackToAgent }: EscalationDashboardProps) {
  const [tickets, setTickets] = useState<EscalationTicket[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedUrgency, setSelectedUrgency] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  // Detail Modal
  const [activeTicket, setActiveTicket] = useState<EscalationTicket | null>(null);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/escalations', { cache: 'no-store' });
      const data = await res.json();
      if (data.success && Array.isArray(data.escalations)) {
        setTickets(data.escalations);
      } else {
        setTickets([]);
      }
    } catch (err) {
      console.error('Error loading escalations:', err);
      setError('Unable to load escalation tickets. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  // Derived Metrics
  const openCount = tickets.filter((t) => (t.status || 'OPEN').toUpperCase() === 'OPEN').length;
  const inProgressCount = tickets.filter(
    (t) => (t.status || '').toUpperCase() === 'IN_PROGRESS'
  ).length;
  const resolvedCount = tickets.filter((t) => (t.status || '').toUpperCase() === 'RESOLVED').length;
  const criticalOpenCount = tickets.filter(
    (t) =>
      (t.urgency_level || '').toUpperCase() === 'CRITICAL' &&
      (t.status || 'OPEN').toUpperCase() === 'OPEN'
  ).length;

  // Filter Logic
  const filteredTickets = tickets.filter((ticket) => {
    const statusMatch =
      selectedStatus === 'ALL' || (ticket.status || 'OPEN').toUpperCase() === selectedStatus;

    const urgencyMatch =
      selectedUrgency === 'ALL' ||
      (ticket.urgency_level || 'MEDIUM').toUpperCase() === selectedUrgency;

    const categoryMatch =
      selectedCategory === 'ALL' ||
      (ticket.category || '').toLowerCase().includes(selectedCategory.toLowerCase());

    const searchLower = searchQuery.toLowerCase().trim();
    const searchMatch =
      !searchLower ||
      ticket.escalation_id.toLowerCase().includes(searchLower) ||
      (ticket.seller_name || '').toLowerCase().includes(searchLower) ||
      (ticket.category || '').toLowerCase().includes(searchLower) ||
      (ticket.issue_summary || '').toLowerCase().includes(searchLower);

    return statusMatch && urgencyMatch && categoryMatch && searchMatch;
  });

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

  const getUrgencyBadge = (urgency: string) => {
    const val = (urgency || 'MEDIUM').toUpperCase();
    switch (val) {
      case 'CRITICAL':
        return 'bg-red-500/15 text-red-600 border-red-500/30 dark:text-red-400';
      case 'HIGH':
        return 'bg-amber-500/15 text-amber-600 border-amber-500/30 dark:text-amber-400';
      case 'MEDIUM':
        return 'bg-blue-500/15 text-blue-600 border-blue-500/30 dark:text-blue-400';
      default:
        return 'bg-zinc-500/15 text-zinc-600 border-zinc-500/30 dark:text-zinc-400';
    }
  };

  const getStatusBadge = (status: string) => {
    const val = (status || 'OPEN').toUpperCase();
    switch (val) {
      case 'OPEN':
        return 'bg-amber-500/15 text-amber-600 border-amber-500/30 dark:text-amber-400';
      case 'IN_PROGRESS':
        return 'bg-blue-500/15 text-blue-600 border-blue-500/30 dark:text-blue-400';
      case 'RESOLVED':
        return 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30 dark:text-emerald-400';
      default:
        return 'bg-zinc-500/15 text-zinc-600 border-zinc-500/30 dark:text-zinc-400';
    }
  };

  return (
    <div className="bg-background text-foreground flex min-h-svh w-full flex-col p-4 sm:p-6 lg:p-8">
      {/* Header with Refresh Button */}
      <div className="border-border/40 mb-6 flex flex-col gap-4 border-b pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Escalation Dashboard</h1>
            <span className="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
              Live Support Tickets
            </span>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Monitor and resolve escalated local commerce seller disputes, payment issues, and bulk
            terms.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onBackToAgent && (
            <button
              onClick={onBackToAgent}
              className="border-border/60 bg-muted/40 text-foreground hover:bg-muted inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-all"
            >
              ← Return to Agent
            </button>
          )}

          <button
            onClick={fetchTickets}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-amber-600/20 transition-all hover:scale-[1.02] hover:bg-amber-700 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {/* Open */}
        <div className="flex flex-col justify-between rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-amber-600 dark:text-amber-400">
            <span className="text-xs font-semibold tracking-wider uppercase">Open</span>
            <AlertCircle className="size-5" />
          </div>
          <div className="text-foreground mt-3 text-3xl font-extrabold">{openCount}</div>
          <div className="text-muted-foreground mt-1 text-[11px]">Awaiting resolution</div>
        </div>

        {/* In Progress */}
        <div className="flex flex-col justify-between rounded-2xl border border-blue-500/20 bg-blue-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-blue-600 dark:text-blue-400">
            <span className="text-xs font-semibold tracking-wider uppercase">In Progress</span>
            <Clock className="size-5" />
          </div>
          <div className="text-foreground mt-3 text-3xl font-extrabold">{inProgressCount}</div>
          <div className="text-muted-foreground mt-1 text-[11px]">Under support review</div>
        </div>

        {/* Resolved */}
        <div className="flex flex-col justify-between rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-emerald-600 dark:text-emerald-400">
            <span className="text-xs font-semibold tracking-wider uppercase">Resolved</span>
            <CheckCircle className="size-5" />
          </div>
          <div className="text-foreground mt-3 text-3xl font-extrabold">{resolvedCount}</div>
          <div className="text-muted-foreground mt-1 text-[11px]">Completed & closed</div>
        </div>

        {/* Critical Open */}
        <div className="flex flex-col justify-between rounded-2xl border border-red-500/20 bg-red-500/5 p-4 shadow-sm">
          <div className="flex items-center justify-between text-red-600 dark:text-red-400">
            <span className="text-xs font-semibold tracking-wider uppercase">Critical Open</span>
            <Users className="size-5 animate-pulse" />
          </div>
          <div className="mt-3 text-3xl font-extrabold text-red-600 dark:text-red-400">
            {criticalOpenCount}
          </div>
          <div className="text-muted-foreground mt-1 text-[11px]">High-priority escalation</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="border-border/60 bg-muted/20 mb-6 flex flex-col gap-3 rounded-2xl border p-3.5 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by Ref ID, Caller, Type or Summary..."
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

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-background text-foreground border-border/60 rounded-xl border px-3 py-2 text-xs font-medium focus:border-amber-500 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          {/* Urgency Filter */}
          <select
            value={selectedUrgency}
            onChange={(e) => setSelectedUrgency(e.target.value)}
            className="bg-background text-foreground border-border/60 rounded-xl border px-3 py-2 text-xs font-medium focus:border-amber-500 focus:outline-none"
          >
            <option value="ALL">All Urgencies</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-background text-foreground border-border/60 rounded-xl border px-3 py-2 text-xs font-medium focus:border-amber-500 focus:outline-none"
          >
            <option value="ALL">All Types</option>
            <option value="payment">Payment Dispute</option>
            <option value="refund">Refund Issue</option>
            <option value="wholesale">Wholesale Bulk Terms</option>
            <option value="order">Order Dispute</option>
          </select>

          {(searchQuery ||
            selectedStatus !== 'ALL' ||
            selectedUrgency !== 'ALL' ||
            selectedCategory !== 'ALL') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedStatus('ALL');
                setSelectedUrgency('ALL');
                setSelectedCategory('ALL');
              }}
              className="text-muted-foreground hover:text-foreground text-xs font-medium underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Table Container */}
      <div className="border-border/60 bg-background flex flex-1 flex-col overflow-hidden rounded-2xl border shadow-sm">
        {error && (
          <div className="border-b border-red-500/20 bg-red-500/10 p-4 text-xs font-medium text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 border-border/50 text-muted-foreground border-b font-semibold tracking-wider uppercase">
              <tr>
                <th className="px-4 py-3.5">ReferenceId</th>
                <th className="px-4 py-3.5">Type</th>
                <th className="px-4 py-3.5">Urgency</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-4 py-3.5">Caller</th>
                <th className="px-4 py-3.5">Created Time</th>
                <th className="px-4 py-3.5">Assigned</th>
              </tr>
            </thead>
            <tbody className="divide-border/30 divide-y">
              {filteredTickets.length > 0 ? (
                filteredTickets.map((ticket) => (
                  <tr
                    key={ticket.escalation_id}
                    onClick={() => setActiveTicket(ticket)}
                    className="group cursor-pointer transition-colors hover:bg-amber-500/5"
                  >
                    {/* ReferenceId */}
                    <td className="text-foreground px-4 py-3.5 font-mono font-bold">
                      <span className="bg-muted border-border/40 rounded-md border px-2 py-1 group-hover:border-amber-500/30">
                        {ticket.escalation_id}
                      </span>
                    </td>

                    {/* Type / Category */}
                    <td className="text-foreground px-4 py-3.5 font-medium">
                      {ticket.category || 'General Escalation'}
                    </td>

                    {/* Urgency */}
                    <td className="px-4 py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase ${getUrgencyBadge(
                          ticket.urgency_level
                        )}`}
                      >
                        {ticket.urgency_level || 'MEDIUM'}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase ${getStatusBadge(
                          ticket.status
                        )}`}
                      >
                        {ticket.status || 'OPEN'}
                      </span>
                    </td>

                    {/* Caller / Seller */}
                    <td className="text-foreground px-4 py-3.5 font-semibold">
                      {ticket.seller_name || ticket.seller_id}
                      {ticket.contact_phone && (
                        <div className="text-muted-foreground text-[10px] font-normal">
                          {ticket.contact_phone}
                        </div>
                      )}
                    </td>

                    {/* Created Time */}
                    <td className="text-muted-foreground px-4 py-3.5 font-medium">
                      {formatTimestamp(ticket.created_at)}
                    </td>

                    {/* Assigned */}
                    <td className="text-muted-foreground px-4 py-3.5 font-medium">
                      {ticket.assigned_to || 'Support Ops'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="text-muted-foreground px-4 py-12 text-center">
                    {loading ? (
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="size-4 animate-spin text-amber-500" />
                        Loading escalation tickets...
                      </div>
                    ) : (
                      <div>
                        <div className="text-foreground text-sm font-semibold">
                          No escalation tickets found
                        </div>
                        <p className="mt-1 text-xs">
                          {searchQuery ||
                          selectedStatus !== 'ALL' ||
                          selectedUrgency !== 'ALL' ||
                          selectedCategory !== 'ALL'
                            ? 'Try resetting your filter options.'
                            : 'When Priya escalates a seller dispute, tickets will appear here.'}
                        </p>
                      </div>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ticket Details Modal */}
      {activeTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="bg-popover text-popover-foreground border-border/80 animate-in fade-in zoom-in-95 w-full max-w-lg rounded-2xl border p-6 shadow-2xl">
            <div className="border-border/40 flex items-center justify-between border-b pb-4">
              <div>
                <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400">
                  {activeTicket.escalation_id}
                </span>
                <h3 className="text-foreground text-lg font-bold">{activeTicket.category}</h3>
              </div>
              <button
                onClick={() => setActiveTicket(null)}
                className="text-muted-foreground hover:text-foreground rounded-full p-1 transition-colors"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-muted-foreground font-semibold">Caller / Shop:</span>
                  <div className="text-foreground font-bold">{activeTicket.seller_name}</div>
                </div>
                <div>
                  <span className="text-muted-foreground font-semibold">Urgency:</span>
                  <div>
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold ${getUrgencyBadge(
                        activeTicket.urgency_level
                      )}`}
                    >
                      {activeTicket.urgency_level}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground font-semibold">Issue Summary:</span>
                <div className="border-border/40 bg-muted/30 text-foreground mt-1 rounded-xl border p-3 font-medium">
                  {activeTicket.issue_summary}
                </div>
              </div>

              {activeTicket.agent_findings && (
                <div>
                  <span className="text-muted-foreground font-semibold">Agent Findings:</span>
                  <div className="border-border/40 bg-muted/30 text-foreground mt-1 rounded-xl border p-3 font-medium">
                    {activeTicket.agent_findings}
                  </div>
                </div>
              )}

              <div className="text-muted-foreground border-border/40 grid grid-cols-2 gap-3 border-t pt-2 text-[11px]">
                <div>Created: {formatTimestamp(activeTicket.created_at)}</div>
                <div>Preferred Contact: {activeTicket.contact_method || 'Phone'}</div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setActiveTicket(null)}
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
