/**
 * React Custom Hook for User Authentication State.
 * Consumes AuthClient from services layer.
 */

import { useState, useEffect } from "react";
import { defaultAuthClient } from "../services/authClient";

export interface AuthState {
  isAuthenticated: boolean;
  userId: string | null;
  loading: boolean;
  error: string | null;
}

export function useAuth(token?: string) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    userId: null,
    loading: !!token,
    error: null,
  });

  useEffect(() => {
    if (!token) return;

    defaultAuthClient
      .verifyUserSession(token)
      .then((res) => {
        setState({
          isAuthenticated: res.valid,
          userId: res.user_id,
          loading: false,
          error: null,
        });
      })
      .catch((err) => {
        setState({
          isAuthenticated: false,
          userId: null,
          loading: false,
          error: err.message,
        });
      });
  }, [token]);

  return state;
}
