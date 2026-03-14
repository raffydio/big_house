// ─────────────────────────────────────────
// src/pages/PaymentSuccess.tsx
// Pagina di ritorno dopo checkout completato
// ─────────────────────────────────────────
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const plan = params.get("plan") ?? "pro";

  const PLAN_LABELS: Record<string, string> = {
    basic: "Basic",
    pro:   "PRO",
    plus:  "PLUS",
  };

  useEffect(() => {
    const timer = setTimeout(() => navigate("/dashboard"), 5000);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "#1e293b",
          border: "1px solid rgba(34,197,94,0.3)",
          borderRadius: "20px",
          padding: "48px 40px",
          maxWidth: "440px",
          width: "100%",
          textAlign: "center",
          boxShadow: "0 0 60px rgba(34,197,94,0.1)",
        }}
      >
        <div style={{ fontSize: "56px", marginBottom: "20px" }}>🎉</div>
        <h1 style={{ color: "#f1f5f9", fontSize: "26px", fontWeight: 800, margin: "0 0 12px" }}>
          Benvenuto nel piano {PLAN_LABELS[plan] ?? plan}!
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "15px", margin: "0 0 8px" }}>
          Il tuo trial di 14 giorni è iniziato.
        </p>
        <p style={{ color: "#64748b", fontSize: "13px", margin: "0 0 32px" }}>
          Nessun addebito per i prossimi 14 giorni.
        </p>
        <div
          style={{
            background: "rgba(34,197,94,0.1)",
            border: "1px solid rgba(34,197,94,0.2)",
            borderRadius: "10px",
            padding: "12px",
            color: "#4ade80",
            fontSize: "13px",
            marginBottom: "28px",
          }}
        >
          ✓ Account aggiornato · ✓ Accesso completo attivo
        </div>
        <button
          onClick={() => navigate("/dashboard")}
          style={{
            background: "#3B82F6",
            color: "#fff",
            border: "none",
            borderRadius: "10px",
            padding: "14px 32px",
            fontSize: "15px",
            fontWeight: 700,
            cursor: "pointer",
            width: "100%",
          }}
        >
          Vai alla Dashboard →
        </button>
        <p style={{ color: "#475569", fontSize: "12px", marginTop: "16px" }}>
          Reindirizzamento automatico tra 5 secondi...
        </p>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────
// src/components/BillingStatusCard.tsx
// Card da mostrare nel Panoramica dashboard
// ─────────────────────────────────────────
import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

interface BillingStatus {
  plan: string;
  trial_ends_at: string | null;
  is_trialing: boolean;
  cancel_at_period: boolean | null;
  next_billing: string | null;
}

export function BillingStatusCard() {
  const [status, setStatus]   = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("bh_token");
    if (!token) { setLoading(false); return; }
    fetch(`${API_BASE}/billing/status`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(setStatus)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !status || status.plan === "free") return null;

  const trialEnd = status.trial_ends_at
    ? new Date(status.trial_ends_at).toLocaleDateString("it-IT")
    : null;

  const nextBill = status.next_billing
    ? new Date(status.next_billing).toLocaleDateString("it-IT")
    : null;

  return (
    <div
      style={{
        background: "rgba(59,130,246,0.06)",
        border: "1px solid rgba(59,130,246,0.2)",
        borderRadius: "12px",
        padding: "16px 20px",
        marginBottom: "20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ fontSize: "20px" }}>
          {status.plan === "plus" ? "⭐" : "💎"}
        </span>
        <div>
          <div style={{ color: "#f1f5f9", fontWeight: 700, fontSize: "14px" }}>
            Piano {status.plan.toUpperCase()}
            {status.is_trialing && (
              <span
                style={{
                  marginLeft: "8px",
                  background: "rgba(34,197,94,0.15)",
                  color: "#4ade80",
                  border: "1px solid rgba(34,197,94,0.3)",
                  borderRadius: "10px",
                  padding: "2px 8px",
                  fontSize: "11px",
                  fontWeight: 600,
                }}
              >
                TRIAL
              </span>
            )}
          </div>
          <div style={{ color: "#64748b", fontSize: "12px" }}>
            {status.is_trialing && trialEnd
              ? `Trial gratuito fino al ${trialEnd}`
              : nextBill
              ? `Prossimo rinnovo: ${nextBill}`
              : null}
            {status.cancel_at_period && (
              <span style={{ color: "#f87171", marginLeft: "8px" }}>
                · Cancellazione a fine periodo
              </span>
            )}
          </div>
        </div>
      </div>

      <a
        href="/pricing"
        style={{
          color: "#3B82F6",
          fontSize: "13px",
          fontWeight: 600,
          textDecoration: "none",
        }}
      >
        Gestisci →
      </a>
    </div>
  );
}
