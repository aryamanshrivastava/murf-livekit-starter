'use client';

import React from 'react';
import { ArrowClockwise, LockKey, MicrophoneSlash } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface MicPermissionCardProps {
  onRetry: () => void;
}

export function MicPermissionCard({ onRetry }: MicPermissionCardProps) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center justify-center rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 text-center shadow-lg backdrop-blur-sm">
      <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-amber-500/20 text-amber-500">
        <MicrophoneSlash size={32} weight="bold" />
      </div>

      <h3 className="text-foreground text-xl font-bold">Microphone Access Blocked</h3>

      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Priya needs microphone access to listen to your orders and updates. Your browser is
        currently blocking access.
      </p>

      <div className="border-border bg-background/80 mt-4 w-full space-y-2 rounded-xl border p-4 text-left text-xs">
        <div className="text-foreground flex items-center gap-1.5 font-semibold">
          <LockKey size={16} className="text-amber-500" /> How to enable microphone:
        </div>
        <ol className="text-muted-foreground list-inside list-decimal space-y-1">
          <li>
            Click the <strong>lock / camera 🔒</strong> icon in your browser address bar.
          </li>
          <li>
            Change <strong>Microphone</strong> permission to <strong>Allow</strong>.
          </li>
          <li>Click the button below to try connecting again.</li>
        </ol>
      </div>

      <Button
        onClick={onRetry}
        size="lg"
        className="mt-5 min-h-[44px] w-full gap-2 rounded-full bg-amber-600 font-bold tracking-wider text-white uppercase hover:bg-amber-700"
      >
        <ArrowClockwise size={18} weight="bold" /> Try Connecting Again
      </Button>
    </div>
  );
}
