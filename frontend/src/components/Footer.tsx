// ─────────────────────────────────────────
// src/components/Footer.tsx
// Footer globale con link legali
// ─────────────────────────────────────────

import React, { useState } from 'react';
import type { Lang } from '../types';
import { t } from '../i18n/translations';

interface FooterProps {
  lang: Lang;
}

// Testi legali minimi inline per ogni voce del footer
// (il modale completo è in TermsModal.tsx — qui sono versioni compatte)
const LEGAL_LABELS: Record<string, Record<Lang, string>> = {
  privacy: {
    it: 'Privacy Policy',
    en: 'Privacy Policy',
    fr: 'Politique de Confidentialité',
    de: 'Datenschutzrichtlinie',
    es: 'Política de Privacidad',
    pt: 'Política de Privacidade',
  },
  terms: {
    it: 'Termini di Servizio',
    en: 'Terms of Service',
    fr: 'Conditions d\'Utilisation',
    de: 'Nutzungsbedingungen',
    es: 'Términos de Servicio',
    pt: 'Termos de Serviço',
  },
  cookie: {
    it: 'Cookie Policy',
    en: 'Cookie Policy',
    fr: 'Politique de Cookies',
    de: 'Cookie-Richtlinie',
    es: 'Política de Cookies',
    pt: 'Política de Cookies',
  },
  disclaimer: {
    it: 'Disclaimer AI',
    en: 'AI Disclaimer',
    fr: 'Avertissement IA',
    de: 'KI-Haftungsausschluss',
    es: 'Descargo IA',
    pt: 'Aviso Legal IA',
  },
  contacts: {
    it: 'Contatti',
    en: 'Contact',
    fr: 'Contact',
    de: 'Kontakt',
    es: 'Contacto',
    pt: 'Contato',
  },
};

const COPYRIGHT: Record<Lang, string> = {
  it: 'Tutti i diritti riservati.',
  en: 'All rights reserved.',
  fr: 'Tous droits réservés.',
  de: 'Alle Rechte vorbehalten.',
  es: 'Todos los derechos reservados.',
  pt: 'Todos os direitos reservados.',
};

const AI_NOTE: Record<Lang, string> = {
  it: 'I risultati AI hanno finalità puramente informativa e non costituiscono consulenza finanziaria o immobiliare.',
  en: 'AI results are for informational purposes only and do not constitute financial or real estate advice.',
  fr: 'Les résultats IA sont à titre informatif uniquement et ne constituent pas un conseil financier ou immobilier.',
  de: 'KI-Ergebnisse dienen nur zu Informationszwecken und stellen keine Finanz- oder Immobilienberatung dar.',
  es: 'Los resultados de IA son solo informativos y no constituyen asesoramiento financiero o inmobiliario.',
  pt: 'Os resultados da IA são apenas informativos e não constituem aconselhamento financeiro ou imobiliário.',
};

type LegalSection = 'privacy' | 'terms' | 'cookie' | 'disclaimer' | 'contacts' | null;

export const Footer: React.FC<FooterProps> = ({ lang }) => {
  const [open, setOpen] = useState<LegalSection>(null);

  return (
    <>
      <footer style={{
        background: 'var(--c-navy)',
        color: 'rgba(255,255,255,.55)',
        padding: '32px clamp(16px, 4vw, 48px) 20px',
        marginTop: 'auto',
      }}>
        {/* Top row */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          marginBottom: 20,
          paddingBottom: 20,
          borderBottom: '1px solid rgba(255,255,255,.08)',
        }}>
          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 20, color: 'var(--c-gold)' }}>⬡</span>
            <span style={{
              fontFamily: 'var(--font-display)',
              fontSize: '1.1rem',
              color: 'rgba(255,255,255,.9)',
              fontStyle: 'italic',
            }}>
              Big House AI
            </span>
          </div>

          {/* Legal links */}
          <nav style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 20px' }}>
            {(Object.keys(LEGAL_LABELS) as LegalSection[]).filter(Boolean).map((key) => (
              <button
                key={key!}
                onClick={() => setOpen(key)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'rgba(255,255,255,.55)',
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-body)',
                  padding: '2px 0',
                  transition: 'color .15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--c-gold)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,.55)'; }}
              >
                {LEGAL_LABELS[key!][lang]}
              </button>
            ))}
          </nav>
        </div>

        {/* AI disclaimer note */}
        <p style={{
          fontSize: '0.73rem',
          lineHeight: 1.6,
          maxWidth: 680,
          marginBottom: 12,
          color: 'rgba(255,255,255,.35)',
        }}>
          ⚠️ {AI_NOTE[lang]}
        </p>

        {/* Bottom row */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          fontSize: '0.73rem',
        }}>
          <span>
            © {new Date().getFullYear()} Big House AI · P.IVA [DA INSERIRE] · {COPYRIGHT[lang]}
          </span>
          <span style={{ color: 'rgba(255,255,255,.25)' }}>
            Conforme AI Act UE 2024/1689 · Legge 132/2025
          </span>
        </div>
      </footer>

      {/* Legal overlay */}
      {open && <LegalOverlay section={open} lang={lang} onClose={() => setOpen(null)} />}
    </>
  );
};

// ── Mini overlay per sezioni legali ──────────────────────────
const LEGAL_CONTENT: Record<NonNullable<LegalSection>, Record<Lang, { title: string; body: string }>> = {
  privacy: {
    it: {
      title: 'Privacy Policy',
      body: `Titolare: Big House AI (P.IVA da inserire), sede in Italia. Contatto: legal@bighouse.ai

DATI RACCOLTI
• Registrazione: nome, email, password (hash Argon2 — non leggibile)
• Utilizzo: query di testo, parametri numerici, storico sessioni
• Tecnici: IP address (max 30 giorni), token JWT (48h)

SUB-PROCESSOR
• Railway — server Frankfurt, UE
• Cloudflare — CDN e sicurezza
• Google Cloud — modello AI piano Free (europe-west)
• AWS / Anthropic — modelli AI piani PRO/PLUS (eu-central-1 Frankfurt)
I trasferimenti USA avvengono tramite SCC (Decisione UE 2021/914).

CONSERVAZIONE: dati account 12 mesi post-chiusura · sessioni 24 mesi · log IP 30 giorni

DIRITTI (Artt. 15-22 GDPR): accesso, rettifica, cancellazione, portabilità, opposizione.
Richieste: legal@bighouse.ai — risposta entro 30 giorni.
Reclami: www.garanteprivacy.it`,
    },
    en: {
      title: 'Privacy Policy',
      body: `Controller: Big House AI (VAT TBD), Italy. Contact: legal@bighouse.ai

DATA COLLECTED
• Registration: name, email, password (Argon2 hash — unreadable)
• Usage: text queries, numeric parameters, session history
• Technical: IP address (max 30 days), JWT token (48h)

SUB-PROCESSORS
• Railway — Frankfurt server, EU
• Cloudflare — CDN and security
• Google Cloud — Free plan AI model (europe-west)
• AWS / Anthropic — PRO/PLUS AI models (eu-central-1 Frankfurt)
US transfers via SCC (EU Decision 2021/914).

RETENTION: account data 12 months after closure · sessions 24 months · IP logs 30 days

RIGHTS (Arts. 15-22 GDPR): access, rectification, deletion, portability, objection.
Requests: legal@bighouse.ai — response within 30 days.
Complaints: www.garanteprivacy.it`,
    },
    fr: {
      title: 'Politique de Confidentialité',
      body: `Responsable: Big House AI (TVA à définir), Italie. Contact: legal@bighouse.ai

DONNÉES COLLECTÉES
• Inscription: nom, email, mot de passe (hash Argon2)
• Utilisation: requêtes texte, paramètres numériques, historique
• Techniques: adresse IP (max 30 jours), token JWT (48h)

SOUS-TRAITANTS
• Railway — serveur Frankfurt, UE
• Cloudflare — CDN et sécurité
• Google Cloud — modèle AI plan Free (europe-west)
• AWS / Anthropic — modèles AI PRO/PLUS (eu-central-1 Frankfurt)
Transferts US via SCC (Décision UE 2021/914).

Droits RGPD: legal@bighouse.ai — réponse sous 30 jours.`,
    },
    de: {
      title: 'Datenschutzrichtlinie',
      body: `Verantwortlicher: Big House AI (USt-IdNr. ausstehend), Italien. Kontakt: legal@bighouse.ai

ERHOBENE DATEN
• Registrierung: Name, E-Mail, Passwort (Argon2-Hash)
• Nutzung: Textanfragen, numerische Parameter, Sitzungsverlauf
• Technisch: IP-Adresse (max. 30 Tage), JWT-Token (48h)

UNTERAUFTRAGSVERARBEITER
• Railway — Frankfurt-Server, EU
• Cloudflare — CDN und Sicherheit
• Google Cloud — KI-Modell Free-Plan (europe-west)
• AWS / Anthropic — KI-Modelle PRO/PLUS (eu-central-1 Frankfurt)
US-Übertragungen über SCC (EU-Beschluss 2021/914).

DSGVO-Rechte: legal@bighouse.ai — Antwort innerhalb 30 Tagen.`,
    },
    es: {
      title: 'Política de Privacidad',
      body: `Responsable: Big House AI (NIF pendiente), Italia. Contacto: legal@bighouse.ai

DATOS RECOPILADOS
• Registro: nombre, email, contraseña (hash Argon2)
• Uso: consultas de texto, parámetros numéricos, historial
• Técnicos: dirección IP (máx. 30 días), token JWT (48h)

SUBENCARGADOS
• Railway — servidor Frankfurt, UE
• Cloudflare — CDN y seguridad
• Google Cloud — modelo IA plan Free (europe-west)
• AWS / Anthropic — modelos IA PRO/PLUS (eu-central-1 Frankfurt)
Transferencias a EE.UU. mediante SCC (Decisión UE 2021/914).

Derechos RGPD: legal@bighouse.ai — respuesta en 30 días.`,
    },
    pt: {
      title: 'Política de Privacidade',
      body: `Responsável: Big House AI (NIF pendente), Itália. Contacto: legal@bighouse.ai

DADOS RECOLHIDOS
• Registo: nome, email, senha (hash Argon2)
• Utilização: consultas de texto, parâmetros numéricos, histórico
• Técnicos: endereço IP (máx. 30 dias), token JWT (48h)

SUBPROCESSADORES
• Railway — servidor Frankfurt, UE
• Cloudflare — CDN e segurança
• Google Cloud — modelo IA plano Free (europe-west)
• AWS / Anthropic — modelos IA PRO/PLUS (eu-central-1 Frankfurt)
Transferências EUA via SCC (Decisão UE 2021/914).

Direitos RGPD: legal@bighouse.ai — resposta em 30 dias.`,
    },
  },

  terms: {
    it: { title: 'Termini di Servizio', body: `Big House AI è una piattaforma SaaS per analisi di investimenti immobiliari.

UTILIZZO CONSENTITO — Solo per:
• Analisi proprietà immobiliari
• Calcolo ROI su immobili
• Ricerca mercato immobiliare italiano/europeo

USI VIETATI
• Qualsiasi uso non connesso al settore immobiliare
• Aggirare limiti giornalieri con account multipli
• Attività illegali o fraudolente

PIANI E PREZZI
• Free: gratuito — 1 Deep Research + 3 Calcola ROI/giorno
• PRO: €29/mese (o €22/mese annuale) — 5 DR + 20 ROI/giorno
• PLUS: €79/mese (o €59/mese annuale) — 20 DR + 100 ROI/giorno

RECESSO: consumatori B2C hanno 14 giorni di recesso (Codice del Consumo, Art. 52).

LIMITAZIONE DI RESPONSABILITÀ — I risultati AI hanno finalità informativa. Non costituiscono consulenza finanziaria o immobiliare. Il Fornitore non è responsabile di perdite derivanti dall'uso delle analisi.

Legge applicabile: italiana. Foro: [sede del Fornitore].
Contatto: legal@bighouse.ai` },
    en: { title: 'Terms of Service', body: `Big House AI is a SaaS platform for real estate investment analysis.

PERMITTED USE — Only for:
• Real estate property analysis
• ROI calculation on properties
• Italian/European real estate market research

PROHIBITED USES
• Any use unrelated to real estate
• Circumventing daily limits with multiple accounts
• Illegal or fraudulent activities

PLANS & PRICING
• Free: free — 1 Deep Research + 3 ROI Calculations/day
• PRO: €29/month (or €22/month annual) — 5 DR + 20 ROI/day
• PLUS: €79/month (or €59/month annual) — 20 DR + 100 ROI/day

WITHDRAWAL: B2C consumers have 14 days withdrawal right.

LIABILITY LIMITATION — AI results are informational only. They do not constitute financial or real estate advice. The Provider is not liable for losses arising from use of the analyses.

Contact: legal@bighouse.ai` },
    fr: { title: 'Conditions d\'Utilisation', body: `Big House AI est une plateforme SaaS pour l'analyse d'investissements immobiliers.

UTILISATION AUTORISÉE — Uniquement pour:
• Analyse de propriétés immobilières
• Calcul du ROI immobilier
• Recherche du marché immobilier

UTILISATIONS INTERDITES
• Tout usage non lié à l'immobilier
• Contourner les limites quotidiennes
• Activités illégales ou frauduleuses

PLANS: Free (gratuit) · PRO (€29/mois) · PLUS (€79/mois)

Droit de rétractation: 14 jours pour les consommateurs B2C.
Responsabilité limitée: les résultats IA sont informatifs uniquement.
Contact: legal@bighouse.ai` },
    de: { title: 'Nutzungsbedingungen', body: `Big House AI ist eine SaaS-Plattform für Immobilieninvestitionsanalysen.

ERLAUBTE NUTZUNG — Nur für:
• Analyse von Immobilien
• ROI-Berechnung für Immobilien
• Immobilienmarktrecherche

VERBOTENE NUTZUNG
• Jede nicht immobilienbezogene Nutzung
• Umgehung von Tageslimits
• Illegale oder betrügerische Aktivitäten

PLÄNE: Free (kostenlos) · PRO (€29/Monat) · PLUS (€79/Monat)

Widerrufsrecht: 14 Tage für B2C-Verbraucher.
Haftungsbeschränkung: KI-Ergebnisse dienen nur zu Informationszwecken.
Kontakt: legal@bighouse.ai` },
    es: { title: 'Términos de Servicio', body: `Big House AI es una plataforma SaaS para análisis de inversiones inmobiliarias.

USO PERMITIDO — Solo para:
• Análisis de propiedades inmobiliarias
• Cálculo de ROI inmobiliario
• Investigación del mercado inmobiliario

USOS PROHIBIDOS
• Cualquier uso no relacionado con el sector inmobiliario
• Eludir límites diarios con múltiples cuentas
• Actividades ilegales o fraudulentas

PLANES: Free (gratis) · PRO (€29/mes) · PLUS (€79/mes)

Desistimiento: 14 días para consumidores B2C.
Responsabilidad limitada: los resultados de IA son solo informativos.
Contacto: legal@bighouse.ai` },
    pt: { title: 'Termos de Serviço', body: `Big House AI é uma plataforma SaaS para análise de investimentos imobiliários.

USO PERMITIDO — Apenas para:
• Análise de propriedades imobiliárias
• Cálculo de ROI imobiliário
• Pesquisa do mercado imobiliário

USOS PROIBIDOS
• Qualquer uso não relacionado ao setor imobiliário
• Contornar limites diários com múltiplas contas
• Atividades ilegais ou fraudulentas

PLANOS: Free (gratuito) · PRO (€29/mês) · PLUS (€79/mês)

Arrependimento: 14 dias para consumidores B2C.
Responsabilidade limitada: os resultados de IA são apenas informativos.
Contacto: legal@bighouse.ai` },
  },

  cookie: {
    it: { title: 'Cookie Policy', body: `Big House AI utilizza esclusivamente storage tecnico strettamente necessario al funzionamento del servizio. NON utilizziamo cookie di profilazione, tracking o pubblicità.

STORAGE TECNICO UTILIZZATO
• bh_token — Token JWT autenticazione — durata 48h — tecnico/necessario
• bh_lang — Preferenza lingua interfaccia — permanente — funzionale
• bh_chat_sessions — Cache locale sessioni — solo per utenti autenticati

COOKIE NON UTILIZZATI
• Google Analytics o sistemi di analisi comportamentale
• Facebook Pixel, LinkedIn o altri tracker pubblicitari
• Sistemi di fingerprinting o remarketing

CLOUDFLARE CDN: può impostare cookie tecnici per protezione DDoS e gestione traffico. cloudflare.com/cookie-policy

COME ELIMINARE IL LOCALSTORE: dalle impostazioni del browser → Privacy → Dati siti web. Nota: l'eliminazione causa il logout automatico.

Non è richiesto consenso poiché utilizziamo solo storage tecnico necessario (Art. 5 Direttiva ePrivacy; Linee Guida Garante Privacy 10/06/2021).

Contatto: legal@bighouse.ai` },
    en: { title: 'Cookie Policy', body: `Big House AI uses only technically necessary storage. We do NOT use profiling, tracking or advertising cookies.

TECHNICAL STORAGE USED
• bh_token — JWT authentication token — 48h duration — technical/necessary
• bh_lang — Interface language preference — permanent — functional
• bh_chat_sessions — Local session cache — authenticated users only

COOKIES NOT USED
• Google Analytics or behavioral analysis systems
• Facebook Pixel, LinkedIn or other advertising trackers
• Fingerprinting or remarketing systems

CLOUDFLARE CDN: may set technical cookies for DDoS protection. cloudflare.com/cookie-policy

No consent required as we only use technically necessary storage (Art. 5 ePrivacy Directive).

Contact: legal@bighouse.ai` },
    fr: { title: 'Politique de Cookies', body: `Big House AI utilise uniquement du stockage technique strictement nécessaire. Nous N'utilisons PAS de cookies de profilage, de suivi ou publicitaires.

STOCKAGE TECHNIQUE UTILISÉ
• bh_token — Token JWT d'authentification — 48h — technique/nécessaire
• bh_lang — Préférence de langue — permanente — fonctionnel
• bh_chat_sessions — Cache local des sessions — utilisateurs connectés uniquement

Aucun consentement requis (Art. 5 Directive ePrivacy).
Contact: legal@bighouse.ai` },
    de: { title: 'Cookie-Richtlinie', body: `Big House AI verwendet ausschließlich technisch notwendigen Speicher. Wir verwenden KEINE Profiling-, Tracking- oder Werbe-Cookies.

VERWENDETER TECHNISCHER SPEICHER
• bh_token — JWT-Authentifizierungstoken — 48h — technisch/notwendig
• bh_lang — Sprachpräferenz — dauerhaft — funktional
• bh_chat_sessions — Lokaler Sitzungscache — nur angemeldete Nutzer

Kein Einverständnis erforderlich (Art. 5 ePrivacy-Richtlinie).
Kontakt: legal@bighouse.ai` },
    es: { title: 'Política de Cookies', body: `Big House AI utiliza únicamente almacenamiento técnico estrictamente necesario. NO utilizamos cookies de perfilado, seguimiento o publicidad.

ALMACENAMIENTO TÉCNICO UTILIZADO
• bh_token — Token JWT de autenticación — 48h — técnico/necesario
• bh_lang — Preferencia de idioma — permanente — funcional
• bh_chat_sessions — Caché local de sesiones — solo usuarios autenticados

No se requiere consentimiento (Art. 5 Directiva ePrivacy).
Contacto: legal@bighouse.ai` },
    pt: { title: 'Política de Cookies', body: `Big House AI utiliza apenas armazenamento técnico estritamente necessário. NÃO utilizamos cookies de perfil, rastreamento ou publicidade.

ARMAZENAMENTO TÉCNICO UTILIZADO
• bh_token — Token JWT de autenticação — 48h — técnico/necessário
• bh_lang — Preferência de idioma — permanente — funcional
• bh_chat_sessions — Cache local de sessões — apenas utilizadores autenticados

Não é necessário consentimento (Art. 5 Diretiva ePrivacy).
Contacto: legal@bighouse.ai` },
  },

  disclaimer: {
    it: { title: 'Disclaimer — Intelligenza Artificiale', body: `Big House AI integra modelli AI di terze parti per generare analisi immobiliari.

MODELLI UTILIZZATI
• Piano Free: Google Gemini Flash 2.0 — server Google Cloud Europa (europe-west)
• Piani PRO/PLUS: Anthropic Claude Haiku/Sonnet — server AWS Francoforte (eu-central-1)

Nessun dato utente viene usato per addestrare i modelli. I sub-processor AI hanno firmato accordi GDPR-compliant.

CLASSIFICAZIONE AI ACT (Reg. UE 2024/1689)
Sistema a RISCHIO LIMITATO. Big House AI fornisce supporto informativo — la decisione finale rimane sempre all'utente.

⚠️ AVVISO IMPORTANTE
I risultati generati dall'AI hanno finalità ESCLUSIVAMENTE informativa. NON costituiscono consulenza finanziaria, immobiliare, legale o fiscale. Verifica sempre con un professionista qualificato prima di prendere decisioni di investimento.

Conforme a: Reg. UE 2024/1689 (AI Act) · Legge italiana 132/2025
Segnalazioni output errati: legal@bighouse.ai` },
    en: { title: 'AI Disclaimer', body: `Big House AI integrates third-party AI models to generate real estate analyses.

MODELS USED
• Free Plan: Google Gemini Flash 2.0 — Google Cloud Europe servers (europe-west)
• PRO/PLUS Plans: Anthropic Claude Haiku/Sonnet — AWS Frankfurt servers (eu-central-1)

No user data is used to train the models. AI sub-processors have signed GDPR-compliant agreements.

AI ACT CLASSIFICATION (EU Reg. 2024/1689)
LIMITED RISK system. Big House AI provides informational support — the final decision always rests with the user.

⚠️ IMPORTANT NOTICE
AI-generated results are for INFORMATIONAL PURPOSES ONLY. They do NOT constitute financial, real estate, legal or tax advice. Always verify with a qualified professional before making investment decisions.

Compliant with: EU Reg. 2024/1689 (AI Act) · Italian Law 132/2025` },
    fr: { title: 'Avertissement IA', body: `Big House AI intègre des modèles IA tiers pour générer des analyses immobilières.

MODÈLES UTILISÉS
• Plan Free: Google Gemini Flash 2.0 — serveurs Google Cloud Europe
• Plans PRO/PLUS: Anthropic Claude — serveurs AWS Frankfurt (eu-central-1)

Aucune donnée utilisateur n'est utilisée pour entraîner les modèles.

⚠️ AVIS IMPORTANT
Les résultats générés par l'IA sont à titre EXCLUSIVEMENT informatif. Ils ne constituent pas un conseil financier, immobilier, juridique ou fiscal.

Conforme à: Règl. UE 2024/1689 (AI Act)` },
    de: { title: 'KI-Haftungsausschluss', body: `Big House AI integriert KI-Modelle Dritter zur Erstellung von Immobilienanalysen.

VERWENDETE MODELLE
• Free-Plan: Google Gemini Flash 2.0 — Google Cloud Europa-Server
• PRO/PLUS-Pläne: Anthropic Claude — AWS Frankfurt-Server (eu-central-1)

Keine Nutzerdaten werden zum Training der Modelle verwendet.

⚠️ WICHTIGER HINWEIS
KI-generierte Ergebnisse dienen AUSSCHLIESSLICH zu Informationszwecken. Sie stellen keine Finanz-, Immobilien-, Rechts- oder Steuerberatung dar.

Konform mit: EU-Verordnung 2024/1689 (KI-Gesetz)` },
    es: { title: 'Descargo de Responsabilidad IA', body: `Big House AI integra modelos de IA de terceros para generar análisis inmobiliarios.

MODELOS UTILIZADOS
• Plan Free: Google Gemini Flash 2.0 — servidores Google Cloud Europa
• Planes PRO/PLUS: Anthropic Claude — servidores AWS Frankfurt (eu-central-1)

Ningún dato de usuario se utiliza para entrenar los modelos.

⚠️ AVISO IMPORTANTE
Los resultados generados por IA son EXCLUSIVAMENTE informativos. NO constituyen asesoramiento financiero, inmobiliario, legal o fiscal.

Conforme a: Regl. UE 2024/1689 (Ley de IA)` },
    pt: { title: 'Aviso Legal IA', body: `Big House AI integra modelos de IA de terceiros para gerar análises imobiliárias.

MODELOS UTILIZADOS
• Plano Free: Google Gemini Flash 2.0 — servidores Google Cloud Europa
• Planos PRO/PLUS: Anthropic Claude — servidores AWS Frankfurt (eu-central-1)

Nenhum dado de utilizador é usado para treinar os modelos.

⚠️ AVISO IMPORTANTE
Os resultados gerados pela IA são EXCLUSIVAMENTE informativos. NÃO constituem aconselhamento financeiro, imobiliário, jurídico ou fiscal.

Conforme a: Reg. UE 2024/1689 (Lei de IA)` },
  },

  contacts: {
    it: { title: 'Contatti', body: `Big House AI
Sede legale: [Città, Italia]
P.IVA: [DA INSERIRE]
Codice Fiscale: [DA INSERIRE]

EMAIL
• Generale: legal@bighouse.ai
• Supporto tecnico: support@bighouse.ai
• Privacy/GDPR: privacy@bighouse.ai

Risposta entro 2 giorni lavorativi per supporto.
Risposta entro 30 giorni per richieste GDPR.

AUTORITÀ DI VIGILANZA
• Garante Privacy: www.garanteprivacy.it
• AgID (sistemi AI): www.agid.gov.it
• ACN (cybersicurezza): www.acn.gov.it` },
    en: { title: 'Contact', body: `Big House AI
Registered address: [City, Italy]
VAT: [TO BE INSERTED]

EMAIL
• General: legal@bighouse.ai
• Technical support: support@bighouse.ai
• Privacy/GDPR: privacy@bighouse.ai

Response within 2 business days for support.
Response within 30 days for GDPR requests.

SUPERVISORY AUTHORITIES
• Italian Privacy Authority: www.garanteprivacy.it
• AgID (AI systems): www.agid.gov.it` },
    fr: { title: 'Contact', body: `Big House AI
Siège social: [Ville, Italie]
TVA: [À INSÉRER]

EMAIL
• Général: legal@bighouse.ai
• Support technique: support@bighouse.ai
• Confidentialité/RGPD: privacy@bighouse.ai

Réponse sous 2 jours ouvrables pour le support.
Réponse sous 30 jours pour les demandes RGPD.` },
    de: { title: 'Kontakt', body: `Big House AI
Sitz: [Stadt, Italien]
USt-IdNr.: [EINZUFÜGEN]

E-MAIL
• Allgemein: legal@bighouse.ai
• Technischer Support: support@bighouse.ai
• Datenschutz/DSGVO: privacy@bighouse.ai

Antwort innerhalb 2 Werktagen für Support.
Antwort innerhalb 30 Tagen für DSGVO-Anfragen.` },
    es: { title: 'Contacto', body: `Big House AI
Domicilio social: [Ciudad, Italia]
NIF: [A INSERTAR]

EMAIL
• General: legal@bighouse.ai
• Soporte técnico: support@bighouse.ai
• Privacidad/RGPD: privacy@bighouse.ai

Respuesta en 2 días hábiles para soporte.
Respuesta en 30 días para solicitudes RGPD.` },
    pt: { title: 'Contato', body: `Big House AI
Sede: [Cidade, Itália]
NIF: [A INSERIR]

EMAIL
• Geral: legal@bighouse.ai
• Suporte técnico: support@bighouse.ai
• Privacidade/RGPD: privacy@bighouse.ai

Resposta em 2 dias úteis para suporte.
Resposta em 30 dias para pedidos RGPD.` },
  },
};

interface LegalOverlayProps {
  section: NonNullable<LegalSection>;
  lang: Lang;
  onClose: () => void;
}

const LegalOverlay: React.FC<LegalOverlayProps> = ({ section, lang, onClose }) => {
  const content = LEGAL_CONTENT[section][lang];

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,.55)',
        backdropFilter: 'blur(4px)',
        zIndex: 9000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-white)',
          borderRadius: 'var(--r-xl)',
          maxWidth: 620,
          width: '100%',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-xl)',
          animation: 'fadeIn .2s ease both',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 24px',
          borderBottom: '1px solid var(--border)',
        }}>
          <h3 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-navy)', fontSize: '1.15rem' }}>
            {content.title}
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 20, color: 'var(--text-muted)', lineHeight: 1,
              padding: '2px 6px', borderRadius: 4,
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ overflowY: 'auto', padding: '24px', flex: 1 }}>
          <pre style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.82rem',
            lineHeight: 1.75,
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: 0,
          }}>
            {content.body}
          </pre>
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', textAlign: 'right' }}>
          <button
            onClick={onClose}
            style={{
              background: 'var(--c-navy)', color: '#fff', border: 'none',
              borderRadius: 'var(--r-md)', padding: '10px 24px',
              cursor: 'pointer', fontSize: '0.87rem', fontWeight: 600,
              fontFamily: 'var(--font-body)',
            }}
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};