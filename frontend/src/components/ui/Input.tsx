// ─────────────────────────────────────────
// src/components/ui/Input.tsx
// ─────────────────────────────────────────

import React, { useState } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  rows?: number;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.8rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  marginBottom: 6,
  letterSpacing: '0.03em',
  textTransform: 'uppercase',
};

const errorStyle: React.CSSProperties = {
  fontSize: '0.78rem',
  color: 'var(--c-red)',
  marginTop: 4,
};

const hintStyle: React.CSSProperties = {
  fontSize: '0.78rem',
  color: 'var(--text-muted)',
  marginTop: 4,
};

// ── Helper: calcola il border completo senza conflitti ──
// Usa SOLO border (non borderColor separato) per evitare il warning React
function getBorder(focused: boolean, hasError: boolean): string {
  if (hasError)    return '1.5px solid var(--c-red)';
  if (focused)     return '1.5px solid var(--c-blue)';
  return '1.5px solid var(--border)';
}

export const Input: React.FC<InputProps> = ({
  label, error, hint, leftIcon,
  style, onFocus, onBlur, ...props
}) => {
  const [focused, setFocused] = useState(false);

  return (
    <div style={{ marginBottom: 0 }}>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={{ position: 'relative' }}>
        {leftIcon && (
          <span style={{
            position: 'absolute', left: 12, top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-muted)', display: 'flex', pointerEvents: 'none',
          }}>
            {leftIcon}
          </span>
        )}
        <input
          {...props}
          onFocus={(e) => { setFocused(true); onFocus?.(e); }}
          onBlur={(e)  => { setFocused(false); onBlur?.(e); }}
          style={{
            width: '100%',
            padding: leftIcon ? '10px 14px 10px 38px' : '10px 14px',
            fontSize: '0.95rem',
            background: 'var(--bg-white)',
            border: getBorder(focused, !!error),   // ← solo border, mai borderColor
            borderRadius: 'var(--r-md)',
            color: 'var(--text-primary)',
            outline: 'none',
            boxShadow: focused && !error
              ? '0 0 0 3px rgba(37,99,235,.12)'
              : 'none',
            transition: 'border var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease)',
            ...style,
          }}
        />
      </div>
      {error && <p style={errorStyle}>{error}</p>}
      {hint && !error && <p style={hintStyle}>{hint}</p>}
    </div>
  );
};

export const Textarea: React.FC<TextareaProps> = ({
  label, error, hint, rows = 4,
  style, onFocus, onBlur, ...props
}) => {
  const [focused, setFocused] = useState(false);

  return (
    <div>
      {label && <label style={labelStyle}>{label}</label>}
      <textarea
        {...props}
        rows={rows}
        onFocus={(e) => { setFocused(true); onFocus?.(e); }}
        onBlur={(e)  => { setFocused(false); onBlur?.(e); }}
        style={{
          width: '100%',
          padding: '10px 14px',
          fontSize: '0.95rem',
          background: 'var(--bg-white)',
          border: getBorder(focused, !!error),
          borderRadius: 'var(--r-md)',
          color: 'var(--text-primary)',
          outline: 'none',
          resize: 'vertical',
          minHeight: 90,
          boxShadow: focused && !error
            ? '0 0 0 3px rgba(37,99,235,.12)'
            : 'none',
          transition: 'border var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease)',
          ...style,
        }}
      />
      {error && <p style={errorStyle}>{error}</p>}
      {hint && !error && <p style={hintStyle}>{hint}</p>}
    </div>
  );
};

export const Select: React.FC<SelectProps> = ({
  label, error, options, style, ...props
}) => (
  <div>
    {label && <label style={labelStyle}>{label}</label>}
    <select
      {...props}
      style={{
        width: '100%',
        padding: '10px 32px 10px 14px',
        fontSize: '0.95rem',
        background: 'var(--bg-white)',
        border: '1.5px solid var(--border)',
        borderRadius: 'var(--r-md)',
        color: 'var(--text-primary)',
        outline: 'none',
        cursor: 'pointer',
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2394a3b8' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 12px center',
        ...style,
      }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
    {error && <p style={errorStyle}>{error}</p>}
  </div>
);