// src/components/CheckoutModal.tsx
// Stripe Embedded Checkout con Appearance API — colori Big House AI

import { useState, useCallback, useEffect } from "react";
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout,
} from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);
const API_BASE      = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const TOKEN_KEY     = "bh_token";

// ── Appearance API — Big House AI theme ──────────────────────
const appearance = {
  theme: "night" as const,
  variables: {
    colorPrimary:      "#3B82F6",   // blu Big House AI
    colorBackground:   "#1e293b",   // sfondo dashboard
    colorText:         "#f1f5f9",   // testo chiaro
    colorDanger:       "#ef4444",   // errori rosso
    colorSuccess:      "#22c55e",
    fontFamily:        "Inter, system-ui, sans-serif",
    fontSizeBase:      "15px",
    borderRadius:      "10px",
    spacingUnit:       "4px",
    focusBoxShadow:    "0 0 0 3px rgba(59,130,246,0.35)",
    buttonBorderRadius:"10px",
  },
};

interface CheckoutModalProps {
  plan: "basic" | "pro" | "plus";
  planLabel: string;
  price: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function CheckoutModal({
  plan,
  planLabel,
  price,
  onClose,
  onSuccess,
}: CheckoutModalProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [error, setError]               = useState<string | null>(null);
  const [loading, setLoading]           = useState(true);


  // Ottieni client_secret dal backend
  const fetchClientSecret = useCallback(async () => {
    setError(null);
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setError("Devi effettuare il login prima di procedere.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/billing/create-checkout-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data?.detail ?? "Errore avvio pagamento. Riprova.");
        setLoading(false);
        return;
      }

      setClientSecret(data.client_secret);
    } catch {
      setError("Errore di rete. Controlla la connessione.");
    } finally {
      setLoading(false);
    }
  }, [plan]);

  useEffect(() => {
    fetchClientSecret();
  }, [fetchClientSecret]);

  // Chiudi con ESC
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "#1e293b",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "520px",
          maxHeight: "90vh",
          overflow: "auto",
          boxShadow: "0 25px 60px rgba(0,0,0,0.5)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "24px 28px 0",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <span style={{ fontSize: "22px", fontWeight: 700, color: "#f1f5f9" }}>
                Piano {planLabel}
              </span>
              <span
                style={{
                  background: "rgba(59,130,246,0.15)",
                  color: "#3B82F6",
                  border: "1px solid rgba(59,130,246,0.3)",
                  borderRadius: "20px",
                  padding: "2px 10px",
                  fontSize: "12px",
                  fontWeight: 600,
                }}
              >
                14 giorni gratis
              </span>
            </div>
            <p style={{ color: "#94a3b8", margin: 0, fontSize: "14px" }}>
              {price}/mese · Carta richiesta, nessun addebito oggi
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "none",
              borderRadius: "8px",
              width: "32px",
              height: "32px",
              cursor: "pointer",
              color: "#94a3b8",
              fontSize: "18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            ×
          </button>
        </div>

        {/* Divider */}
        <div style={{ margin: "20px 0 0", height: "1px", background: "rgba(255,255,255,0.06)" }} />

        {/* Stripe Embedded Checkout */}
        <div style={{ padding: "0 4px 4px" }}>
          {loading && (
            <div
              style={{
                padding: "60px 20px",
                textAlign: "center",
                color: "#94a3b8",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  border: "3px solid rgba(59,130,246,0.3)",
                  borderTopColor: "#3B82F6",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                  margin: "0 auto 12px",
                }}
              />
              <style>{`@keyframes spin { to { transform: rotate(360deg); }}`}</style>
              Preparazione pagamento sicuro...
            </div>
          )}

          {error && (
            <div
              style={{
                margin: "20px 24px",
                padding: "14px 16px",
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: "10px",
                color: "#fca5a5",
                fontSize: "14px",
                textAlign: "center",
              }}
            >
              {error}
            </div>
          )}

          {clientSecret && !loading && (
            <EmbeddedCheckoutProvider
              stripe={stripePromise}
              options={{
                clientSecret,
                onComplete: () => {
                  onSuccess?.();
                  onClose();
                },
              }}
            >
              <EmbeddedCheckout />
            </EmbeddedCheckoutProvider>
          )}
        </div>

        {/* Footer sicurezza */}
        {!loading && !error && (
          <div
            style={{
              padding: "12px 24px 20px",
              textAlign: "center",
              color: "#475569",
              fontSize: "12px",
            }}
          >
            🔒 Pagamento sicuro via Stripe · Dati crittografati · Cancella in qualsiasi momento
          </div>
        )}
      </div>
    </div>
  );
}
