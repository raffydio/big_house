// src/components/PlanBadge.tsx
// FIX: aggiunto 'basic' in PLAN_STYLES (mancava → crash runtime)

import React from 'react';
import type { Plan } from '../types';

interface PlanBadgeProps {
  plan: Plan;
  size?: 'sm' | 'md';
}

const PLAN_STYLES: Record<Plan, { bg: string; color: string; label: string }> = {
  free:  { bg: 'rgba(148,163,184,.15)', color: 'var(--text-secondary)', label: 'FREE'  },
  basic: { bg: 'rgba(100,116,139,.12)', color: '#64748b',               label: 'BASIC' }, // ← AGGIUNTO
  pro:   { bg: 'rgba(37,99,235,.12)',   color: 'var(--c-blue)',          label: 'PRO'   },
  plus:  { bg: 'rgba(201,168,76,.15)',  color: 'var(--c-gold)',          label: 'PLUS'  },
};

export const PlanBadge: React.FC<PlanBadgeProps> = ({ plan, size = 'md' }) => {
  // Fallback sicuro se arriva un valore inatteso
  const s = PLAN_STYLES[plan] ?? PLAN_STYLES['free'];

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: size === 'sm' ? '2px 8px' : '4px 12px',
      background: s.bg,
      color: s.color,
      borderRadius: 'var(--r-full)',
      fontSize: size === 'sm' ? '0.65rem' : '0.72rem',
      fontWeight: 700,
      letterSpacing: '0.08em',
      fontFamily: 'var(--font-body)',
    }}>
      {s.label}
    </span>
  );
};