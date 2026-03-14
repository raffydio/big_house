// ─────────────────────────────────────────
// src/pages/AuthPage.tsx
// ─────────────────────────────────────────

import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { Lang, AuthMode } from '../types';
import type { UseAuth } from '../hooks/useAuth';
import { t } from '../i18n/translations';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { TermsModal } from '../components/TermsModal';

interface AuthPageProps {
  lang: Lang;
  mode: AuthMode;
  onModeChange: (mode: AuthMode) => void;
  auth: UseAuth;
  onSuccess: () => void;
  onLangChange?: (lang: Lang) => void;
}

interface FormState  { email: string; password: string; name: string; }
interface FormErrors { email?: string; password?: string; name?: string; }

export const AuthPage: React.FC<AuthPageProps> = ({
  lang, mode, onModeChange, auth, onSuccess, onLangChange,
}) => {
  const [form, setForm]               = useState<FormState>({ email: '', password: '', name: '' });
  const [errors, setErrors]           = useState<FormErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [googleError, setGoogleError] = useState<string | null>(null);

  // 'form' | 'google' | null
  const [termsModalOpen, setTermsModalOpen]           = useState<'form' | 'google' | null>(null);
  const [pendingGoogleCredential, setPendingGCredential] = useState<string | null>(null);

  const isLogin = mode === 'login';

  // ── Validazione form ──
  const validate = (): boolean => {
    const e: FormErrors = {};
    if (!form.email)   e.email = t(lang, 'errorRequired');
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = t(lang, 'errorEmailFormat');
    if (!form.password) e.password = t(lang, 'errorRequired');
    else if (form.password.length < 8) e.password = t(lang, 'errorPasswordLength');
    if (!isLogin && !form.name) e.name = t(lang, 'errorRequired');
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // ── Accettazione T&C ──
  const handleTermsAccept = async (chosenLang: Lang) => {
    setTermsModalOpen(null);
    if (onLangChange) onLangChange(chosenLang);

    if (termsModalOpen === 'google' && pendingGoogleCredential) {
      const ok = await auth.loginWithGoogle(pendingGoogleCredential);
      setPendingGCredential(null);
      if (ok) onSuccess();
      return;
    }

    auth.clearError();
    const ok = await auth.register({ email: form.email, password: form.password, name: form.name });
    if (ok) onSuccess();
  };

  // ── Submit form ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    auth.clearError();
    if (!validate()) return;

    if (isLogin) {
      const ok = await auth.login({ email: form.email, password: form.password });
      if (ok) onSuccess();
      return;
    }
    setTermsModalOpen('form');
  };

  // ── Google OAuth success ──
  const handleGoogleSuccess = async (credential: string) => {
    setGoogleError(null);
    if (isLogin) {
      // Login: diretto, senza T&C
      const ok = await auth.loginWithGoogle(credential);
      if (ok) onSuccess();
      return;
    }
    // Registrazione: T&C prima
    setPendingGCredential(credential);
    setTermsModalOpen('google');
  };

  const update = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(f => ({ ...f, [field]: e.target.value }));
    setErrors(er => ({ ...er, [field]: undefined }));
  };

  return (
  <>
    <div style={{
      minHeight: '100vh', display: 'flex',
      background: `radial-gradient(ellipse 70% 60% at 30% 20%, rgba(37,99,235,.08) 0%, transparent 70%), var(--bg-page)`,
    }}>

      {/* ── Left panel visual (solo desktop) ── */}
      <div
        style={{
          flex: 1,
          background: 'linear-gradient(160deg, var(--c-navy) 0%, var(--c-navy-light) 60%, #1d4ed8 100%)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          padding: 48, position: 'relative', overflow: 'hidden',
        }}
        className="auth-visual"
      >
        <style>{`@media (max-width: 768px) { .auth-visual { display: none !important; } }`}</style>
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{
            position: 'absolute', width: 80 + i * 30, height: 80 + i * 30,
            border: `1px solid rgba(255,255,255,${0.03 + i * 0.01})`, borderRadius: '20%',
            top: `${10 + i * 12}%`, left: `${5 + i * 8}%`,
            transform: `rotate(${i * 15}deg)`, pointerEvents: 'none',
          }} />
        ))}
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 380 }}>
          <div style={{
            width: 60, height: 60, background: 'rgba(255,255,255,.1)', borderRadius: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
            margin: '0 auto 24px', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,.15)',
          }}>⬡</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2.2rem', color: '#fff', marginBottom: 16, fontStyle: 'italic' }}>
            Big House AI
          </h2>
          <p style={{ color: 'rgba(255,255,255,.65)', lineHeight: 1.7, fontSize: '1rem' }}>
            {t(lang, 'heroSubtitle')}
          </p>
          <div style={{
            marginTop: 48, background: 'rgba(255,255,255,.06)', border: '1px solid rgba(255,255,255,.1)',
            borderRadius: 'var(--r-lg)', padding: 24, backdropFilter: 'blur(8px)',
          }}>
            <p style={{ color: 'rgba(255,255,255,.8)', fontSize: '0.92rem', lineHeight: 1.7, fontStyle: 'italic', marginBottom: 14 }}>
              "Ho analizzato 8 proprietà in un pomeriggio con Big House AI. Il ROI reale era esattamente quello previsto."
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, color: 'var(--c-navy-dark)', fontSize: '0.9rem',
              }}>M</div>
              <div>
                <div style={{ color: '#fff', fontSize: '0.82rem', fontWeight: 600 }}>Marco R.</div>
                <div style={{ color: 'rgba(255,255,255,.45)', fontSize: '0.75rem' }}>Investitore • Milano</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right panel form ── */}
      <div style={{
        flex: '0 0 min(480px, 100%)', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', padding: 'clamp(24px, 5vw, 48px)',
      }}>
        <div style={{ width: '100%', maxWidth: 400, animation: 'fadeIn .5s ease both' }}>

          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--text-navy)', marginBottom: 8 }}>
              {t(lang, isLogin ? 'loginTitle' : 'registerTitle')}
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.93rem' }}>
              {t(lang, isLogin ? 'loginSubtitle' : 'registerSubtitle')}
            </p>
          </div>

          {/* ── GOOGLE LOGIN REALE ── */}
          <div style={{ marginBottom: 8 }}>
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                if (credentialResponse.credential) {
                  handleGoogleSuccess(credentialResponse.credential);
                }
              }}
              onError={() => setGoogleError('Accesso con Google non riuscito. Riprova.')}
              width="400"
              text={isLogin ? 'signin_with' : 'signup_with'}
              shape="rectangular"
              theme="outline"
              locale="it"
            />
          </div>
          {googleError && (
            <p style={{ marginBottom: 12, fontSize: '0.82rem', color: 'var(--c-red)', textAlign: 'center' }}>
              {googleError}
            </p>
          )}

          {/* Divider */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, marginTop: 12,
            color: 'var(--text-muted)', fontSize: '0.8rem',
          }}>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
            {t(lang, 'orContinueWith')}
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {!isLogin && (
                <Input label={t(lang, 'nameLabel')} type="text" placeholder={t(lang, 'namePlaceholder')}
                  value={form.name} onChange={update('name')} error={errors.name} autoComplete="name" />
              )}
              <Input label={t(lang, 'emailLabel')} type="email" placeholder={t(lang, 'emailPlaceholder')}
                value={form.email} onChange={update('email')} error={errors.email} autoComplete="email" />
              <div style={{ position: 'relative' }}>
                <Input label={t(lang, 'passwordLabel')} type={showPassword ? 'text' : 'password'}
                  placeholder={t(lang, 'passwordPlaceholder')} value={form.password}
                  onChange={update('password')} error={errors.password}
                  autoComplete={isLogin ? 'current-password' : 'new-password'} />
                <button type="button" onClick={() => setShowPassword(s => !s)} style={{
                  position: 'absolute', right: 12, bottom: errors.password ? 28 : 10,
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-muted)', fontSize: 14, padding: 2,
                }}>
                  {showPassword ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            {auth.error && (
              <div style={{
                marginTop: 14, padding: '10px 14px',
                background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)',
                borderRadius: 'var(--r-md)', fontSize: '0.85rem', color: 'var(--c-red)',
              }}>
                {t(lang, auth.error as any) || auth.error}
              </div>
            )}

            {isLogin && (
              <div style={{ textAlign: 'right', marginTop: 8 }}>
                <button type="button" style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: '0.8rem', color: 'var(--c-blue)', fontFamily: 'var(--font-body)',
                }}>
                  {t(lang, 'forgotPassword')}
                </button>
              </div>
            )}

            <Button variant="primary" size="lg" fullWidth type="submit"
              loading={auth.loading} style={{ marginTop: 22 }}>
              {t(lang, isLogin ? 'loginBtn' : 'registerBtn')}
            </Button>
          </form>

          {/* Switch mode */}
          <p style={{ textAlign: 'center', marginTop: 24, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <button onClick={() => {
              onModeChange(isLogin ? 'register' : 'login');
              auth.clearError();
              setErrors({});
              setForm({ email: '', password: '', name: '' });
              setGoogleError(null);
            }} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--c-blue)', fontWeight: 600, fontSize: '0.85rem',
              fontFamily: 'var(--font-body)',
            }}>
              {t(lang, isLogin ? 'switchToRegister' : 'switchToLogin')}
            </button>
          </p>

          {!isLogin && (
            <p style={{ marginTop: 16, fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.5 }}>
              {t(lang, 'termsNote')}
            </p>
          )}
        </div>
      </div>
    </div>

    {termsModalOpen && (
      <TermsModal
        currentLang={lang}
        onAccept={handleTermsAccept}
        onClose={() => { setTermsModalOpen(null); setPendingGCredential(null); }}
      />
    )}
  </>
  );
};
