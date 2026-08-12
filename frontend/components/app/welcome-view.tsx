'use client';

import React from 'react';
import { CircleNotch, Notebook, Package, ShoppingCart, Storefront } from '@phosphor-icons/react';
import { MicPermissionCard } from '@/components/app/mic-permission-card';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  isConnecting?: boolean;
  micError?: boolean;
  onStartCall: () => void;
  onRetryMic?: () => void;
}

export function WelcomeView({
  startButtonText,
  isConnecting = false,
  micError = false,
  onStartCall,
  onRetryMic,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) {
  if (micError) {
    return (
      <div ref={ref} className="flex min-h-svh items-center justify-center p-4">
        <MicPermissionCard onRetry={onRetryMic || onStartCall} />
      </div>
    );
  }

  return (
    <div ref={ref} className="flex min-h-svh flex-col items-center justify-between p-6 text-center">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center">
        {/* Priya Avatar Badge */}
        <div className="relative mb-6">
          <div className="flex size-20 items-center justify-center rounded-2xl border border-amber-500/30 bg-amber-500/15 text-amber-600 shadow-lg dark:text-amber-400">
            <Storefront size={44} weight="duotone" />
          </div>
          {/* <div className="ring-background absolute -right-1 -bottom-1 flex size-7 items-center justify-center rounded-full bg-amber-600 text-xs font-bold text-white ring-4">
            AI
          </div> */}
        </div>

        <h1 className="text-foreground text-2xl font-bold tracking-tight sm:text-3xl">
          Daily Bazaar
        </h1>
        <p className="text-muted-foreground mt-1 text-xs font-semibold tracking-wider uppercase">
          Voice Helper for Kirana & Small Shops
        </p>

        {/* Capability Chips */}
        <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
          <span className="bg-muted/60 text-muted-foreground border-border/40 inline-flex items-center gap-1 rounded-full border px-3 py-1 font-medium">
            <ShoppingCart size={14} className="text-amber-500" /> Record Orders
          </span>
          <span className="bg-muted/60 text-muted-foreground border-border/40 inline-flex items-center gap-1 rounded-full border px-3 py-1 font-medium">
            <Package size={14} className="text-amber-500" /> Update Stock
          </span>
          <span className="bg-muted/60 text-muted-foreground border-border/40 inline-flex items-center gap-1 rounded-full border px-3 py-1 font-medium">
            <Notebook size={14} className="text-amber-500" /> Manage Khata
          </span>
        </div>

        {/* State Display: Connecting vs Ready */}
        {isConnecting ? (
          <div className="mt-8 flex w-full flex-col items-center space-y-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-6 py-5">
            <CircleNotch size={32} className="animate-spin text-amber-500" weight="bold" />
            <div className="text-foreground text-sm font-semibold">Connecting to Priya...</div>
            <p className="text-muted-foreground text-xs">
              Please wait while we join your voice call.
            </p>
          </div>
        ) : (
          <div className="mt-8 flex w-full flex-col items-center">
            {/* Step 2 Requirement: One clear button to begin in Ready state */}
            <Button
              size="lg"
              onClick={onStartCall}
              className="min-h-[48px] w-full max-w-xs rounded-full bg-amber-600 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] hover:bg-amber-700"
            >
              {startButtonText}
            </Button>
            <p className="text-muted-foreground mt-3 text-xs">
              Tap above to speak with Priya in English, Hindi, or Hinglish
            </p>

            <a
              href="/escalations"
              className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-xs font-semibold text-amber-600 transition-all hover:bg-amber-500/20 dark:text-amber-400"
            >
              View Escalation Dashboard →
            </a>
          </div>
        )}
      </div>

      {/* Footer link */}
      <footer className="w-full py-2">
        <p className="text-muted-foreground text-xs leading-5">
          Powered by Murf Falcon TTS & LiveKit Voice AI
        </p>
      </footer>
    </div>
  );
}
