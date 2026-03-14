// src/App.tsx
// FIX navigate: legge localStorage (sincrono) invece di auth.token (React state asincrono)
// Quando loginWithGoogle chiama onSuccess() → navigate('dashboard'), lo state auth.token
// potrebbe non essere ancora aggiornato. localStorage.setItem avviene prima, quindi è affidabile.

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

  // ── CORE FIX ──────────────────────────────────────────────────────────────
  // navigate NON dipende da auth.token (React state).
  // Dipende da localStorage.getItem(TOKEN_KEY) che è sincrono e viene scritto
  // PRIMA che onSuccess() venga chiamato in useAuth._handleToken().
  // Questo risolve il problema del redirect che non avveniva dopo Google login.
  // ──────────────────────────────────────────────────────────────────────────
  const navigate = useCallback((target: View) => {
    const hasToken = !!localStorage.getItem(TOKEN_KEY);
    if (DASHBOARD_VIEWS.includes(target) && !hasToken) {
      setAuthMode('login');
      setView('login');
      return;
    }
    setView(target);
    setSidebarOpen(false);
  }, []); // nessuna dipendenza: legge localStorage live ogni chiamata

  useEffect(() => { auth.fetchUser(); }, []);

  useEffect(() => {
    if (auth.user) {
      authGet<UserLimits>('/users/me/limits').then((d) => { if (d) setLimits(d); });
      storage.fetchSessions();
      storage.fetchStorageInfo();
    }
  }, [auth.user?.id]);

  // Kick-out se token sparisce (logout)
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

  // isDashboard: localStorage (sincrono) + view è una dashboard view
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
              {view === 'reports' && <ReportsPlaceholder lang={lang} onNavigate={navigate} />}
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

const ReportsPlaceholder: React.FC<{ lang: Lang; onNavigate: (v: View) => void }> = ({ onNavigate }) => (
  <div style={{
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', minHeight: '60vh', padding: 32, gap: 16, textAlign: 'center',
  }}>
    <div style={{ fontSize: 48, opacity: 0.3 }}>▣</div>
    <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--text-navy)' }}>
      Report Export PDF
    </h2>
    <p style={{ color: 'var(--text-muted)', maxWidth: 360 }}>
      Esporta i tuoi report in PDF con analisi completa.<br />
      <em>I report .docx sono già disponibili nella chat di ogni sessione.</em>
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

export default App;