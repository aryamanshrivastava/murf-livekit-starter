'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { ConnectionState } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { CallEndedView } from '@/components/app/call-ended-view';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);
const MotionCallEndedView = motion.create(CallEndedView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden' as const,
  animate: 'visible' as const,
  exit: 'hidden' as const,
  transition: {
    duration: 0.4,
    ease: 'easeInOut' as const,
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const session = useSessionContext();
  const isConnected = session.isConnected;
  const isConnecting = session.connectionState === ConnectionState.Connecting;
  const start = session.start;
  const { resolvedTheme } = useTheme();

  const [hasEnded, setHasEnded] = useState(false);
  const [micError, setMicError] = useState(false);
  const wasConnectedRef = useRef(false);

  // Track state transitions to detect when call finishes
  useEffect(() => {
    if (isConnected) {
      wasConnectedRef.current = true;
      setHasEnded(false);
    } else if (wasConnectedRef.current && !isConnecting) {
      wasConnectedRef.current = false;
      setHasEnded(true);
    }
  }, [isConnected, isConnecting]);

  const handleStartCall = useCallback(async () => {
    setHasEnded(false);
    setMicError(false);

    try {
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        // Trigger browser microphone permission popup
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
      }
      await start();
    } catch (err: unknown) {
      const errObj = err as { name?: string; message?: string };
      if (
        errObj?.name === 'NotAllowedError' ||
        errObj?.name === 'PermissionDeniedError' ||
        errObj?.message?.toLowerCase().includes('denied') ||
        errObj?.message?.toLowerCase().includes('permission') ||
        errObj?.message?.toLowerCase().includes('not allowed')
      ) {
        setMicError(true);
      }
    }
  }, [start]);

  const handleResetToReady = useCallback(() => {
    setHasEnded(false);
    setMicError(false);
  }, []);

  return (
    <AnimatePresence mode="wait">
      {/* 1. Call Ended State */}
      {!isConnected && !isConnecting && hasEnded && (
        <MotionCallEndedView
          key="call-ended"
          {...VIEW_MOTION_PROPS}
          onStartAgain={handleResetToReady}
        />
      )}

      {/* 2. Ready / Connecting / Mic Error States */}
      {!isConnected && (!hasEnded || isConnecting || micError) && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          isConnecting={isConnecting}
          micError={micError}
          onStartCall={handleStartCall}
          onRetryMic={handleStartCall}
        />
      )}

      {/* 3. Session View (Listening & Speaking States) */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          className="fixed inset-0"
        />
      )}
    </AnimatePresence>
  );
}
