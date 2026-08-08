'use client';

import React from 'react';
import { ArrowClockwise, CheckCircle, PhoneDisconnect } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface CallEndedViewProps {
  onStartAgain: () => void;
}

export function CallEndedView({ onStartAgain }: CallEndedViewProps) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center justify-center px-4 py-8 text-center">
      <div className="mb-4 flex size-16 items-center justify-center rounded-full bg-rose-500/10 text-rose-500">
        <PhoneDisconnect size={36} weight="bold" />
      </div>

      <div className="bg-muted text-muted-foreground mb-2 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold">
        <CheckCircle size={14} className="text-emerald-500" weight="fill" />
        Session Completed
      </div>

      <h2 className="text-foreground text-2xl font-bold tracking-tight">Call Ended</h2>

      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Your voice session with <strong>Priya (Daily Bazaar)</strong> has ended. All your recorded
        orders and updates have been saved.
      </p>

      <div className="border-border/60 bg-muted/30 mt-6 w-full space-y-2 rounded-xl border p-4 text-left text-xs">
        <span className="text-foreground font-semibold">Need more help?</span>
        <p className="text-muted-foreground">
          You can start a new voice session anytime to record customer orders, update stock levels,
          or check khata balances.
        </p>
      </div>

      <Button
        onClick={onStartAgain}
        size="lg"
        className="mt-6 min-h-[48px] w-full max-w-xs gap-2 rounded-full bg-amber-600 font-bold tracking-wider text-white uppercase shadow-md hover:bg-amber-700"
      >
        <ArrowClockwise size={20} weight="bold" /> Start Again
      </Button>
    </div>
  );
}
