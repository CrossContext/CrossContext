/**
 * React Hook for managing user session state and verification.
 */

import { useState, useEffect } from "react";
import { defaultAuthClient, VerificationResult } from "../api/authClient";

export function useAuthSession(initialToken?: string) {
  const [session, setSession] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!initialToken) {
      setLoading(false);
      return;
    }

    defaultAuthClient.verifySessionToken(initialToken)
      .then((res) => {
        setSession(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [initialToken]);

  return { session, loading, error };
}
