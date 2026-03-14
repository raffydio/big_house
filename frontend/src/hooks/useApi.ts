// ─────────────────────────────────────────
// src/hooks/useApi.ts
// ─────────────────────────────────────────

import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const TOKEN_KEY = 'bh_token';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApi<T, P> extends UseApiState<T> {
  call: (payload: P) => Promise<T | null>;
  reset: () => void;
}

/** Converte qualsiasi risposta di errore in stringa leggibile */
function parseError(data: unknown, status: number): string {
  // 422 Unprocessable Entity — Pydantic restituisce array di oggetti
  // [{type, loc, msg, input, ctx}, ...]
  if (status === 422) {
    if (Array.isArray(data)) {
      return data.map((e: any) => e?.msg ?? 'Errore di validazione').join(', ');
    }
    if (data && typeof data === 'object' && Array.isArray((data as any).detail)) {
      return (data as any).detail
        .map((e: any) => e?.msg ?? 'Errore di validazione')
        .join(', ');
    }
    return 'Dati non validi. Controlla i campi inseriti.';
  }

  // Errore standard con detail stringa
  if (data && typeof data === 'object') {
    const detail = (data as any).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((e: any) => e?.msg ?? String(e)).join(', ');
    }
  }

  return 'errorGeneral';
}

export function useApi<T, P = unknown>(endpoint: string): UseApi<T, P> {
  const [data, setData]       = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const call = useCallback(
    async (payload: P): Promise<T | null> => {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          if (res.status === 429) {
            setError('errorLimit');
          } else if (res.status === 401) {
            setError('errorAuth');
          } else {
            // parseError gestisce 422 e tutti gli altri casi
            setError(parseError(errData, res.status));
          }
          return null;
        }

        const result: T = await res.json();
        setData(result);
        return result;
      } catch {
        setError('errorNetwork');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [endpoint]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, call, reset };
}

/** Fetch autenticato GET generico */
export async function authGet<T>(path: string): Promise<T | null> {
  const token = localStorage.getItem(TOKEN_KEY);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/** Fetch autenticato POST per upgrade piano */
export async function upgradeUserPlan(plan: string): Promise<boolean> {
  const token = localStorage.getItem(TOKEN_KEY);
  try {
    const res = await fetch(`${API_BASE}/users/billing/upgrade`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ plan }),
    });
    return res.ok;
  } catch {
    return false;
  }
}