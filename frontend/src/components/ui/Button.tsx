// ─────────────────────────────────────────
// src/components/ui/Button.tsx
// Pulsante riutilizzabile con varianti e stati
// ─────────────────────────────────────────

import React from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'gold';
type Size    = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const baseStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
  fontFamily: 'var(--font-body)',
  fontWeight: 600,
  letterSpacing: '0.01em',
  border: 'none',
  borderRadius: 'var(--r-md)',
  cursor: 'pointer',
  transition: 'all var(--dur-base) var(--ease)',
  whiteSpace: 'nowrap',
  userSelect: 'none',
  position: 'relative',
  overflow: 'hidden',
};

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: 'linear-gradient(135deg, var(--c-navy) 0%, var(--c-blue) 100%)',
    color: '#fff',
    boxShadow: '0 4px 14px rgba(37,99,235,.3)',
  },
  secondary: {
    background: 'var(--bg-white)',
    color: 'var(--c-navy)',
    border: '1.5px solid var(--border)',
    boxShadow: 'var(--shadow-sm)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-secondary)',
  },
  danger: {
    background: 'linear-gradient(135deg, #dc2626, #ef4444)',
    color: '#fff',
    boxShadow: '0 4px 14px rgba(239,68,68,.3)',
  },
  gold: {
    background: 'linear-gradient(135deg, var(--c-gold) 0%, var(--c-gold-light) 100%)',
    color: 'var(--c-navy-dark)',
    boxShadow: '0 4px 14px rgba(201,168,76,.3)',
  },
};

const sizeStyles: Record<Size, React.CSSProperties> = {
  sm: { padding: '6px 14px', fontSize: '0.8rem', borderRadius: 'var(--r-sm)' },
  md: { padding: '10px 22px', fontSize: '0.9rem' },
  lg: { padding: '14px 32px', fontSize: '1rem', borderRadius: 'var(--r-lg)' },
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  children,
  disabled,
  style,
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <button
      {...props}
      disabled={isDisabled}
      style={{
        ...baseStyle,
        ...variantStyles[variant],
        ...sizeStyles[size],
        ...(fullWidth ? { width: '100%' } : {}),
        ...(isDisabled ? { opacity: 0.6, cursor: 'not-allowed', boxShadow: 'none' } : {}),
        ...style,
      }}
    >
      {loading ? (
        <span className={variant === 'secondary' ? 'spinner spinner--dark' : 'spinner'} />
      ) : (
        <>
          {leftIcon && <span style={{ display: 'flex', alignItems: 'center' }}>{leftIcon}</span>}
          {children}
          {rightIcon && <span style={{ display: 'flex', alignItems: 'center' }}>{rightIcon}</span>}
        </>
      )}
    </button>
  );
};
