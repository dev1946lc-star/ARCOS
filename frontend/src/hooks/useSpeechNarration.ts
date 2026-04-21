"use client";

import { useEffect, useRef } from "react";

import type { DashboardEvent } from "@/hooks/useNormalizedEvents";

export function useSpeechNarration(enabled: boolean, events: DashboardEvent[]) {
  const spokenIdsRef = useRef<Set<string>>(new Set());
  const pendingIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!("speechSynthesis" in window)) return;

    if (!enabled) {
      window.speechSynthesis.cancel();
      return;
    }

    const nextEvent = [...events]
      .reverse()
      .find(
        (event) =>
          event.speakable &&
          !spokenIdsRef.current.has(event.id) &&
          !pendingIdsRef.current.has(event.id)
      );

    if (!nextEvent) return;
    pendingIdsRef.current.add(nextEvent.id);

    const utterance = new SpeechSynthesisUtterance(nextEvent.message);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onend = () => {
      pendingIdsRef.current.delete(nextEvent.id);
      spokenIdsRef.current.add(nextEvent.id);
    };
    utterance.onerror = () => {
      pendingIdsRef.current.delete(nextEvent.id);
      spokenIdsRef.current.add(nextEvent.id);
    };

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
    }

    window.speechSynthesis.speak(utterance);

    return () => {
      utterance.onend = null;
      utterance.onerror = null;
    };
  }, [enabled, events]);

  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);
}
