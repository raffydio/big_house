// src/components/AgentThinking.tsx
// Mostra lo stato "sto pensando" degli agenti AI con animazione
// Appare durante l'elaborazione di Deep Research o Calcola

import React, { useEffect, useState } from 'react';
import type { ChatFeature } from '../types';

interface AgentThinkingProps {
  feature: ChatFeature;
  visible: boolean;
}

// Steps simulati per ogni feature
const DR_STEPS = [
  { agent: 'Property Finder',      icon: '🔍', label: 'Analisi strutturale proprietà...' },
  { agent: 'Market Analyzer',      icon: '📊', label: 'Raccolta dati di mercato...' },
  { agent: 'Renovation Expert',    icon: '🏗️', label: 'Stima costi ristrutturazione...' },
  { agent: 'Investment Advisor',   icon: '💡', label: 'Elaborazione raccomandazioni...' },
];

const CALC_STEPS = [
  { agent: 'Cost Estimator',   icon: '🧮', label: 'Calcolo costi per scenario...' },
  { agent: 'Timeline Planner', icon: '📅', label: 'Pianificazione timeline lavori...' },
  { agent: 'Risk Analyst',     icon: '⚖️', label: 'Analisi rischi e ROI...' },
];

export const AgentThinking: React.FC<AgentThinkingProps> = ({ feature, visible }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const steps = feature === 'deepresearch' ? DR_STEPS : CALC_STEPS;

  useEffect(() => {
    if (!visible) {
      setActiveStep(0);
      setCompletedSteps([]);
      return;
    }

    // Avanza step ogni ~8s (simulazione; il backend può metterne di più)
    const interval = setInterval(() => {
      setActiveStep((prev) => {
        if (prev < steps.length - 1) {
          setCompletedSteps((c) => [...c, prev]);
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 7000);

    return () => clearInterval(interval);
  }, [visible, steps.length]);

  if (!visible) return null;

  return (
    <div style={{
      background: 'var(--bg-white)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--r-lg)',
      padding: 24,
      animation: 'fadeIn .4s ease both',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 20,
      }}>
        <div style={{
          display: 'flex',
          gap: 4,
          alignItems: 'center',
        }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{
              width: 7, height: 7,
              borderRadius: '50%',
              background: 'var(--c-blue)',
              animation: `thinking 1.4s ${i * 0.16}s infinite ease-in-out`,
            }} />
          ))}
        </div>
        <span style={{
          fontSize: '0.88rem',
          fontWeight: 600,
          color: 'var(--c-blue)',
        }}>
          {feature === 'deepresearch'
            ? 'Agenti AI al lavoro...'
            : 'Calcolo scenari in corso...'}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
        }}>
          Potrebbe richiedere 30–90 secondi
        </span>
      </div>

      {/* Agent steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {steps.map((step, i) => {
          const isDone    = completedSteps.includes(i);
          const isActive  = activeStep === i;
          const isPending = i > activeStep;

          return (
            <div key={step.agent} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '10px 14px',
              background: isDone
                ? 'rgba(16,185,129,.06)'
                : isActive
                  ? 'rgba(37,99,235,.06)'
                  : 'var(--bg-muted)',
              borderRadius: 'var(--r-md)',
              border: `1px solid ${isDone ? 'rgba(16,185,129,.2)' : isActive ? 'rgba(37,99,235,.15)' : 'transparent'}`,
              transition: 'all var(--dur-base) var(--ease)',
              opacity: isPending ? 0.4 : 1,
            }}>
              {/* Icon / Stato */}
              <div style={{
                width: 32, height: 32,
                borderRadius: '50%',
                background: isDone
                  ? 'rgba(16,185,129,.15)'
                  : isActive
                    ? 'rgba(37,99,235,.12)'
                    : 'rgba(148,163,184,.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 15,
                flexShrink: 0,
              }}>
                {isDone ? '✓' : step.icon}
              </div>

              {/* Text */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: isDone ? 'var(--c-green)' : isActive ? 'var(--c-blue)' : 'var(--text-muted)',
                  letterSpacing: '.03em',
                }}>
                  {step.agent}
                </div>
                {isActive && (
                  <div style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    marginTop: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}>
                    <span className="spinner spinner--dark" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
                    {step.label}
                  </div>
                )}
                {isDone && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--c-green)', marginTop: 2 }}>
                    Completato
                  </div>
                )}
              </div>

              {/* Timer badge attivo */}
              {isActive && (
                <div style={{
                  padding: '3px 8px',
                  background: 'rgba(37,99,235,.1)',
                  borderRadius: 'var(--r-full)',
                  fontSize: '0.7rem',
                  color: 'var(--c-blue)',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}>
                  in corso
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <p style={{
        marginTop: 16,
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
        textAlign: 'center',
        lineHeight: 1.5,
      }}>
        Gli agenti AI stanno analizzando i dati in modo sequenziale. Non chiudere la finestra.
      </p>
    </div>
  );
};
