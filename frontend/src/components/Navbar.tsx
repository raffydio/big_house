// ─────────────────────────────────────────
// src/components/Navbar.tsx
// Navbar per le pagine pubbliche (landing, pricing, auth)
// ─────────────────────────────────────────
// ─────────────────────────────────────────
// src/components/Navbar.tsx
// ─────────────────────────────────────────

import React, { useState, useEffect } from 'react';
import type { Lang, View, User } from '../types';
import { t } from '../i18n/translations';
import { LangSelector } from './LangSelector';
import { PlanBadge } from './PlanBadge';
import { Button } from './ui/Button';

interface NavbarProps {
  lang: Lang;
  onLangChange: (l: Lang) => void;
  onNavigate: (view: View) => void;
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  lang, onLangChange, onNavigate, user, onLogout,
}) => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <>
      {/* ── Media query per nascondere nav-links su mobile ── */}
      <style>{`
        .navbar-links { display: flex; }
        @media (max-width: 768px) { .navbar-links { display: none !important; } }
      `}</style>

      <nav style={{
        position: 'sticky',
        top: 0,
        zIndex: 900,
        background: scrolled ? 'rgba(248,250,255,.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid var(--border)' : 'none',
        transition: 'all var(--dur-base) var(--ease)',
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 24px',
          height: 68,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 24,
        }}>

          {/* Logo */}
          <button
            onClick={() => onNavigate('landing')}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: 'none', border: 'none', cursor: 'pointer',
              padding: 0, flexShrink: 0,
            }}
          >
            <div style={{
              width: 36, height: 36,
              background: 'linear-gradient(135deg, var(--c-navy), var(--c-blue))',
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18,
            }}>⬡</div>
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: '1.15rem',
              fontWeight: 700, color: 'var(--text-navy)', letterSpacing: '-0.01em',
            }}>
              Big House <span style={{ color: 'var(--c-blue)' }}>AI</span>
            </span>
          </button>

          {/* Nav links — desktop only (nascosti su mobile via CSS) */}
          <div
            className="navbar-links"
            style={{ alignItems: 'center', gap: 4 }}
          >
            <NavLink label={t(lang, 'navPricing')} onClick={() => onNavigate('pricing')} />
          </div>

          {/* Right side */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <LangSelector lang={lang} onChange={onLangChange} />

            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <PlanBadge plan={user.plan} size="sm" />
                <Button
                  variant="ghost" size="sm"
                  onClick={() => onNavigate('dashboard')}
                  style={{ color: 'var(--c-blue)', fontWeight: 600 }}
                >
                  Dashboard
                </Button>
                <Button variant="secondary" size="sm" onClick={onLogout}>
                  {t(lang, 'navLogout')}
                </Button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Button
                  variant="ghost" size="sm"
                  onClick={() => onNavigate('login')}
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {t(lang, 'navLogin')}
                </Button>
                <Button variant="primary" size="sm" onClick={() => onNavigate('register')}>
                  {t(lang, 'navRegister')}
                </Button>
              </div>
            )}
          </div>
        </div>
      </nav>
    </>
  );
};

const NavLink: React.FC<{ label: string; onClick: () => void }> = ({ label, onClick }) => (
  <button
    onClick={onClick}
    style={{
      background: 'none', border: 'none', cursor: 'pointer',
      padding: '6px 12px', fontSize: '0.9rem', fontWeight: 500,
      color: 'var(--text-secondary)', borderRadius: 'var(--r-sm)',
      fontFamily: 'var(--font-body)',
      transition: 'color var(--dur-fast), background var(--dur-fast)',
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.color = 'var(--c-blue)';
      e.currentTarget.style.background = 'var(--bg-muted)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.color = 'var(--text-secondary)';
      e.currentTarget.style.background = 'transparent';
    }}
  >
    {label}
  </button>
);