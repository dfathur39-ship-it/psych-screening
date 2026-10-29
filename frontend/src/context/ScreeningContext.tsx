import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { getParticipant } from "../api/services";
import { getErrorMessage } from "../api/client";
import type { ParticipantProfile } from "../api/types";

/** "Login" for participants is their data diri: the participant id saved on this device.
 *  The profile (name, email, KTP status, screening state) is always re-read from the server. */
interface ScreeningState {
  participantId: string | null;
  sessionId: string | null;
  profile: ParticipantProfile | null;
  profileError: string | null;
  setParticipantId: (id: string | null) => void;
  setSessionId: (id: string | null) => void;
  refreshProfile: () => Promise<ParticipantProfile | null>;
  reset: () => void;
}

const STORAGE_KEY = "screening_progress_v1";

function loadSaved(): { participantId: string | null; sessionId: string | null } {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    return { participantId: parsed.participantId ?? null, sessionId: parsed.sessionId ?? null };
  } catch {
    return { participantId: null, sessionId: null }; // corrupted storage: start fresh
  }
}

const ScreeningContext = createContext<ScreeningState | undefined>(undefined);

export function ScreeningProvider({ children }: { children: ReactNode }) {
  // Read saved progress synchronously: pages redirect when ids are missing, so loading
  // them in an effect would bounce a refreshed page back to the start.
  const [saved] = useState(loadSaved);
  const [participantId, setParticipantId] = useState<string | null>(saved.participantId);
  const [sessionId, setSessionId] = useState<string | null>(saved.sessionId);
  const [profile, setProfile] = useState<ParticipantProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const currentId = useRef(participantId);
  currentId.current = participantId;

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ participantId, sessionId }));
  }, [participantId, sessionId]);

  const reset = useCallback(() => {
    setParticipantId(null);
    setSessionId(null);
    setProfile(null);
    setProfileError(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const refreshProfile = useCallback(async () => {
    const id = participantId;
    if (!id) return null;
    try {
      const fresh = await getParticipant(id);
      if (currentId.current !== id) return null; // participant changed while the request was in flight
      setProfile(fresh);
      setProfileError(null);
      return fresh;
    } catch (err) {
      if (currentId.current !== id) return null;
      if ((err as { response?: { status?: number } })?.response?.status === 404) {
        reset(); // the saved participant no longer exists: go back to filling in data diri
      } else {
        setProfileError(getErrorMessage(err));
      }
      return null;
    }
  }, [participantId, reset]);

  // Load the profile whenever the signed-in participant changes (including on first page load).
  useEffect(() => {
    setProfile(null);
    setProfileError(null);
    void refreshProfile();
  }, [refreshProfile]);

  return (
    <ScreeningContext.Provider
      value={{ participantId, sessionId, profile, profileError, setParticipantId, setSessionId, refreshProfile, reset }}
    >
      {children}
    </ScreeningContext.Provider>
  );
}

export function useScreening() {
  const ctx = useContext(ScreeningContext);
  if (!ctx) throw new Error("useScreening must be used within ScreeningProvider");
  return ctx;
}

/** For pages rendered inside MemberLayout, which only mounts them once the profile has loaded. */
export function useProfile(): ParticipantProfile {
  const { profile } = useScreening();
  if (!profile) throw new Error("useProfile must be used inside MemberLayout");
  return profile;
}
