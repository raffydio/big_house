// ─────────────────────────────────────────
// src/pages/LandingPage.tsx
// Landing page con Hero, Features e CTA
// ─────────────────────────────────────────

import React from 'react';
import type { Lang, View } from '../types';
import { t } from '../i18n/translations';
import { Button } from '../components/ui/Button';

interface LandingPageProps {
  lang: Lang;
  onNavigate: (view: View) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ lang, onNavigate }) => (
  <div>
    <HeroSection lang={lang} onNavigate={onNavigate} />
    <FeaturesSection lang={lang} />
    <StatsSection lang={lang} />
    <CtaSection lang={lang} onNavigate={onNavigate} />
    <Footer lang={lang} onNavigate={onNavigate} />
  </div>
);

/* ── Hero ── */
const HeroSection: React.FC<{ lang: Lang; onNavigate: (v: View) => void }> = ({ lang, onNavigate }) => (
  <section style={{
    minHeight: '92vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
    background: `
      radial-gradient(ellipse 80% 60% at 50% -10%, rgba(37,99,235,.12) 0%, transparent 70%),
      radial-gradient(ellipse 40% 40% at 85% 50%, rgba(26,58,110,.08) 0%, transparent 60%),
      var(--bg-page)
    `,
    padding: '100px 24px 80px',
  }}>
    {/* Decorative grid */}
    <div style={{
      position: 'absolute',
      inset: 0,
      backgroundImage: `
        linear-gradient(rgba(37,99,235,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37,99,235,.04) 1px, transparent 1px)
      `,
      backgroundSize: '48px 48px',
      pointerEvents: 'none',
    }} />

    {/* Floating shapes */}
    <FloatingShape size={320} x="10%" y="20%" opacity={0.04} delay={0} />
    <FloatingShape size={200} x="75%" y="60%" opacity={0.06} delay={1} />
    <FloatingShape size={140} x="85%" y="15%" opacity={0.05} delay={2} />

    <div style={{
      maxWidth: 780,
      textAlign: 'center',
      position: 'relative',
      zIndex: 1,
      animation: 'fadeIn .8s ease both',
    }}>
      {/* Tagline pill */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '7px 18px',
        background: 'rgba(37,99,235,.08)',
        border: '1px solid rgba(37,99,235,.15)',
        borderRadius: 'var(--r-full)',
        marginBottom: 28,
        fontSize: '0.8rem',
        fontWeight: 600,
        color: 'var(--c-blue)',
        letterSpacing: '.04em',
        textTransform: 'uppercase',
      }}>
        <span style={{ animation: 'pulse 2s infinite', display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--c-blue)' }} />
        {t(lang, 'heroTagline')}
      </div>

      {/* Main title */}
      <h1 style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(2.8rem, 6vw, 4.5rem)',
        fontWeight: 700,
        lineHeight: 1.08,
        color: 'var(--text-navy)',
        marginBottom: 24,
        letterSpacing: '-0.02em',
        whiteSpace: 'pre-line',
      }}>
        {t(lang, 'heroTitle')}
      </h1>

      {/* Subtitle */}
      <p style={{
        fontSize: 'clamp(1rem, 2vw, 1.2rem)',
        color: 'var(--text-secondary)',
        maxWidth: 580,
        margin: '0 auto 40px',
        lineHeight: 1.7,
      }}>
        {t(lang, 'heroSubtitle')}
      </p>

      {/* CTAs */}
      <div style={{
        display: 'flex',
        gap: 14,
        justifyContent: 'center',
        flexWrap: 'wrap',
        marginBottom: 20,
      }}>
        <Button variant="primary" size="lg" onClick={() => onNavigate('register')}>
          {t(lang, 'heroCta')} →
        </Button>
        <Button variant="secondary" size="lg" onClick={() => onNavigate('pricing')}>
          {t(lang, 'navPricing')}
        </Button>
      </div>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        ✓ {t(lang, 'heroCtaSub')}
      </p>

      {/* Hero mockup card */}
      <div style={{
        marginTop: 60,
        background: 'var(--bg-white)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-xl)',
        boxShadow: 'var(--shadow-xl)',
        overflow: 'hidden',
        maxWidth: 680,
        margin: '60px auto 0',
      }}>
        {/* Mockup header */}
        <div style={{
          background: 'var(--bg-sidebar)',
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          {['#ef4444','#f59e0b','#10b981'].map((c) => (
            <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
          ))}
          <div style={{
            flex: 1,
            background: 'rgba(255,255,255,.1)',
            borderRadius: 6,
            height: 20,
            marginLeft: 8,
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 10,
          }}>
            <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,.4)' }}>
              bighouseai.com/dashboard
            </span>
          </div>
        </div>

        {/* Mockup content */}
        <div style={{ padding: 24, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
          {[
            { label: 'ROI Scenario A', value: '+18.4%', color: 'var(--c-green)', icon: '↑' },
            { label: 'ROI Scenario B', value: '+28.7%', color: 'var(--c-blue)', icon: '↑' },
            { label: 'ROI Scenario C', value: '+41.2%', color: 'var(--c-gold)', icon: '↑' },
          ].map((m) => (
            <div key={m.label} style={{
              background: 'var(--bg-muted)',
              borderRadius: 'var(--r-md)',
              padding: 16,
            }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6 }}>{m.label}</div>
              <div style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.4rem',
                fontWeight: 700,
                color: m.color,
              }}>
                {m.icon} {m.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </section>
);

/* ── Features ── */
const FeaturesSection: React.FC<{ lang: Lang }> = ({ lang }) => {
  const features = [
    { icon: '⬡', titleKey: 'feat1Title', descKey: 'feat1Desc', color: 'var(--c-blue)' },
    { icon: '◎', titleKey: 'feat2Title', descKey: 'feat2Desc', color: 'var(--c-green)' },
    { icon: '▣', titleKey: 'feat3Title', descKey: 'feat3Desc', color: 'var(--c-gold)' },
  ];

  return (
    <section style={{
      padding: 'var(--space-3xl) 24px',
      background: 'var(--bg-white)',
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(1.8rem, 3.5vw, 2.8rem)',
            color: 'var(--text-navy)',
            marginBottom: 14,
          }}>
            {t(lang, 'featuresTitle')}
          </h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 520, margin: '0 auto', lineHeight: 1.7 }}>
            {t(lang, 'featuresSubtitle')}
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 24,
        }}>
          {features.map((f, i) => (
            <div
              key={f.titleKey}
              style={{
                padding: 32,
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-xl)',
                background: 'var(--bg-page)',
                animation: `fadeIn .6s ${i * .12}s ease both`,
                transition: 'all var(--dur-base) var(--ease)',
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget;
                el.style.transform = 'translateY(-4px)';
                el.style.boxShadow = 'var(--shadow-lg)';
                el.style.borderColor = f.color;
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget;
                el.style.transform = '';
                el.style.boxShadow = '';
                el.style.borderColor = 'var(--border)';
              }}
            >
              <div style={{
                width: 52, height: 52,
                background: `linear-gradient(135deg, ${f.color}18, ${f.color}0a)`,
                border: `1px solid ${f.color}30`,
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                color: f.color,
                marginBottom: 20,
              }}>
                {f.icon}
              </div>
              <h3 style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.15rem',
                color: 'var(--text-navy)',
                marginBottom: 10,
              }}>
                {t(lang, f.titleKey as any)}
              </h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.65, fontSize: '0.93rem' }}>
                {t(lang, f.descKey as any)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

/* ── Stats ── */
const StatsSection: React.FC<{ lang: Lang }> = ({ lang }) => (
  <section style={{
    padding: 'var(--space-2xl) 24px',
    background: 'linear-gradient(135deg, var(--c-navy) 0%, var(--c-navy-light) 100%)',
  }}>
    <div style={{
      maxWidth: 900,
      margin: '0 auto',
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: 0,
      textAlign: 'center',
    }}>
      {[
        { value: '12.400+', labelKey: 'heroStat1' },
        { value: '3.200+',  labelKey: 'heroStat2' },
        { value: '24.3%',   labelKey: 'heroStat3' },
      ].map((s, i) => (
        <div key={i} style={{
          padding: '32px 24px',
          borderRight: i < 2 ? '1px solid rgba(255,255,255,.1)' : 'none',
        }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(2rem, 4vw, 3rem)',
            fontWeight: 700,
            color: '#fff',
            marginBottom: 8,
          }}>
            {s.value}
          </div>
          <div style={{ fontSize: '0.88rem', color: 'rgba(255,255,255,.55)', letterSpacing: '.04em' }}>
            {t(lang, s.labelKey as any)}
          </div>
        </div>
      ))}
    </div>
  </section>
);

/* ── CTA ── */
const CtaSection: React.FC<{ lang: Lang; onNavigate: (v: View) => void }> = ({ lang, onNavigate }) => (
  <section style={{
    padding: 'var(--space-3xl) 24px',
    textAlign: 'center',
    background: 'var(--bg-page)',
  }}>
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(1.8rem, 3.5vw, 2.6rem)',
        color: 'var(--text-navy)',
        marginBottom: 20,
      }}>
        {t(lang, 'ctaSection')}
      </h2>
      <Button variant="primary" size="lg" onClick={() => onNavigate('register')}>
        {t(lang, 'ctaButton')} →
      </Button>
    </div>
  </section>
);

/* ── Footer ── */
const Footer: React.FC<{ lang: Lang; onNavigate: (v: View) => void }> = ({ lang, onNavigate }) => (
  <footer style={{
    padding: '32px 24px',
    borderTop: '1px solid var(--border)',
    background: 'var(--bg-white)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 16,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        width: 28, height: 28,
        background: 'linear-gradient(135deg, var(--c-navy), var(--c-blue))',
        borderRadius: 7,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14,
      }}>⬡</div>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--text-navy)', fontSize: '0.9rem' }}>
        Big House AI
      </span>
    </div>
    <div style={{ display: 'flex', gap: 20 }}>
      {['landing', 'pricing'].map((v) => (
        <button
          key={v}
          onClick={() => onNavigate(v as View)}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '0.82rem', color: 'var(--text-muted)',
            fontFamily: 'var(--font-body)',
          }}
        >
          {v === 'pricing' ? t(lang, 'navPricing') : 'Home'}
        </button>
      ))}
    </div>
    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
      © {new Date().getFullYear()} Big House AI. All rights reserved.
    </p>
  </footer>
);

/* ── Floating decorative shapes ── */
const FloatingShape: React.FC<{
  size: number; x: string; y: string; opacity: number; delay: number;
}> = ({ size, x, y, opacity, delay }) => (
  <div style={{
    position: 'absolute',
    width: size,
    height: size,
    left: x,
    top: y,
    background: `radial-gradient(ellipse, rgba(37,99,235,${opacity}) 0%, transparent 70%)`,
    borderRadius: '50%',
    pointerEvents: 'none',
    animation: `pulse ${4 + delay}s ${delay}s ease-in-out infinite`,
  }} />
);
