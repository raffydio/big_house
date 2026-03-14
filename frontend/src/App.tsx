// src/App.tsx
// FIX navigate: legge localStorage (sincrono) invece di auth.token (React state asincrono)
// FIX ReportsPlaceholder: mostra contenuto corretto per PRO/PLUS, upgrade solo per FREE/BASIC

import React, { useState, useEffect, useCallback } from 'react';
import type { Lang, View, AuthMode, Plan, UserLimits } from './types';
import { useAuth } from './hooks/useAuth';
import { useStorage } from './hooks/useStorage';
import { authGet } from './hooks/useApi';

import { Navbar }       from './components/Navbar';
import { Sidebar }      from './components/Sidebar';
import { TopBar }       from './components/TopBar';
import { UpgradeModal } from './components/UpgradeModal';

import { LandingPage }  from './pages/LandingPage';
import { AuthPage }     from './pages/AuthPage';
import PricingPage      from './pages/PricingPage';
import { Dashboard }    from './pages/Dashboard';
import { DeepResearchPage } from './pages/dashboard/DeepResearch';
import { CalcROIPage }      from './pages/dashboard/CalcROI';
import { HistoryPage }      from './pages/dashboard/History';
import { StoragePage }      from './pages/dashboard/StoragePage';
import PaymentSuccess   from './pages/PaymentSuccess';

import './styles/globals.css';

const TOKEN_KEY = 'bh_token';
type Feature = 'deepresearch' | 'calcola';

const DASHBOARD_VIEWS: View[] = [
  'dashboard', 'deepresearch', 'calcola', 'reports', 'history', 'storage',
];

const App: React.FC = () => {
  const [lang, setLang] = useState<Lang>(() => {
    const s = localStorage.getItem('bh_lang') as Lang | null;
    return s ?? (navigator.language.startsWith('it') ? 'it' : 'en');
  });
  const [view, setView]               = useState<View>('landing');
  const [authMode, setAuthMode]       = useState<AuthMode>('login');
  const [collapsed, setCollapsed]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [limits, setLimits]           = useState<UserLimits | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [upgradeFeature, setUpgradeFeature] = useState<Feature>('deepresearch');

  const auth    = useAuth();
  const storage = useStorage();

  const handleLangChange = (l: Lang) => {
    setLang(l);
    localStorage.setItem('bh_lang', l);
  };

  const navigate = useCallback((target: View) => {
    const hasToken = !!localStorage.getItem(TOKEN_KEY);
    if (DASHBOARD_VIEWS.includes(target) && !hasToken) {
      setAuthMode('login');
      setView('login');
      return;
    }
    setView(target);
    setSidebarOpen(false);
  }, []);

  useEffect(() => { auth.fetchUser(); }, []);

  useEffect(() => {
    if (auth.user) {
      authGet<UserLimits>('/users/me/limits').then((d) => { if (d) setLimits(d); });
      storage.fetchSessions();
      storage.fetchStorageInfo();
    }
  }, [auth.user?.id]);

  useEffect(() => {
    if (!auth.token && DASHBOARD_VIEWS.includes(view)) setView('landing');
  }, [auth.token]);

  const handleLogout = () => {
    auth.logout();
    setView('landing');
    setLimits(null);
  };

  const handlePlanUpgrade = (_plan: Plan) => { auth.fetchUser(); };

  const handleLimitReached = (feature: Feature = 'deepresearch') => {
    setUpgradeFeature(feature);
    setUpgradeOpen(true);
  };

  const handleUsageIncrement = (feature: Feature = 'deepresearch') => {
    setLimits((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        usage_today: { ...prev.usage_today, [feature]: (prev.usage_today[feature] ?? 0) + 1 },
        remaining:   { ...prev.remaining,   [feature]: Math.max(0, (prev.remaining[feature] ?? 0) - 1) },
      };
    });
  };

  if (view === 'payment-success') {
    return <PaymentSuccess onNavigate={navigate} />;
  }

  const isDashboard = !!localStorage.getItem(TOKEN_KEY) && DASHBOARD_VIEWS.includes(view);

  return (
    <>
      {!isDashboard && (
        <>
          <Navbar lang={lang} onLangChange={handleLangChange}
            onNavigate={navigate} user={auth.user} onLogout={handleLogout} />
          {view === 'landing' && <LandingPage lang={lang} onNavigate={navigate} />}
          {(view === 'login' || view === 'register') && (
            <AuthPage lang={lang} mode={authMode} onModeChange={setAuthMode}
              auth={auth} onSuccess={() => navigate('dashboard')} />
          )}
          {view === 'pricing' && (
            <PricingPage lang={lang} user={auth.user}
              onNavigate={navigate} onPlanUpgrade={handlePlanUpgrade} />
          )}
        </>
      )}

      {isDashboard && (
        <div className="dashboard-layout">
          {sidebarOpen && (
            <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
          )}
          <div className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''} ${sidebarOpen ? 'sidebar--open' : ''}`}>
            <Sidebar lang={lang} onLangChange={handleLangChange}
              currentView={view} onNavigate={navigate}
              onLogout={handleLogout} user={auth.user}
              collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)} />
          </div>
          <div className="dashboard-main">
            <TopBar lang={lang} onLangChange={handleLangChange}
              currentView={view} user={auth.user}
              limits={limits} storageInfo={storage.storageInfo}
              onNavigate={navigate}
              onMenuToggle={() => setSidebarOpen((o) => !o)} />
            <main className="dashboard-content">
              {view === 'dashboard' && (
                <Dashboard lang={lang} user={auth.user}
                  onNavigate={navigate} limits={limits} onLimitsLoaded={setLimits} />
              )}
              {view === 'deepresearch' && (
                <DeepResearchPage lang={lang} user={auth.user}
                  onLimitReached={() => handleLimitReached('deepresearch')}
                  onUsageIncrement={() => handleUsageIncrement('deepresearch')}
                  onSaveSession={storage.saveSession}
                  remaining={limits?.remaining?.deepresearch} />
              )}
              {view === 'calcola' && (
                <CalcROIPage lang={lang} user={auth.user}
                  onLimitReached={() => handleLimitReached('calcola')}
                  onUsageIncrement={() => handleUsageIncrement('calcola')}
                  onSaveSession={storage.saveSession} />
              )}
              {view === 'history' && (
                <HistoryPage lang={lang} sessions={storage.sessions}
                  onDeleteSession={storage.deleteSession} onNavigate={navigate} />
              )}
              {view === 'storage' && (
                <StoragePage lang={lang} user={auth.user}
                  storageInfo={storage.storageInfo} sessions={storage.sessions}
                  loadingStorage={storage.loading} onFetchStorage={storage.fetchStorageInfo}
                  onDownloadZip={storage.downloadZip} onDeleteSession={storage.deleteSession} />
              )}
              {view === 'reports' && (
                <ReportsPage
                  lang={lang}
                  userPlan={auth.user?.plan ?? 'free'}
                  sessions={storage.sessions}
                  onNavigate={navigate}
                />
              )}
            </main>
          </div>
        </div>
      )}

      <UpgradeModal isOpen={upgradeOpen} onClose={() => setUpgradeOpen(false)}
        onViewPlans={() => { setUpgradeOpen(false); navigate('pricing'); }}
        lang={lang} feature={upgradeFeature} />
    </>
  );
};

// ── Reports Page — mostra contenuto corretto per ogni piano ──────────────────
import type { ChatSession } from './types';
import { generateDocx } from './hooks/useStorage';

const ReportsPage: React.FC<{
  lang: Lang;
  userPlan: Plan;
  sessions: ChatSession[];
  onNavigate: (v: View) => void;
}> = ({ userPlan, sessions, onNavigate }) => {
  const isPaidPlan = userPlan === 'pro' || userPlan === 'plus';
  const [downloading, setDownloading] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  // Sessioni che hanno contenuto AI
  const exportableSessions = sessions.filter(
    (s) => s.messages.some((m) => m.role === 'assistant' && m.content.length > 50)
  );

  const handleExport = async (session: ChatSession) => {
    setDownloading(session.id);
    setSuccess(null);
    try {
      const userMsg = session.messages.find((m) => m.role === 'user');
      const aiMsg   = session.messages.find((m) => m.role === 'assistant');
      if (!aiMsg) return;

      const featureLabel = session.feature === 'deepresearch' ? 'Deep Research' : 'Calcola ROI';
      const date = new Date(session.created_at).toLocaleDateString('it-IT', {
        day: '2-digit', month: 'long', year: 'numeric',
      });

      await generateDocx(`${featureLabel} — ${session.title || 'Report'}`, [
        { heading: 'Informazioni Report',  content: `Feature: ${featureLabel}\nData: ${date}\nPiano: ${userPlan.toUpperCase()}` },
        { heading: 'Query',               content: userMsg?.content ?? '—' },
        { heading: 'Analisi AI',          content: aiMsg.content },
      ]);
      setSuccess(session.id);
      setTimeout(() => setSuccess(null), 3000);
    } finally {
      setDownloading(null);
    }
  };

  // Utenti FREE o BASIC → mostra upgrade
  if (!isPaidPlan) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '60vh', padding: 32, gap: 16, textAlign: 'center',
      }}>
        <div style={{ fontSize: 48, opacity: 0.3 }}>▣</div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--text-navy)' }}>
          Report Export DOCX
        </h2>
        <p style={{ color: 'var(--text-muted)', maxWidth: 360 }}>
          Esporta i tuoi report in formato .docx con analisi completa.<br />
          Disponibile dal piano <strong>PRO</strong> in su.
        </p>
        <button onClick={() => onNavigate('pricing')} style={{
          padding: '10px 24px',
          background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
          border: 'none', borderRadius: 'var(--r-md)', cursor: 'pointer',
          fontWeight: 700, color: 'var(--c-navy-dark)', fontFamily: 'var(--font-body)', fontSize: '0.9rem',
        }}>
          ⚡ Upgrade a PRO
        </button>
      </div>
    );
  }

  // PRO o PLUS → mostra la lista sessioni esportabili
  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 860, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(1.4rem, 3vw, 2rem)',
          color: 'var(--text-navy)', marginBottom: 6,
        }}>
          Report Export DOCX
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Esporta le tue sessioni in formato Word (.docx) — piano {userPlan.toUpperCase()} attivo ✓
        </p>
      </div>

      {exportableSessions.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          padding: '60px 24px', gap: 14, textAlign: 'center',
        }}>
          <span style={{ fontSize: 40, opacity: .25 }}>▣</span>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Nessuna sessione da esportare ancora.<br />
            Avvia una Deep Research o un Calcolo ROI per generare i tuoi report.
          </p>
          <button
            onClick={() => onNavigate('deepresearch')}
            style={{
              padding: '10px 22px',
              background: 'var(--c-blue)', color: '#fff',
              border: 'none', borderRadius: 'var(--r-md)',
              cursor: 'pointer', fontWeight: 700,
              fontFamily: 'var(--font-body)', fontSize: '0.88rem',
            }}
          >
            Avvia Deep Research →
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Info banner */}
          <div style={{
            padding: '12px 16px',
            background: 'rgba(16,185,129,.06)',
            border: '1px solid rgba(16,185,129,.2)',
            borderRadius: 'var(--r-md)',
            fontSize: '0.82rem',
            color: '#065f46',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span>✓</span>
            <span>
              {exportableSessions.length} sessione{exportableSessions.length !== 1 ? 'i' : ''} disponibil{exportableSessions.length !== 1 ? 'i' : 'e'} per l'export.
              Il file .docx viene scaricato direttamente nel tuo browser.
            </span>
          </div>

          {exportableSessions.map((session) => {
            const aiMsg   = session.messages.find((m) => m.role === 'assistant');
            const date    = new Date(session.created_at).toLocaleDateString('it-IT', {
              day: '2-digit', month: 'short', year: 'numeric',
            });
            const color   = session.feature === 'deepresearch' ? 'var(--c-blue)' : 'var(--c-green)';
            const icon    = session.feature === 'deepresearch' ? '⬡' : '◎';
            const label   = session.feature === 'deepresearch' ? 'Deep Research' : 'Calcola ROI';
            const isDl    = downloading === session.id;
            const isDone  = success === session.id;

            return (
              <div key={session.id} style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '16px 18px',
                background: 'var(--bg-white)',
                border: `1px solid ${isDone ? 'rgba(16,185,129,.3)' : 'var(--border)'}`,
                borderRadius: 'var(--r-lg)',
                boxShadow: 'var(--shadow-sm)',
                transition: 'border-color .2s',
              }}>
                {/* Feature icon */}
                <div style={{
                  width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                  background: `${color}12`,
                  border: `1px solid ${color}25`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 16, color,
                }}>
                  {icon}
                </div>

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-navy)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {session.title || 'Report senza titolo'}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 3 }}>
                    {label} · {date} ·{' '}
                    {aiMsg ? `${Math.round(aiMsg.content.length / 5)} parole` : '—'}
                  </div>
                </div>

                {/* Download button */}
                <button
                  onClick={() => handleExport(session)}
                  disabled={isDl}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 16px',
                    background: isDone
                      ? 'rgba(16,185,129,.1)'
                      : 'rgba(37,99,235,.08)',
                    border: `1px solid ${isDone ? 'rgba(16,185,129,.25)' : 'rgba(37,99,235,.2)'}`,
                    borderRadius: 'var(--r-md)',
                    cursor: isDl ? 'not-allowed' : 'pointer',
                    fontSize: '0.8rem', fontWeight: 700,
                    color: isDone ? '#065f46' : 'var(--c-blue)',
                    fontFamily: 'var(--font-body)',
                    flexShrink: 0,
                    opacity: isDl ? 0.7 : 1,
                    transition: 'all .2s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {isDl
                    ? <><span className="spinner spinner--dark" style={{ width: 13, height: 13 }} /> Generando…</>
                    : isDone
                      ? <>✓ Scaricato</>
                      : <>📄 Scarica .docx</>
                  }
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default App;