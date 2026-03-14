// ─────────────────────────────────────────
// src/components/TermsModal.tsx
// Modal accettazione T&C con selettore lingua
// Si apre prima di qualsiasi flusso di registrazione
// ─────────────────────────────────────────

import React, { useState } from 'react';
import type { Lang } from '../types';

interface TermsModalProps {
  currentLang: Lang;
  onAccept: (lang: Lang) => void;  // utente accetta → procede con la lingua scelta
  onClose: () => void;              // utente chiude senza accettare
}

// ── Configurazione lingue ──────────────────
const LANGS: { code: Lang; flag: string; label: string; nativeName: string }[] = [
  { code: 'it', flag: '🇮🇹', label: 'Italiano',   nativeName: 'Italiano' },
  { code: 'en', flag: '🇬🇧', label: 'English',    nativeName: 'English' },
  { code: 'fr', flag: '🇫🇷', label: 'Français',   nativeName: 'Français' },
  { code: 'de', flag: '🇩🇪', label: 'Deutsch',    nativeName: 'Deutsch' },
  { code: 'es', flag: '🇪🇸', label: 'Español',    nativeName: 'Español' },
  { code: 'pt', flag: '🇵🇹', label: 'Português',  nativeName: 'Português' },
];

// ── Testi UI per lingua ────────────────────
const UI: Record<Lang, {
  selectLang: string;
  title: string;
  subtitle: string;
  checkboxLabel: string;
  privacyLink: string;
  termsLink: string;
  acceptBtn: string;
  cancelBtn: string;
  mustAccept: string;
  poweredBy: string;
}> = {
  it: {
    selectLang: 'Seleziona la tua lingua',
    title: 'Prima di continuare',
    subtitle: 'Leggi e accetta i nostri documenti legali per creare il tuo account.',
    checkboxLabel: 'Ho letto e accetto i',
    privacyLink: 'Termini di Servizio',
    termsLink: 'e la Privacy Policy',
    acceptBtn: 'Accetto e continuo',
    cancelBtn: 'Annulla',
    mustAccept: 'Devi accettare i termini per continuare.',
    poweredBy: 'AI conforme a Reg. UE 2024/1689 (AI Act) · Legge 132/2025',
  },
  en: {
    selectLang: 'Select your language',
    title: 'Before continuing',
    subtitle: 'Read and accept our legal documents to create your account.',
    checkboxLabel: 'I have read and accept the',
    privacyLink: 'Terms of Service',
    termsLink: 'and Privacy Policy',
    acceptBtn: 'Accept and continue',
    cancelBtn: 'Cancel',
    mustAccept: 'You must accept the terms to continue.',
    poweredBy: 'AI compliant with EU Reg. 2024/1689 (AI Act)',
  },
  fr: {
    selectLang: 'Sélectionnez votre langue',
    title: 'Avant de continuer',
    subtitle: 'Lisez et acceptez nos documents légaux pour créer votre compte.',
    checkboxLabel: 'J\'ai lu et j\'accepte les',
    privacyLink: 'Conditions d\'Utilisation',
    termsLink: 'et la Politique de Confidentialité',
    acceptBtn: 'Accepter et continuer',
    cancelBtn: 'Annuler',
    mustAccept: 'Vous devez accepter les conditions pour continuer.',
    poweredBy: 'IA conforme au Règl. UE 2024/1689 (Loi IA)',
  },
  de: {
    selectLang: 'Sprache auswählen',
    title: 'Bevor Sie fortfahren',
    subtitle: 'Lesen und akzeptieren Sie unsere rechtlichen Dokumente, um ein Konto zu erstellen.',
    checkboxLabel: 'Ich habe gelesen und akzeptiere die',
    privacyLink: 'Nutzungsbedingungen',
    termsLink: 'und Datenschutzrichtlinie',
    acceptBtn: 'Akzeptieren und fortfahren',
    cancelBtn: 'Abbrechen',
    mustAccept: 'Sie müssen die Bedingungen akzeptieren, um fortzufahren.',
    poweredBy: 'KI konform mit EU-Verordnung 2024/1689 (KI-Gesetz)',
  },
  es: {
    selectLang: 'Selecciona tu idioma',
    title: 'Antes de continuar',
    subtitle: 'Lee y acepta nuestros documentos legales para crear tu cuenta.',
    checkboxLabel: 'He leído y acepto los',
    privacyLink: 'Términos de Servicio',
    termsLink: 'y la Política de Privacidad',
    acceptBtn: 'Aceptar y continuar',
    cancelBtn: 'Cancelar',
    mustAccept: 'Debes aceptar los términos para continuar.',
    poweredBy: 'IA conforme al Regl. UE 2024/1689 (Ley de IA)',
  },
  pt: {
    selectLang: 'Selecione o seu idioma',
    title: 'Antes de continuar',
    subtitle: 'Leia e aceite os nossos documentos legais para criar a sua conta.',
    checkboxLabel: 'Li e aceito os',
    privacyLink: 'Termos de Serviço',
    termsLink: 'e a Política de Privacidade',
    acceptBtn: 'Aceitar e continuar',
    cancelBtn: 'Cancelar',
    mustAccept: 'Deve aceitar os termos para continuar.',
    poweredBy: 'IA conforme ao Reg. UE 2024/1689 (Lei de IA)',
  },
};

// ── Testo T&C per lingua (versione modal compatta) ──
const TERMS_TEXT: Record<Lang, string> = {
  it: `TERMINI DI SERVIZIO — RIEPILOGO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI è una piattaforma SaaS per l'analisi professionale di investimenti immobiliari.

📋 UTILIZZO CONSENTITO
Il servizio è esclusivamente per analisi e calcoli ROI nel settore immobiliare. Qualsiasi uso fuori da questo ambito è vietato e comporta la sospensione immediata dell'account.

💳 PIANI E PREZZI
• Free: gratuito — 1 Deep Research + 3 Calcola ROI al giorno
• PRO: €29/mese o €22/mese annuale (sconto 25%)
• PLUS: €79/mese o €59/mese annuale (sconto 25%)
I consumatori B2C hanno diritto di recesso entro 14 giorni.

🤖 INTELLIGENZA ARTIFICIALE
I risultati generati dalla piattaforma sono prodotti da modelli AI di terze parti:
• Piano Free: Google Gemini Flash 2.0 — server Google Cloud Europa
• Piani PRO/PLUS: Anthropic Claude — server AWS Francoforte (EU)

⚠️ LIMITAZIONE DI RESPONSABILITÀ
I risultati hanno finalità ESCLUSIVAMENTE informativa. Non costituiscono consulenza finanziaria, immobiliare, legale o fiscale. L'utente è responsabile delle proprie decisioni di investimento. Verifica sempre con un professionista qualificato.

🔒 PRIVACY E DATI
I tuoi dati sono trattati in conformità al GDPR (Reg. UE 2016/679). I dati vengono processati da server situati in Europa. Non usiamo i tuoi dati per addestrare i modelli AI. Hai il diritto di accesso, rettifica, cancellazione e portabilità dei tuoi dati.

📧 Contatto: legal@bighouse.ai
🌐 Conforme a: AI Act UE 2024/1689 · Legge italiana 132/2025`,

  en: `TERMS OF SERVICE — SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI is a SaaS platform for professional real estate investment analysis.

📋 PERMITTED USE
The service is exclusively for real estate analysis and ROI calculations. Any use outside this scope is prohibited and will result in immediate account suspension.

💳 PLANS & PRICING
• Free: free — 1 Deep Research + 3 ROI Calculations per day
• PRO: €29/month or €22/month annual (25% discount)
• PLUS: €79/month or €59/month annual (25% discount)
B2C consumers have a 14-day withdrawal right.

🤖 ARTIFICIAL INTELLIGENCE
Results are generated by third-party AI models:
• Free Plan: Google Gemini Flash 2.0 — Google Cloud Europe servers
• PRO/PLUS Plans: Anthropic Claude — AWS Frankfurt servers (EU)

⚠️ LIABILITY LIMITATION
Results are for INFORMATIONAL PURPOSES ONLY. They do not constitute financial, real estate, legal or tax advice. Always verify with a qualified professional before investing.

🔒 PRIVACY & DATA
Your data is processed in compliance with GDPR (EU Reg. 2016/679). Data is processed on European servers. We never use your data to train AI models.

📧 Contact: legal@bighouse.ai
🌐 Compliant with: EU AI Act 2024/1689`,

  fr: `CONDITIONS D'UTILISATION — RÉSUMÉ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI est une plateforme SaaS pour l'analyse professionnelle d'investissements immobiliers.

📋 UTILISATION AUTORISÉE
Le service est exclusivement pour l'analyse immobilière et les calculs de ROI.

💳 PLANS ET TARIFS
• Free: gratuit — 1 Deep Research + 3 calculs ROI par jour
• PRO: €29/mois ou €22/mois annuel (remise 25%)
• PLUS: €79/mois ou €59/mois annuel (remise 25%)
Droit de rétractation de 14 jours pour les consommateurs B2C.

🤖 INTELLIGENCE ARTIFICIELLE
• Plan Free: Google Gemini Flash 2.0 — serveurs Google Cloud Europe
• Plans PRO/PLUS: Anthropic Claude — serveurs AWS Frankfurt (UE)

⚠️ Les résultats sont EXCLUSIVEMENT informatifs. Vérifiez toujours avec un professionnel qualifié.

🔒 Données traitées en conformité RGPD sur des serveurs européens.
📧 Contact: legal@bighouse.ai`,

  de: `NUTZUNGSBEDINGUNGEN — ZUSAMMENFASSUNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI ist eine SaaS-Plattform für professionelle Immobilieninvestitionsanalysen.

📋 ERLAUBTE NUTZUNG
Der Dienst ist ausschließlich für Immobilienanalyse und ROI-Berechnungen bestimmt.

💳 PLÄNE UND PREISE
• Free: kostenlos — 1 Deep Research + 3 ROI-Berechnungen pro Tag
• PRO: €29/Monat oder €22/Monat jährlich (25% Rabatt)
• PLUS: €79/Monat oder €59/Monat jährlich (25% Rabatt)
14-tägiges Widerrufsrecht für B2C-Verbraucher.

🤖 KÜNSTLICHE INTELLIGENZ
• Free-Plan: Google Gemini Flash 2.0 — Google Cloud Europa-Server
• PRO/PLUS-Pläne: Anthropic Claude — AWS Frankfurt-Server (EU)

⚠️ Ergebnisse dienen AUSSCHLIESSLICH zu Informationszwecken. Keine Finanz- oder Immobilienberatung.

🔒 Daten werden DSGVO-konform auf europäischen Servern verarbeitet.
📧 Kontakt: legal@bighouse.ai`,

  es: `TÉRMINOS DE SERVICIO — RESUMEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI es una plataforma SaaS para análisis profesional de inversiones inmobiliarias.

📋 USO PERMITIDO
El servicio es exclusivamente para análisis inmobiliario y cálculos de ROI.

💳 PLANES Y PRECIOS
• Free: gratuito — 1 Deep Research + 3 cálculos ROI al día
• PRO: €29/mes o €22/mes anual (descuento 25%)
• PLUS: €79/mes o €59/mes anual (descuento 25%)
Derecho de desistimiento de 14 días para consumidores B2C.

🤖 INTELIGENCIA ARTIFICIAL
• Plan Free: Google Gemini Flash 2.0 — servidores Google Cloud Europa
• Planes PRO/PLUS: Anthropic Claude — servidores AWS Frankfurt (UE)

⚠️ Los resultados son EXCLUSIVAMENTE informativos. No constituyen asesoramiento financiero o inmobiliario.

🔒 Datos procesados conforme al RGPD en servidores europeos.
📧 Contacto: legal@bighouse.ai`,

  pt: `TERMOS DE SERVIÇO — RESUMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Big House AI é uma plataforma SaaS para análise profissional de investimentos imobiliários.

📋 USO PERMITIDO
O serviço destina-se exclusivamente à análise imobiliária e cálculos de ROI.

💳 PLANOS E PREÇOS
• Free: gratuito — 1 Deep Research + 3 cálculos ROI por dia
• PRO: €29/mês ou €22/mês anual (desconto 25%)
• PLUS: €79/mês ou €59/mês anual (desconto 25%)
Direito de arrependimento de 14 dias para consumidores B2C.

🤖 INTELIGÊNCIA ARTIFICIAL
• Plano Free: Google Gemini Flash 2.0 — servidores Google Cloud Europa
• Planos PRO/PLUS: Anthropic Claude — servidores AWS Frankfurt (UE)

⚠️ Os resultados são EXCLUSIVAMENTE informativos. Não constituem aconselhamento financeiro ou imobiliário.

🔒 Dados processados em conformidade com o RGPD em servidores europeus.
📧 Contacto: legal@bighouse.ai`,
};

// ═══════════════════════════════════════════
// COMPONENTE PRINCIPALE
// ═══════════════════════════════════════════
export const TermsModal: React.FC<TermsModalProps> = ({
  currentLang,
  onAccept,
  onClose,
}) => {
  const [selectedLang, setSelectedLang] = useState<Lang>(currentLang);
  const [accepted, setAccepted] = useState(false);
  const [showError, setShowError] = useState(false);
  const [step, setStep] = useState<'lang' | 'terms'>('lang');

  const ui = UI[selectedLang];

  const handleContinueToTerms = () => {
    setStep('terms');
  };

  const handleAccept = () => {
    if (!accepted) {
      setShowError(true);
      return;
    }
    onAccept(selectedLang);
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(10,20,50,.7)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        style={{
          background: 'var(--bg-white)',
          borderRadius: 'var(--r-xl)',
          maxWidth: 540,
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 60px rgba(0,0,0,.35)',
          animation: 'slideInUp .25s ease both',
          overflow: 'hidden',
        }}
      >
        {/* ── STEP 1: Selettore lingua ── */}
        {step === 'lang' && (
          <>
            <ModalHeader
              icon="🌐"
              title={ui.selectLang}
              onClose={onClose}
            />

            <div style={{ padding: '24px', overflowY: 'auto' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 10,
              }}>
                {LANGS.map((l) => (
                  <button
                    key={l.code}
                    onClick={() => setSelectedLang(l.code)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 6,
                      padding: '14px 8px',
                      border: `2px solid ${selectedLang === l.code ? 'var(--c-blue)' : 'var(--border)'}`,
                      borderRadius: 'var(--r-md)',
                      background: selectedLang === l.code
                        ? 'rgba(37,99,235,.06)'
                        : 'var(--bg-white)',
                      cursor: 'pointer',
                      transition: 'all .15s',
                      fontFamily: 'var(--font-body)',
                    }}
                  >
                    <span style={{ fontSize: 24 }}>{l.flag}</span>
                    <span style={{
                      fontSize: '0.78rem',
                      fontWeight: selectedLang === l.code ? 700 : 400,
                      color: selectedLang === l.code ? 'var(--c-blue)' : 'var(--text-secondary)',
                    }}>
                      {l.nativeName}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <ModalFooter>
              <button
                onClick={onClose}
                style={cancelBtnStyle}
              >
                {UI[selectedLang].cancelBtn}
              </button>
              <button
                onClick={handleContinueToTerms}
                style={primaryBtnStyle}
              >
                Continua →
              </button>
            </ModalFooter>
          </>
        )}

        {/* ── STEP 2: Termini e Condizioni ── */}
        {step === 'terms' && (
          <>
            <ModalHeader
              icon="📄"
              title={ui.title}
              subtitle={ui.subtitle}
              onClose={onClose}
              onBack={() => setStep('lang')}
              backLabel={LANGS.find(l => l.code === selectedLang)?.flag}
            />

            {/* T&C text */}
            <div style={{
              overflowY: 'auto',
              padding: '20px 24px',
              flex: 1,
              borderTop: '1px solid var(--border)',
              borderBottom: '1px solid var(--border)',
              background: 'var(--bg-page)',
            }}>
              <pre style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.8rem',
                lineHeight: 1.8,
                color: 'var(--text-secondary)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: 0,
              }}>
                {TERMS_TEXT[selectedLang]}
              </pre>
            </div>

            {/* Checkbox + error */}
            <div style={{ padding: '16px 24px 0' }}>
              <label style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                cursor: 'pointer',
              }}>
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => {
                    setAccepted(e.target.checked);
                    if (e.target.checked) setShowError(false);
                  }}
                  style={{ marginTop: 2, width: 16, height: 16, cursor: 'pointer', accentColor: 'var(--c-blue)' }}
                />
                <span style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {ui.checkboxLabel}{' '}
                  <strong style={{ color: 'var(--c-blue)' }}>{ui.privacyLink}</strong>{' '}
                  {ui.termsLink}
                </span>
              </label>

              {showError && (
                <p style={{
                  margin: '8px 0 0 26px',
                  fontSize: '0.78rem',
                  color: 'var(--c-red)',
                }}>
                  ⚠️ {ui.mustAccept}
                </p>
              )}
            </div>

            <ModalFooter>
              <button onClick={onClose} style={cancelBtnStyle}>
                {ui.cancelBtn}
              </button>
              <button
                onClick={handleAccept}
                style={{
                  ...primaryBtnStyle,
                  opacity: accepted ? 1 : 0.6,
                }}
              >
                {ui.acceptBtn}
              </button>
            </ModalFooter>

            {/* Compliance note */}
            <div style={{
              padding: '10px 24px 14px',
              textAlign: 'center',
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
            }}>
              🛡️ {ui.poweredBy}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ── Sub-componenti ────────────────────────
interface ModalHeaderProps {
  icon: string;
  title: string;
  subtitle?: string;
  onClose: () => void;
  onBack?: () => void;
  backLabel?: string;
}

const ModalHeader: React.FC<ModalHeaderProps> = ({ icon, title, subtitle, onClose, onBack, backLabel }) => (
  <div style={{
    padding: '20px 24px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              background: 'none', border: '1px solid var(--border)',
              borderRadius: 6, cursor: 'pointer', padding: '3px 8px',
              fontSize: '0.8rem', color: 'var(--text-muted)',
              fontFamily: 'var(--font-body)',
            }}
            title="Torna alla selezione lingua"
          >
            {backLabel} ←
          </button>
        )}
        <span style={{ fontSize: 20 }}>{icon}</span>
        <h3 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.1rem',
          color: 'var(--text-navy)',
          margin: 0,
        }}>
          {title}
        </h3>
      </div>
      <button
        onClick={onClose}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 20, color: 'var(--text-muted)', padding: '2px 6px',
          borderRadius: 4, lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
    {subtitle && (
      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 30px' }}>
        {subtitle}
      </p>
    )}
  </div>
);

const ModalFooter: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    display: 'flex', gap: 10, justifyContent: 'flex-end',
    padding: '14px 24px',
  }}>
    {children}
  </div>
);

const cancelBtnStyle: React.CSSProperties = {
  background: 'none',
  border: '1.5px solid var(--border)',
  borderRadius: 'var(--r-md)',
  padding: '10px 20px',
  cursor: 'pointer',
  fontSize: '0.87rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  fontFamily: 'var(--font-body)',
};

const primaryBtnStyle: React.CSSProperties = {
  background: 'var(--c-navy)',
  color: '#fff',
  border: 'none',
  borderRadius: 'var(--r-md)',
  padding: '10px 22px',
  cursor: 'pointer',
  fontSize: '0.87rem',
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
  transition: 'opacity .15s',
};