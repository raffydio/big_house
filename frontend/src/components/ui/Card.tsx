// ─────────────────────────────────────────
// src/components/ui/Card.tsx
// Card container con varianti
// ─────────────────────────────────────────

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  padding?: number | string;
  hoverable?: boolean;
  highlighted?: boolean;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  style,
  className,
  padding = 24,
  hoverable = false,
  highlighted = false,
  onClick,
}) => (
  <div
    className={className}
    onClick={onClick}
    style={{
      background: 'var(--bg-card)',
      border: highlighted
        ? '2px solid var(--c-blue)'
        : '1px solid var(--border)',
      borderRadius: 'var(--r-lg)',
      padding: typeof padding === 'number' ? `${padding}px` : padding,
      boxShadow: highlighted ? 'var(--shadow-lg)' : 'var(--shadow-sm)',
      transition: 'all var(--dur-base) var(--ease)',
      ...(hoverable || onClick ? { cursor: 'pointer' } : {}),
      ...(hoverable
        ? {
            ':hover': {
              transform: 'translateY(-2px)',
              boxShadow: 'var(--shadow-md)',
            },
          }
        : {}),
      ...style,
    }}
  >
    {children}
  </div>
);

/** Card titolata con header divider */
export const TitledCard: React.FC<{
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ title, subtitle, action, children, style }) => (
  <Card style={style}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
      <div>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-navy)', fontFamily: 'var(--font-body)', marginBottom: subtitle ? 2 : 0 }}>
          {title}
        </h3>
        {subtitle && (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{subtitle}</p>
        )}
      </div>
      {action}
    </div>
    {children}
  </Card>
);
