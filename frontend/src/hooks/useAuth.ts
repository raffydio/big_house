// ─────────────────────────────────────────
// src/hooks/useAuth.ts
// ─────────────────────────────────────────

import { useState, useCallback } from 'react';
import type { User, AuthResponse, RegisterPayload, LoginPayload } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const TOKEN_KEY = 'bh_token';

export interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface UseAuth extends AuthState {
  login: (payload: LoginPayload) => Promise<boolean>;
  loginWithGoogle: (credential: string) => Promise<boolean>;
  register: (payload: RegisterPayload) => Promise<boolean>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  clearError: () => void;
}

export function useAuth(): UseAuth {
  const [user, setUser]     = useState<User | null>(null);
  const [token, setToken]   = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  // ── Helper interno: salva token e carica profilo ──
  const _handleToken = useCallback(async (accessToken: string): Promise<boolean> => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
    try {
      const res = await fetch(`${API_BASE}/users/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        setUser(await res.json());
        return true;
      }
    } catch { /* silent */ }
    return false;
  }, []);

  // ── Fetch profilo utente ──
  const fetchUser = useCallback(async () => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    try {
      const res = await fetch(`${API_BASE}/users/me`, {
        headers: { Authorization: `Bearer ${stored}` },
      });
      if (!res.ok) {
        if (res.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        }
        return;
      }
      setUser(await res.json());
    } catch { /* silent */ }
  }, []);

  // ── Login email/password ──
  const login = useCallback(async (payload: LoginPayload): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const form = new URLSearchParams();
      form.append('username', payload.email);
      form.append('password', payload.password);

      const res = await fetch(`${API_BASE}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail ?? 'errorAuth');
        return false;
      }

      const data: AuthResponse = await res.json();
      return await _handleToken(data.access_token);
    } catch {
      setError('errorNetwork');
      return false;
    } finally {
      setLoading(false);
    }
  }, [_handleToken]);

  // ── Login con Google ──
  const loginWithGoogle = useCallback(async (credential: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail ?? 'errorAuth');
        return false;
      }

      const data: AuthResponse = await res.json();
      return await _handleToken(data.access_token);
    } catch {
      setError('errorNetwork');
      return false;
    } finally {
      setLoading(false);
    }
  }, [_handleToken]);

  // ── Register ──
  const register = useCallback(async (payload: RegisterPayload): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail ?? 'errorGeneral');
        return false;
      }

      // Auto-login dopo registrazione
      return await login({ email: payload.email, password: payload.password });
    } catch {
      setError('errorNetwork');
      return false;
    } finally {
      setLoading(false);
    }
  }, [login]);

  // ── Logout ──
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  return {
    user, token, loading, error,
    login, loginWithGoogle, register,
    logout, fetchUser, clearError,
  };
}
