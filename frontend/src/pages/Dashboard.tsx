// ─────────────────────────────────────────
// src/pages/Dashboard.tsx
// Panoramica dashboard: benvenuto, utilizzo, azioni rapide
// ─────────────────────────────────────────

import React, { useEffect, useState } from 'react';
import type { Lang, View, User, UserLimits } from '../types';
import { t } from '../i18n/translations';
import { authGet } from '../hooks/useApi';
import { Button } from '../components/ui/Button';
import { Card, TitledCard } from '../components/ui/Card';
import { PlanBadge } from '../components/PlanBadge';

interface DashboardProps {
  lang: Lang;
  user: User | null;
  onNavigate: (view: View) => void;
  limits: UserLimits | null;
  onLimitsLoaded: (limits: UserLimits) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  lang, user, onNavigate, limits, onLimitsLoaded,
}) => {
  useEffect(() => {
    authGet<UserLimits>('/users/me/limits').then((data) => {
      if (data) onLimitsLoaded(data);
    });
  }, []);

  if (!user) return null;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? '☀️' : hour < 18 ? '🌤' : '🌙';

  return (
    <div style={{
      padding: 32,
      maxWidth: 960,
      margin: '0 auto',
      animation: 'fadeIn .4s ease both',
    }}>
      {/* Welcome header */}
      <div style={{ marginBottom: 36 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          marginBottom: 6,
        }}>
          <span style={{ fontSize: 24 }}>{greeting}</span>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(1.6rem, 3vw, 2.2rem)',
            color: 'var(--text-navy)',
          }}>
            {t(lang, 'dashboardWelcome')}, {user.name.split(' ')[0]}
          </h1>
          <PlanBadge plan={user.plan} />
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
          {t(lang, 'dashboardSubtitle')}
        </p>
      </div>

      {/* Quick actions */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{
          fontSize: '0.75rem',
          fontWeight: 700,
          letterSpacing: '.1em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
          marginBottom: 14,
          fontFamily: 'var(--font-body)',
        }}>
          {t(lang, 'dashboardQuickActions')}
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
        }}>
          <QuickActionCard
            icon="⬡"
            title={t(lang, 'navDeepResearch')}
            description="Analisi AI multi-agente su 1-5 proprietà"
            color="var(--c-blue)"
            remaining={limits?.remaining?.deepresearch}
            max={limits?.limits?.deepresearch}
            onClick={() => onNavigate('deepresearch')}
          />
          <QuickActionCard
            icon="◎"
            title={t(lang, 'navCalcola')}
            description="3 scenari ROI con stime real-time"
            color="var(--c-green)"
            remaining={limits?.remaining?.calcola}
            max={limits?.limits?.calcola}
            onClick={() => onNavigate('calcola')}
          />
          {user.plan !== 'free' && (
            <QuickActionCard
              icon="▣"
              title={t(lang, 'navReports')}
              description="Export PDF dei tuoi report di analisi"
              color="var(--c-gold)"
              onClick={() => onNavigate('reports')}
            />
          )}
        </div>
      </div>

      {/* Usage stats */}
      {limits && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 20,
          marginBottom: 32,
        }}>
          <TitledCard title={t(lang, 'dashboardUsageToday')} style={{ flex: 1 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <UsageBar
                label="Deep Research"
                used={limits.usage_today.deepresearch ?? 0}
                max={limits.limits.deepresearch ?? 1}
                color="var(--c-blue)"
              />
              <UsageBar
                label="Calcola ROI"
                used={limits.usage_today.calcola ?? 0}
                max={limits.limits.calcola ?? 3}
                color="var(--c-green)"
              />
            </div>
          </TitledCard>

          {/* Upgrade card — solo per FREE */}
          {user.plan === 'free' && (
            <Card style={{
              background: 'linear-gradient(135deg, var(--c-navy), var(--c-navy-light))',
              border: 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
            }}>
              <div style={{
                fontSize: 28,
                marginBottom: 12,
                filter: 'drop-shadow(0 2px 8px rgba(201,168,76,.4))',
              }}>⚡</div>
              <h3 style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.1rem',
                color: '#fff',
                marginBottom: 8,
              }}>
                {t(lang, 'dashboardUpgrade')}
              </h3>
              <p style={{
                fontSize: '0.82rem',
                color: 'rgba(255,255,255,.55)',
                marginBottom: 18,
                lineHeight: 1.6,
              }}>
                Passa a Pro per 5x più analisi e report PDF illimitati.
              </p>
              <Button
                variant="gold"
                size="sm"
                onClick={() => onNavigate('pricing')}
              >
                Vedi i Piani →
              </Button>
            </Card>
          )}
        </div>
      )}

      {/* Recent activity placeholder */}
      <TitledCard title={t(lang, 'dashboardRecentActivity')}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '32px 0',
          color: 'var(--text-muted)',
          gap: 10,
        }}>
          <span style={{ fontSize: 32, opacity: .4 }}>◈</span>
          <p style={{ fontSize: '0.88rem' }}>{t(lang, 'dashboardNoActivity')}</p>
          <Button variant="secondary" size="sm" onClick={() => onNavigate('deepresearch')}>
            Avvia la prima analisi
          </Button>
        </div>
      </TitledCard>
    </div>
  );
};

/* ── Quick action card ── */
const QuickActionCard: React.FC<{
  icon: string;
  title: string;
  description: string;
  color: string;
  remaining?: number;
  max?: number;
  onClick: () => void;
}> = ({ icon, title, description, color, remaining, max, onClick }) => (
  <button
    onClick={onClick}
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
      padding: 22,
      background: 'var(--bg-white)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--r-lg)',
      cursor: 'pointer',
      textAlign: 'left',
      boxShadow: 'var(--shadow-sm)',
      transition: 'all var(--dur-base) var(--ease)',
      fontFamily: 'var(--font-body)',
    }}
    onMouseEnter={(e) => {
      const el = e.currentTarget;
      el.style.transform = 'translateY(-3px)';
      el.style.boxShadow = 'var(--shadow-md)';
      el.style.borderColor = color;
    }}
    onMouseLeave={(e) => {
      const el = e.currentTarget;
      el.style.transform = '';
      el.style.boxShadow = 'var(--shadow-sm)';
      el.style.borderColor = 'var(--border)';
    }}
  >
    <div style={{
      width: 42, height: 42,
      background: `${color}14`,
      border: `1px solid ${color}25`,
      borderRadius: 11,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 18, color,
      marginBottom: 12,
    }}>
      {icon}
    </div>
    <div style={{
      fontSize: '0.92rem',
      fontWeight: 700,
      color: 'var(--text-navy)',
      marginBottom: 5,
    }}>
      {title}
    </div>
    <div style={{
      fontSize: '0.78rem',
      color: 'var(--text-muted)',
      lineHeight: 1.5,
      marginBottom: remaining !== undefined ? 12 : 0,
    }}>
      {description}
    </div>
    {remaining !== undefined && max !== undefined && (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        background: remaining === 0 ? 'rgba(239,68,68,.08)' : `${color}10`,
        borderRadius: 'var(--r-full)',
        fontSize: '0.72rem',
        fontWeight: 600,
        color: remaining === 0 ? 'var(--c-red)' : color,
        marginTop: 'auto',
      }}>
        {remaining}/{max} rimanenti oggi
      </div>
    )}
  </button>
);

/* ── Usage bar ── */
const UsageBar: React.FC<{
  label: string; used: number; max: number; color: string;
}> = ({ label, used, max, color }) => {
  const pct = Math.min((used / max) * 100, 100);
  const full = used >= max;

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: 6,
        fontSize: '0.82rem',
      }}>
        <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600, color: full ? 'var(--c-red)' : 'var(--text-navy)' }}>
          {used} / {max}
        </span>
      </div>
      <div style={{
        height: 6,
        background: 'var(--bg-muted)',
        borderRadius: 'var(--r-full)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: full ? 'var(--c-red)' : color,
          borderRadius: 'var(--r-full)',
          transition: 'width .6s var(--ease)',
        }} />
      </div>
    </div>
  );
};
