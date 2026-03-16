// src/pages/PricingPage.tsx
// AGGIORNATO: feature list allineata con security.py
//   PRO:  10 DR + 10 Calc (era 20+20)
//   PLUS: 20 DR + 50 Calc (era illimitato)
//   Aggiunto label modello AI per ogni piano

import { useState } from "react";
import type { View, User, Plan as PlanType } from "../types";
import CheckoutModal from "../components/CheckoutModal";

type PlanKey = "basic" | "pro" | "plus";

interface Plan {
  key: PlanKey;
  label: string;
  priceMonthly: number;
  priceAnnual: number;
  description: string;
  badge?: string;
  color: string;
  modelLabel: string;   // modello AI usato
  features: string[];
}

interface PricingPageProps {
  lang: string;
  user: User | null;
  onNavigate: (v: View) => void;
  onPlanUpgrade?: (plan: PlanType) => void;
}

const PLANS: Plan[] = [
  {
    key: "basic",
    label: "Basic",
    priceMonthly: 4.99,
    priceAnnual: 3.74,
    description: "Per chi vuole iniziare a esplorare con l'AI.",
    color: "#64748b",
    modelLabel: "Gemini 2.5 Flash",
    features: [
      "3 Deep Research al giorno",
      "3 Calcola ROI al giorno",
      "Export report DOCX",
      "Storage 500MB",
      "Storico sessioni",
      "Gemini 2.5 Flash AI",
      "Trial 14 giorni gratis",
    ],
  },
  {
    key: "pro",
    label: "PRO",
    priceMonthly: 29,
    priceAnnual: 21.75,
    description: "Per investitori attivi che analizzano più opportunità ogni giorno.",
    badge: "Più Scelto",
    color: "#3B82F6",
    modelLabel: "Gemini 2.5 Pro",
    features: [
      "10 Deep Research al giorno",   // ← era 20
      "10 Calcola ROI al giorno",      // ← era 20
      "Export report DOCX",
      "Storage 2GB",
      "Storico sessioni illimitato",
      "Gemini 2.5 Pro AI ⭐",          // ← modello superiore
      "Trial 14 giorni gratis",
    ],
  },
  {
    key: "plus",
    label: "PLUS",
    priceMonthly: 79,
    priceAnnual: 59.25,
    description: "Per professionisti e agenzie con portfolio complessi.",
    badge: "Pro Level",
    color: "#f59e0b",
    modelLabel: "Gemini 2.5 Pro",
    features: [
      "20 Deep Research al giorno",   // ← era illimitato
      "50 Calcola ROI al giorno",     // ← era illimitato
      "Export DOCX + Report PDF",
      "Storage 10GB",
      "Gemini 2.5 Pro AI ⭐",
      "Accesso prioritario nuovi modelli AI",
      "Supporto dedicato",
      "Trial 14 giorni gratis",
    ],
  },
];

const FREE_FEATURES = [
  "1 Deep Research al giorno",
  "1 Calcola ROI al giorno",
  "Gemini 2.5 Flash-Lite AI",
  "Nessun export",
  "Nessuno storage",
];

export default function PricingPage({ onNavigate, user }: PricingPageProps) {
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [cycle, setCycle] = useState<"monthly" | "annual">("monthly");
  const isLoggedIn = !!localStorage.getItem("bh_token");

  const handleSelectPlan = (plan: Plan) => {
    if (!isLoggedIn) {
      onNavigate("login");
      return;
    }
    setSelectedPlan(plan);
  };

  const handleCheckoutSuccess = () => {
    setSelectedPlan(null);
    onNavigate("payment-success");
  };

  const getPrice = (plan: Plan) =>
    cycle === "annual" ? plan.priceAnnual : plan.priceMonthly;

  const formatPrice = (n: number) =>
    n % 1 === 0 ? `€${n}` : `€${n.toFixed(2)}`;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        padding: "60px 20px",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "48px" }}>
        <div style={{
          display: "inline-block",
          background: "rgba(59,130,246,0.1)",
          border: "1px solid rgba(59,130,246,0.3)",
          borderRadius: "20px",
          padding: "6px 16px",
          color: "#3B82F6",
          fontSize: "13px",
          fontWeight: 600,
          marginBottom: "16px",
        }}>
          14 giorni gratis su tutti i piani
        </div>
        <h1 style={{
          fontSize: "clamp(28px, 5vw, 48px)",
          fontWeight: 800,
          color: "#f1f5f9",
          margin: "0 0 16px",
        }}>
          Scegli il tuo piano
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "16px", maxWidth: "520px", margin: "0 auto 32px" }}>
          Analisi immobiliari professionali con AI. Più alto il piano, più potente il modello AI.
        </p>

        {/* Toggle mensile/annuale */}
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "999px",
          padding: "4px",
        }}>
          {(["monthly", "annual"] as const).map((c) => (
            <button
              key={c}
              onClick={() => setCycle(c)}
              style={{
                padding: "8px 20px",
                borderRadius: "999px",
                border: "none",
                cursor: "pointer",
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: "14px",
                fontWeight: 600,
                transition: "all 0.2s",
                background: cycle === c ? "#3B82F6" : "transparent",
                color: cycle === c ? "#fff" : "#94a3b8",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {c === "monthly" ? "Mensile" : "Annuale"}
              {c === "annual" && (
                <span style={{
                  background: cycle === "annual" ? "rgba(255,255,255,0.2)" : "#f59e0b",
                  color: cycle === "annual" ? "#fff" : "#0f172a",
                  borderRadius: "999px",
                  padding: "1px 8px",
                  fontSize: "11px",
                  fontWeight: 800,
                }}>
                  -25%
                </span>
              )}
            </button>
          ))}
        </div>

        {cycle === "annual" && (
          <p style={{ color: "#22c55e", fontSize: "13px", marginTop: "10px" }}>
            ✓ Risparmi fino a €237/anno scegliendo il piano annuale
          </p>
        )}
      </div>

      {/* Cards */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "24px",
        justifyContent: "center",
        maxWidth: "1100px",
        margin: "0 auto 60px",
      }}>
        {PLANS.map((plan) => {
          const isPopular = plan.key === "pro";
          const price = getPrice(plan);

          return (
            <div
              key={plan.key}
              style={{
                background: isPopular ? "linear-gradient(145deg, #1e3a5f, #1e293b)" : "#1e293b",
                border: `1.5px solid ${isPopular ? plan.color : "rgba(255,255,255,0.07)"}`,
                borderRadius: "20px",
                padding: "32px 28px",
                width: "300px",
                position: "relative",
                boxShadow: isPopular ? `0 0 40px rgba(59,130,246,0.15)` : "0 4px 20px rgba(0,0,0,0.2)",
                transition: "transform 0.2s",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)"; }}
            >
              {plan.badge && (
                <div style={{
                  position: "absolute",
                  top: "-13px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: plan.color,
                  color: "#fff",
                  borderRadius: "20px",
                  padding: "4px 16px",
                  fontSize: "12px",
                  fontWeight: 700,
                  whiteSpace: "nowrap",
                }}>
                  ⭐ {plan.badge}
                </div>
              )}

              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ color: plan.color, fontWeight: 700, fontSize: "13px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    {plan.label}
                  </span>
                  {/* Badge modello AI */}
                  <span style={{
                    background: "rgba(255,255,255,0.07)",
                    color: "#94a3b8",
                    borderRadius: "6px",
                    padding: "2px 8px",
                    fontSize: "10px",
                    fontWeight: 600,
                  }}>
                    {plan.modelLabel}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "4px", margin: "8px 0 4px" }}>
                  <span style={{ fontSize: "40px", fontWeight: 800, color: "#f1f5f9" }}>
                    {formatPrice(price)}
                  </span>
                  <span style={{ color: "#64748b", fontSize: "14px" }}>/mese</span>
                </div>
                {cycle === "annual" && (
                  <p style={{ color: "#22c55e", fontSize: "12px", margin: "2px 0 6px" }}>
                    Fatturato {formatPrice(price * 12)}/anno
                  </p>
                )}
                <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>{plan.description}</p>
              </div>

              <button
                onClick={() => handleSelectPlan(plan)}
                style={{
                  width: "100%",
                  padding: "14px",
                  background: isPopular ? plan.color : "rgba(255,255,255,0.06)",
                  color: isPopular ? "#fff" : "#f1f5f9",
                  border: isPopular ? "none" : `1px solid rgba(255,255,255,0.12)`,
                  borderRadius: "10px",
                  fontSize: "15px",
                  fontWeight: 700,
                  cursor: "pointer",
                  marginBottom: "24px",
                  fontFamily: "Inter, system-ui, sans-serif",
                }}
              >
                Inizia 14 giorni gratis →
              </button>

              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {plan.features.map((f) => (
                  <li key={f} style={{ display: "flex", alignItems: "flex-start", gap: "10px", padding: "6px 0", color: "#cbd5e1", fontSize: "13.5px" }}>
                    <span style={{ color: "#22c55e", flexShrink: 0, marginTop: "1px" }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* Piano Free */}
      <div style={{
        maxWidth: "600px",
        margin: "0 auto 40px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "16px",
        padding: "24px 28px",
        textAlign: "center",
      }}>
        <p style={{ color: "#64748b", fontSize: "13px", margin: "0 0 12px", fontWeight: 600 }}>
          PIANO GRATUITO (sempre disponibile)
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px" }}>
          {FREE_FEATURES.map((f) => (
            <span key={f} style={{ color: "#475569", fontSize: "13px" }}>· {f}</span>
          ))}
        </div>
      </div>

      {/* Note */}
      <div style={{ maxWidth: "600px", margin: "0 auto", textAlign: "center" }}>
        <p style={{ color: "#64748b", fontSize: "13px" }}>
          ✅ Nessun addebito durante i 14 giorni di prova &nbsp;·&nbsp;
          ✅ Cancella in qualsiasi momento &nbsp;·&nbsp;
          ✅ Pagamento sicuro via Stripe
        </p>
      </div>

      {/* Checkout Modal */}
      {selectedPlan && (
        <CheckoutModal
          plan={selectedPlan.key}
          planLabel={selectedPlan.label}
          price={formatPrice(getPrice(selectedPlan))}
          onClose={() => setSelectedPlan(null)}
          onSuccess={handleCheckoutSuccess}
        />
      )}
    </div>
  );
}
