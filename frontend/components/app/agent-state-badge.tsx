'use client';

import React from 'react';
import { useAgent, useLocalParticipant } from '@livekit/components-react';
import { Brain, CircleNotch, Microphone, SpeakerHigh } from '@phosphor-icons/react';
import { cn } from '@/lib/shadcn/utils';

interface AgentStateBadgeProps {
  className?: string;
}

export function AgentStateBadge({ className }: AgentStateBadgeProps) {
  const { state: agentState } = useAgent();
  const { localParticipant } = useLocalParticipant();
  const isLocalSpeaking = localParticipant.isSpeaking;

  let stateLabel = 'Listening to you';
  let icon = <Microphone size={18} className="animate-pulse text-emerald-500" weight="fill" />;
  let badgeStyle = 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400';

  if (agentState === 'speaking') {
    stateLabel = 'Agent is speaking';
    icon = <SpeakerHigh size={18} className="animate-bounce text-amber-500" weight="fill" />;
    badgeStyle =
      'border-amber-500/40 bg-amber-500/15 text-amber-600 dark:text-amber-400 shadow-md shadow-amber-500/10';
  } else if (agentState === 'thinking') {
    stateLabel = 'Priya is thinking...';
    icon = <Brain size={18} className="animate-pulse text-purple-500" weight="fill" />;
    badgeStyle = 'border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400';
  } else if (agentState === 'connecting' || agentState === 'initializing') {
    stateLabel = 'Connecting...';
    icon = <CircleNotch size={18} className="animate-spin text-amber-500" weight="bold" />;
    badgeStyle = 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400';
  } else if (isLocalSpeaking || agentState === 'listening') {
    stateLabel = 'Listening to you';
    icon = <Microphone size={18} className="animate-pulse text-emerald-500" weight="fill" />;
    badgeStyle =
      'border-emerald-500/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 shadow-md shadow-emerald-500/10';
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-bold tracking-wide backdrop-blur-md transition-all duration-300',
        badgeStyle,
        className
      )}
    >
      {icon}
      <span>{stateLabel}</span>
    </div>
  );
}
