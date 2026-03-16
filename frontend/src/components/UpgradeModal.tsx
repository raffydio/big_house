// src/components/UpgradeModal.tsx
// AGGIORNATO: PRO_BENEFITS allineati con security.py
//   10 Deep Research + 10 Calcola ROI (era 20+20)

import React, { useEffect } from 'react';
import type { Lang } from '../types';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onViewPlans: () => void;
  lang: Lang;
  feature?: 'deepresearch' | 'calcola';
}

const FEATURE_LABELS: Record<string, string> = {
  deepresearch: 'Deep Research',
  calcola: 'Calcola ROI',
};

const PRO_BENEFITS = [
  { icon: '⬡', text: '10 Deep Research al giorno' },    // ← era 20
  { icon: '◎', text: '10 Calcola ROI al giorno' },       // ← era 20
  { icon: '📄', text: 'Export report DOCX illimitati' },
  { icon: '🗂', text: 'Storico sessioni completo' },
  { icon: '☁️', text: 'Storage 2GB per i tuoi file' },
  { icon: '🤖', text: 'Gemini 2.5 Pro — massima qualità AI' }, // ← nuovo
];

export const UpgradeModal: React.FC<UpgradeModalProps> = ({
  isOpen,
  onClose,
  onViewPlans,
  lang,
  feature = 'deepresearch',
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!isOpen) return null;

  const featureLabel = FEATURE_LABELS[feature] ?? feature;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.2s ease',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'linear-gradient(145deg, #0f172a, #1e293b)',
          border: '1px solid rgba(59,130,246,0.25)',
          borderRadius: '20px',
          padding: '36px 32px',
          maxWidth: '460px',
          width: '100%',
          boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.1)',
          position: 'relative',
          animation: 'slideUp 0.25s ease',
        }}
      >
        <style>{`
          @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
          @keyframes slideUp { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
        `}</style>

        {/* Chiudi */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 16, right: 16,
            background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '50%', width: 32, height: 32,
            cursor: 'pointer', color: '#94a3b8', fontSize: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            lineHeight: 1,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.12)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
        >
          ×
        </button>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 56, height: 56, borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.2))',
            border: '1px solid rgba(59,130,246,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, margin: '0 auto 16px',
          }}>
            ⬡
          </div>
          <h2 style={{
            fontFamily: 'var(--font-display, Georgia, serif)',
            fontSize: '1.5rem', fontWeight: 700,
            color: '#f1f5f9', marginBottom: 8,
          }}>
            Hai raggiunto il limite
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5 }}>
            Hai esaurito le ricerche {featureLabel} del piano gratuito.<br />
            Passa a <strong style={{ color: '#3B82F6' }}>PRO</strong> per continuare.
          </p>
        </div>

        {/* Benefits */}
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: '12px',
          padding: '16px 20px',
          marginBottom: 24,
        }}>
          <p style={{
            color: '#94a3b8', fontSize: '0.75rem', fontWeight: 600,
            letterSpacing: '0.08em', marginBottom: 12, textTransform: 'uppercase',
          }}>
            Con il piano PRO ottieni:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {PRO_BENEFITS.map((b) => (
              <div key={b.text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                  background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
                }}>
                  {b.icon}
                </span>
                <span style={{ color: '#cbd5e1', fontSize: '0.88rem' }}>{b.text}</span>
                <span style={{ marginLeft: 'auto', color: '#22c55e', fontSize: 14, flexShrink: 0 }}>✓</span>
              </div>
            ))}
          </div>
        </div>

        {/* Prezzo */}
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <span style={{ color: '#64748b', fontSize: '0.85rem' }}>A partire da </span>
          <span style={{ color: '#f1f5f9', fontSize: '1.4rem', fontWeight: 800 }}>€29</span>
          <span style={{ color: '#64748b', fontSize: '0.85rem' }}>/mese</span>
          <span style={{
            marginLeft: 10, background: 'rgba(34,197,94,0.1)', color: '#22c55e',
            border: '1px solid rgba(34,197,94,0.3)',
            borderRadius: '999px', padding: '2px 10px', fontSize: '0.75rem', fontWeight: 700,
          }}>
            14 giorni gratis
          </span>
        </div>

        {/* CTA */}
        <button
          onClick={onViewPlans}
          style={{
            width: '100%', padding: '14px',
            background: 'linear-gradient(135deg, #3B82F6, #6366f1)',
            border: 'none', borderRadius: '10px',
            color: '#fff', fontSize: '1rem', fontWeight: 700,
            cursor: 'pointer', fontFamily: 'inherit',
            boxShadow: '0 4px 20px rgba(59,130,246,0.35)',
            marginBottom: 10,
          }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          Vedi tutti i piani →
        </button>

        <button
          onClick={onClose}
          style={{
            width: '100%', padding: '10px',
            background: 'transparent', border: 'none',
            color: '#475569', fontSize: '0.85rem', cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          Continua con il piano gratuito
        </button>
      </div>
    </div>
  );
};
