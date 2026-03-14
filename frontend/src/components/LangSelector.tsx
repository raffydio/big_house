// ─────────────────────────────────────────
// src/components/LangSelector.tsx
// Selettore lingua con dropdown elegante
// ─────────────────────────────────────────

import React, { useState, useRef, useEffect } from 'react';
import type { Lang } from '../types';

interface LangSelectorProps {
  lang: Lang;
  onChange: (lang: Lang) => void;
  dark?: boolean; // versione per sfondo scuro (sidebar)
}

const LANGS: { code: Lang; label: string; flag: string }[] = [
  { code: 'it', label: 'Italiano',   flag: '🇮🇹' },
  { code: 'en', label: 'English',    flag: '🇬🇧' },
  { code: 'fr', label: 'Français',   flag: '🇫🇷' },
  { code: 'de', label: 'Deutsch',    flag: '🇩🇪' },
  { code: 'es', label: 'Español',    flag: '🇪🇸' },
  { code: 'pt', label: 'Português',  flag: '🇵🇹' },
];

export const LangSelector: React.FC<LangSelectorProps> = ({ lang, onChange, dark = false }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = LANGS.find((l) => l.code === lang) ?? LANGS[0];

  // Chiudi dropdown al click esterno
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const textColor = dark ? 'rgba(255,255,255,.8)' : 'var(--text-secondary)';
  const borderColor = dark ? 'rgba(255,255,255,.12)' : 'var(--border)';
  const bgColor = dark ? 'rgba(255,255,255,.06)' : 'var(--bg-white)';
  const hoverBg = dark ? 'rgba(255,255,255,.1)' : 'var(--bg-muted)';
  const dropdownBg = 'var(--bg-white)';

  return (
    <div ref={ref} style={{ position: 'relative', zIndex: 100 }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Select language"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 10px',
          background: bgColor,
          border: `1px solid ${borderColor}`,
          borderRadius: 'var(--r-sm)',
          cursor: 'pointer',
          color: textColor,
          fontSize: '0.82rem',
          fontWeight: 500,
          fontFamily: 'var(--font-body)',
          transition: 'background var(--dur-fast)',
        }}
        onMouseEnter={(e) => { (e.target as HTMLElement).style.background = hoverBg; }}
        onMouseLeave={(e) => { (e.target as HTMLElement).style.background = bgColor; }}
      >
        <span style={{ fontSize: 14 }}>{current.flag}</span>
        <span>{current.code.toUpperCase()}</span>
        <span style={{
          fontSize: 8,
          opacity: .6,
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform var(--dur-fast)',
        }}>▼</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          background: dropdownBg,
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-md)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          minWidth: 150,
          animation: 'fadeIn .15s ease both',
        }}>
          {LANGS.map((l) => (
            <button
              key={l.code}
              onClick={() => { onChange(l.code); setOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                width: '100%',
                padding: '9px 14px',
                background: l.code === lang ? 'var(--c-blue-pale)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: l.code === lang ? 'var(--c-blue)' : 'var(--text-primary)',
                fontSize: '0.85rem',
                fontWeight: l.code === lang ? 600 : 400,
                fontFamily: 'var(--font-body)',
                textAlign: 'left',
                transition: 'background var(--dur-fast)',
              }}
              onMouseEnter={(e) => {
                if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'var(--bg-muted)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = l.code === lang ? 'var(--c-blue-pale)' : 'transparent';
              }}
            >
              <span style={{ fontSize: 16 }}>{l.flag}</span>
              <span>{l.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
