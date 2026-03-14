// ─────────────────────────────────────────
// src/components/Sidebar.tsx
// Sidebar navigazione della dashboard con collasso
// ─────────────────────────────────────────

import React from 'react';
import type { Lang, View, User } from '../types';
import { SIDEBAR_ITEMS } from '../types';
import { t } from '../i18n/translations';
import { PlanBadge } from './PlanBadge';
import { LangSelector } from './LangSelector';

interface SidebarProps {
  lang: Lang;
  onLangChange: (l: Lang) => void;
  currentView: View;
  onNavigate: (view: View) => void;
  onLogout: () => void;
  user: User | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  lang, onLangChange, currentView, onNavigate, onLogout,
  user, collapsed, onToggleCollapse,
}) => {
  const w = collapsed ? 'var(--sidebar-w-col)' : 'var(--sidebar-w)';

  return (
    <aside style={{
      width: w,
      minHeight: '100vh',
      background: 'var(--bg-sidebar)',
      display: 'flex',
      flexDirection: 'column',
      transition: 'width var(--dur-base) var(--ease)',
      overflow: 'hidden',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      zIndex: 200,
    }}>
      {/* Header / Logo */}
      <div style={{
        padding: collapsed ? '20px 0' : '20px 20px 16px',
        borderBottom: '1px solid rgba(255,255,255,.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        gap: 10,
      }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32,
              background: 'linear-gradient(135deg, var(--c-blue) 0%, var(--c-blue-light) 100%)',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, flexShrink: 0,
            }}>⬡</div>
            <span style={{
              fontFamily: 'var(--font-display)',
              fontSize: '0.95rem',
              fontWeight: 700,
              color: '#fff',
              whiteSpace: 'nowrap',
            }}>
              Big House <span style={{ color: 'var(--c-blue-light)' }}>AI</span>
            </span>
          </div>
        )}
        {collapsed && (
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(135deg, var(--c-blue), var(--c-blue-light))',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>⬡</div>
        )}
        {/* Collapse toggle */}
        <button
          onClick={onToggleCollapse}
          title={collapsed ? 'Espandi' : 'Comprimi'}
          style={{
            background: 'rgba(255,255,255,.07)',
            border: '1px solid rgba(255,255,255,.1)',
            borderRadius: 6,
            padding: '4px 6px',
            cursor: 'pointer',
            color: 'rgba(255,255,255,.6)',
            fontSize: 11,
            display: 'flex',
            flexShrink: 0,
            transition: 'background var(--dur-fast)',
          }}
          onMouseEnter={(e) => { (e.currentTarget).style.background = 'rgba(255,255,255,.14)'; }}
          onMouseLeave={(e) => { (e.currentTarget).style.background = 'rgba(255,255,255,.07)'; }}
        >
          {collapsed ? '▶' : '◀'}
        </button>
      </div>

      {/* User info */}
      {user && (
        <div style={{
          padding: collapsed ? '14px 0' : '14px 20px',
          borderBottom: '1px solid rgba(255,255,255,.06)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          justifyContent: collapsed ? 'center' : 'flex-start',
        }}>
          {/* Avatar */}
          <div style={{
            width: 34, height: 34,
            borderRadius: 'var(--r-full)',
            background: 'linear-gradient(135deg, var(--c-navy-light), var(--c-blue))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.85rem',
            fontWeight: 700,
            color: '#fff',
            flexShrink: 0,
            cursor: 'pointer',
          }}
            title={user.name}
          >
            {user.name.charAt(0).toUpperCase()}
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden' }}>
              <div style={{
                fontSize: '0.82rem',
                fontWeight: 600,
                color: '#fff',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {user.name}
              </div>
              <PlanBadge plan={user.plan} size="sm" />
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav style={{ flex: 1, padding: collapsed ? '16px 10px' : '16px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {!collapsed && (
          <div style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            letterSpacing: '.1em',
            color: 'rgba(255,255,255,.3)',
            textTransform: 'uppercase',
            padding: '0 8px',
            marginBottom: 6,
          }}>
            Menu
          </div>
        )}

        {SIDEBAR_ITEMS.map((item) => {
          const active = currentView === item.id;
          const locked = item.planRequired && user?.plan === 'free' && item.planRequired !== 'free';

          return (
            <button
              key={item.id}
              onClick={() => !locked && onNavigate(item.id)}
              title={collapsed ? t(lang, item.labelKey as any) : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                padding: collapsed ? '11px' : '10px 12px',
                borderRadius: 'var(--r-md)',
                background: active
                  ? 'rgba(37,99,235,.25)'
                  : 'transparent',
                border: active
                  ? '1px solid rgba(37,99,235,.4)'
                  : '1px solid transparent',
                cursor: locked ? 'not-allowed' : 'pointer',
                width: '100%',
                opacity: locked ? 0.5 : 1,
                transition: 'all var(--dur-fast) var(--ease)',
                color: active ? '#fff' : 'rgba(255,255,255,.65)',
                fontFamily: 'var(--font-body)',
              }}
              onMouseEnter={(e) => {
                if (!active && !locked)
                  e.currentTarget.style.background = 'rgba(255,255,255,.07)';
              }}
              onMouseLeave={(e) => {
                if (!active) e.currentTarget.style.background = 'transparent';
              }}
            >
              <span style={{
                fontSize: 16,
                flexShrink: 0,
                color: active ? 'var(--c-blue-light)' : 'rgba(255,255,255,.5)',
              }}>
                {item.icon}
              </span>
              {!collapsed && (
                <>
                  <span style={{ fontSize: '0.88rem', fontWeight: active ? 600 : 400, flex: 1, textAlign: 'left' }}>
                    {t(lang, item.labelKey as any)}
                  </span>
                  {locked && (
                    <span style={{ fontSize: '0.65rem', color: 'var(--c-gold)', fontWeight: 700 }}>PRO</span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div style={{
        padding: collapsed ? '14px 10px' : '14px 12px',
        borderTop: '1px solid rgba(255,255,255,.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        alignItems: collapsed ? 'center' : 'stretch',
      }}>
        {/* Upgrade CTA — solo FREE */}
        {!collapsed && user?.plan === 'free' && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(201,168,76,.15), rgba(37,99,235,.1))',
            border: '1px solid rgba(201,168,76,.2)',
            borderRadius: 'var(--r-md)',
            padding: '12px 14px',
            marginBottom: 4,
          }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--c-gold)', marginBottom: 4 }}>
              ⚡ Upgrade
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,.5)', marginBottom: 10 }}>
              {t(lang, 'dashboardUpgrade')}
            </div>
            <button
              onClick={() => onNavigate('pricing')}
              style={{
                width: '100%',
                padding: '6px',
                background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
                border: 'none',
                borderRadius: 'var(--r-sm)',
                color: 'var(--c-navy-dark)',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                fontFamily: 'var(--font-body)',
              }}
            >
              {t(lang, 'pricingUpgrade')} PRO →
            </button>
          </div>
        )}

        {/* Lang selector */}
        <div style={{ display: 'flex', justifyContent: collapsed ? 'center' : 'flex-start' }}>
          <LangSelector lang={lang} onChange={onLangChange} dark />
        </div>

        {/* Logout */}
        <button
          onClick={onLogout}
          title="Logout"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: collapsed ? 0 : 10,
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '9px' : '9px 12px',
            background: 'transparent',
            border: '1px solid transparent',
            borderRadius: 'var(--r-md)',
            cursor: 'pointer',
            color: 'rgba(255,255,255,.45)',
            fontSize: '0.85rem',
            fontFamily: 'var(--font-body)',
            transition: 'all var(--dur-fast)',
            width: '100%',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(239,68,68,.1)';
            e.currentTarget.style.color = '#fca5a5';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'rgba(255,255,255,.45)';
          }}
        >
          <span style={{ fontSize: 14 }}>↩</span>
          {!collapsed && <span>{t(lang, 'navLogout')}</span>}
        </button>
      </div>
    </aside>
  );
};
