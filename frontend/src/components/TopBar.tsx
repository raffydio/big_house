// src/components/TopBar.tsx — AGGIORNATO
// Lingua vicino all'avatar, storage indicator, hamburger mobile

import React from 'react';
import type { Lang, View, User, UserLimits } from '../types';
import { t } from '../i18n/translations';
import { PlanBadge } from './PlanBadge';
import { LangSelector } from './LangSelector';
import { StorageIndicator } from './StorageIndicator';
import type { StorageInfo } from '../types';

interface TopBarProps {
  lang: Lang;
  onLangChange: (l: Lang) => void;
  currentView: View;
  user: User | null;
  limits: UserLimits | null;
  storageInfo: StorageInfo | null;
  onNavigate: (view: View) => void;
  onMenuToggle: () => void; // apre sidebar su mobile
}

const VIEW_TITLES: Record<string, string> = {
  dashboard:    'navOverview',
  deepresearch: 'navDeepResearch',
  calcola:      'navCalcola',
  reports:      'navReports',
  history:      'navHistory',
  storage:      'navStorage',
};

export const TopBar: React.FC<TopBarProps> = ({
  lang, onLangChange, currentView, user, limits, storageInfo,
  onNavigate, onMenuToggle,
}) => {
  const titleKey = VIEW_TITLES[currentView] ?? 'navOverview';

  return (
    <header className="topbar" style={{
      height: 'var(--topbar-h)',
      background: 'var(--bg-white)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 20px',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      flexShrink: 0,
      gap: 12,
    }}>
      {/* Left: hamburger (mobile) + title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        {/* Hamburger — visibile solo mobile */}
        <button
          onClick={onMenuToggle}
          aria-label="Menu"
          style={{
            display: 'none', // visibile via CSS media query (.show-mobile)
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: 'var(--r-sm)',
            color: 'var(--text-secondary)',
            fontSize: 20,
            flexShrink: 0,
          }}
          className="show-mobile"
        >
          ☰
        </button>

        <h1 className="topbar-title" style={{
          fontFamily: 'var(--font-body)',
          fontSize: '0.95rem',
          fontWeight: 700,
          color: 'var(--text-navy)',
          letterSpacing: '-0.01em',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {t(lang, titleKey as any)}
        </h1>
      </div>

      {/* Right: usage + lang + storage + avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
        {/* Usage pills — nascoste su mobile piccolo */}
        {limits && (
          <div className="hide-mobile" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <UsagePill
              label="DR"
              used={limits.usage_today.deepresearch ?? 0}
              max={limits.limits.deepresearch ?? 1}
              color="var(--c-blue)"
            />
            <UsagePill
              label="Calc"
              used={limits.usage_today.calcola ?? 0}
              max={limits.limits.calcola ?? 3}
              color="var(--c-green)"
            />
          </div>
        )}

        {/* Storage circle — solo piani pagati */}
        {user && user.plan !== 'free' && (
          <button
            onClick={() => onNavigate('storage')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            title="Gestione storage"
          >
            <StorageIndicator storageInfo={storageInfo} compact />
          </button>
        )}

        {/* Upgrade badge — FREE */}
        {user?.plan === 'free' && (
          <button
            onClick={() => onNavigate('pricing')}
            className="hide-mobile"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '5px 12px',
              background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
              border: 'none',
              borderRadius: 'var(--r-full)',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--c-navy-dark)',
              fontFamily: 'var(--font-body)',
              whiteSpace: 'nowrap',
            }}
          >
            ⚡ Upgrade
          </button>
        )}

        {/* ── LANGUAGE SELECTOR — vicino avatar ── */}
        <LangSelector lang={lang} onChange={onLangChange} />

        {/* User avatar + plan */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <PlanBadge plan={user.plan} size="sm" />
            <div
              title={`${user.name} · ${user.email}`}
              style={{
                width: 34, height: 34,
                borderRadius: 'var(--r-full)',
                background: 'linear-gradient(135deg, var(--c-navy), var(--c-blue))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.82rem',
                fontWeight: 700,
                color: '#fff',
                flexShrink: 0,
                cursor: 'default',
                userSelect: 'none',
              }}
            >
              {user.name.charAt(0).toUpperCase()}
            </div>
          </div>
        )}
      </div>

      {/* CSS per hamburger mobile */}
      <style>{`
        @media (max-width: 768px) {
          .show-mobile { display: flex !important; }
        }
      `}</style>
    </header>
  );
};

// ── Usage pill ──
const UsagePill: React.FC<{
  label: string; used: number; max: number; color: string;
}> = ({ label, used, max, color }) => {
  const pct  = Math.min((used / max) * 100, 100);
  const full = used >= max;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
      <div style={{ width: 44, height: 4, background: 'var(--bg-muted)', borderRadius: 'var(--r-full)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: full ? 'var(--c-red)' : color,
          borderRadius: 'var(--r-full)',
          transition: 'width var(--dur-base)',
        }} />
      </div>
      <span style={{ fontSize: '0.68rem', color: full ? 'var(--c-red)' : 'var(--text-muted)', fontWeight: 500 }}>
        {used}/{max}
      </span>
    </div>
  );
};
