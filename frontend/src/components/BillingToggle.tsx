// src/components/BillingToggle.tsx
// Toggle mensile/annuale con badge sconto 25%

import React from 'react';
import type { BillingCycle } from '../types';

interface BillingToggleProps {
  cycle: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
}

export const BillingToggle: React.FC<BillingToggleProps> = ({ cycle, onChange }) => {
  const isAnnual = cycle === 'annual';

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 12,
      background: 'var(--bg-white)',
      border: '1.5px solid var(--border)',
      borderRadius: 'var(--r-full)',
      padding: '4px',
      boxShadow: 'var(--shadow-sm)',
    }}>
      {/* Mensile */}
      <button
        onClick={() => onChange('monthly')}
        style={{
          padding: '8px 20px',
          borderRadius: 'var(--r-full)',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'var(--font-body)',
          fontSize: '0.88rem',
          fontWeight: 600,
          transition: 'all var(--dur-base) var(--ease)',
          background: !isAnnual
            ? 'linear-gradient(135deg, var(--c-navy), var(--c-blue))'
            : 'transparent',
          color: !isAnnual ? '#fff' : 'var(--text-secondary)',
          boxShadow: !isAnnual ? 'var(--shadow-md)' : 'none',
        }}
      >
        Mensile
      </button>

      {/* Annuale */}
      <button
        onClick={() => onChange('annual')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 20px',
          borderRadius: 'var(--r-full)',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'var(--font-body)',
          fontSize: '0.88rem',
          fontWeight: 600,
          transition: 'all var(--dur-base) var(--ease)',
          background: isAnnual
            ? 'linear-gradient(135deg, var(--c-navy), var(--c-blue))'
            : 'transparent',
          color: isAnnual ? '#fff' : 'var(--text-secondary)',
          boxShadow: isAnnual ? 'var(--shadow-md)' : 'none',
        }}
      >
        Annuale
        {/* Badge sconto */}
        <span style={{
          padding: '2px 8px',
          background: isAnnual
            ? 'rgba(255,255,255,.2)'
            : 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
          color: isAnnual ? '#fff' : 'var(--c-navy-dark)',
          borderRadius: 'var(--r-full)',
          fontSize: '0.65rem',
          fontWeight: 800,
          letterSpacing: '.04em',
          whiteSpace: 'nowrap',
        }}>
          -25%
        </span>
      </button>
    </div>
  );
};
