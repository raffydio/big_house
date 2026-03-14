// src/pages/PaymentSuccess.tsx
import { useEffect } from "react";
import type { View } from "../types";

interface Props {
  onNavigate: (v: View) => void;
}

export default function PaymentSuccess({ onNavigate }: Props) {
  // Legge il piano dall'URL se presente (?plan=pro)
  const params = new URLSearchParams(window.location.search);
  const plan = params.get("plan") ?? "pro";

  const PLAN_LABELS: Record<string, string> = {
    basic: "Basic",
    pro:   "PRO",
    plus:  "PLUS",
  };

  // Redirect automatico alla dashboard dopo 5 secondi
  useEffect(() => {
    const timer = setTimeout(() => onNavigate("dashboard"), 5000);
    return () => clearTimeout(timer);
  }, [onNavigate]);

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
        <h1
          style={{
            color: "#f1f5f9",
            fontSize: "26px",
            fontWeight: 800,
            margin: "0 0 12px",
          }}
        >
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
          ✓ Account aggiornato &nbsp;·&nbsp; ✓ Accesso completo attivo
        </div>

        <button
          onClick={() => onNavigate("dashboard")}
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