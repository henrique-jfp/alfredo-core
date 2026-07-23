import { useState, useEffect, useCallback } from 'react';
import type { AlfredoState } from '../components/AlfredoOrb';

/**
 * Central hook for Alfredo's state machine.
 * Tracks the assistant's current state (idle/listening/thinking/speaking/executing/error).
 * Components can read the state and trigger transitions.
 */
export function useAlfredoState() {
  const [state, setState] = useState<AlfredoState>('idle');
  const [lastEvent, setLastEvent] = useState<{ type: string; timestamp: number } | null>(null);

  const transitionTo = useCallback((newState: AlfredoState) => {
    setState(newState);
    setLastEvent({ type: `state:${newState}`, timestamp: Date.now() });
  }, []);

  // Auto-reset from thinking/speaking to idle after timeout
  useEffect(() => {
    if (state === 'thinking') {
      const timer = setTimeout(() => {
        // If no speaking state arrived, go back to idle after 8s
        setState((prev) => prev === 'thinking' ? 'idle' : prev);
      }, 8000);
      return () => clearTimeout(timer);
    }
    if (state === 'speaking') {
      const timer = setTimeout(() => {
        setState('idle');
      }, 15000); // Max speaking duration before auto-idle
      return () => clearTimeout(timer);
    }
    if (state === 'executing') {
      const timer = setTimeout(() => {
        setState('idle');
      }, 5000);
      return () => clearTimeout(timer);
    }
    if (state === 'error') {
      const timer = setTimeout(() => {
        setState('idle');
      }, 6000);
      return () => clearTimeout(timer);
    }
  }, [state]);

  // Expose connection to WebMic states via window events
  useEffect(() => {
    const handleMicStart = () => transitionTo('listening');
    const handleMicStop = () => transitionTo('thinking');
    const handleMicResponse = () => transitionTo('speaking');
    const handleMicDone = () => transitionTo('idle');
    const handleMicError = () => transitionTo('error');

    window.addEventListener('alfredo:mic:start', handleMicStart);
    window.addEventListener('alfredo:mic:stop', handleMicStop);
    window.addEventListener('alfredo:mic:response', handleMicResponse);
    window.addEventListener('alfredo:mic:done', handleMicDone);
    window.addEventListener('alfredo:mic:error', handleMicError);

    return () => {
      window.removeEventListener('alfredo:mic:start', handleMicStart);
      window.removeEventListener('alfredo:mic:stop', handleMicStop);
      window.removeEventListener('alfredo:mic:response', handleMicResponse);
      window.removeEventListener('alfredo:mic:done', handleMicDone);
      window.removeEventListener('alfredo:mic:error', handleMicError);
    };
  }, [transitionTo]);

  return { state, lastEvent, transitionTo };
}
