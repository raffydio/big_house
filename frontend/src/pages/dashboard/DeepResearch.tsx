// src/pages/dashboard/DeepResearch.tsx  v3
// FIX: check limite PREVENTIVO prima della chiamata API
//      → se remaining === 0 apre UpgradeModal immediatamente senza aspettare il server
//      → aggiunta prop remaining per sapere quante ricerche restano

import React, { useState, useRef, useEffect } from 'react';
import type { Lang, ChatMessage, ChatSession } from '../../types';
import { useApi } from '../../hooks/useApi';
import { generateDocx } from '../../hooks/useStorage';
import { Button } from '../../components/ui/Button';
import { AgentThinking } from '../../components/AgentThinking';
import { ChatBubble } from '../../components/ChatBubble';

interface FoundOpportunity {
  title: string;
  estimated_price_range: string;
  size_range: string;
  zone: string;
  price_per_sqm: number;
  condition: string;
  opportunity_score: number;
  roi_potential: string;
  renovation_estimate: string;
  key_pros: string[];
  key_cons: string[];
  why_interesting: string;
}

interface DRResponse {
  market_context: string;
  opportunities: FoundOpportunity[];
  best_pick: string;
  market_trend: string;
  action_plan: string;
  comparison_summary: string;
  disclaimer: string;
  remaining_usage: number;
}

interface DeepResearchProps {
  lang: Lang;
  user: { name: string; plan: string } | null;
  onLimitReached: () => void;
  onUsageIncrement: () => void;
  onSaveSession: (session: ChatSession) => void;
  remaining?: number;   // ← NUOVO: ricerche rimaste oggi (da App.tsx via limits)
}

const EXAMPLES: Record<string, string[]> = {
  it: [
    'Cerco appartamento da ristrutturare a Napoli centro storico, budget 200.000€, almeno 70mq, buon potenziale Airbnb',
    'Investimento buy-to-let a Milano zona Loreto o Lambrate, budget 350.000€, rendimento affitto minimo 4%',
    'Trilocale a Roma Pigneto da ristrutturare, budget 180.000€, per flipping entro 18 mesi',
  ],
  en: [
    'Looking for apartment to renovate in Naples historic center, budget €200,000, at least 70sqm, good Airbnb potential',
    'Buy-to-let in Milan Loreto area, budget €350,000, minimum 4% gross yield',
    '3-bed in Rome to renovate, max budget €180,000, for flipping within 18 months',
  ],
};
const getExamples = (lang: string) => EXAMPLES[lang] || EXAMPLES.it;

function buildText(r: DRResponse): string {
  return [
    '── PANORAMICA MERCATO ──', r.market_context, '',
    `🏆 SCELTA CONSIGLIATA: ${r.best_pick}`, '',
    '── OPPORTUNITÀ TROVATE ──',
    ...r.opportunities.map((o, i) =>
      `[${i + 1}] ${o.title}\nScore: ${o.opportunity_score}/10 | ${o.estimated_price_range} | ${o.size_range}\n` +
      `${o.zone} | €${o.price_per_sqm.toLocaleString('it-IT')}/mq | ${o.condition}\n` +
      `ROI: ${o.roi_potential} | Rinnovo: ${o.renovation_estimate}\n` +
      `✅ ${o.key_pros.join(' · ')}\n⚠️ ${o.key_cons.join(' · ')}\n${o.why_interesting}`
    ),
    '', '── TREND MERCATO ──', r.market_trend,
    '', '── PIANO D\'AZIONE ──', r.action_plan,
    '', r.disclaimer,
  ].join('\n');
}

export const DeepResearchPage: React.FC<DeepResearchProps> = ({
  lang, user, onLimitReached, onUsageIncrement, onSaveSession, remaining,
}) => {
  const [query, setQuery]       = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResult, setLastResult] = useState<DRResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const { loading, error, call } = useApi<DRResponse, { query: string }>('/features/deep-research');

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const addMsg = (msg: Omit<ChatMessage, 'id' | 'timestamp'>): ChatMessage => {
    const full = {
      ...msg,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    } as ChatMessage;
    setMessages((p) => [...p, full]);
    return full;
  };

  const handleSubmit = async () => {
    if (query.trim().length < 15 || loading) return;
    setLocalError(null);

    // ── FIX: check PREVENTIVO ──
    // Se remaining è 0 (o la prop non è definita ma il piano è free),
    // apriamo subito il modal SENZA chiamare il backend
    if (remaining !== undefined && remaining <= 0) {
      onLimitReached();
      return;
    }

    const q = query;
    setQuery('');
    const userMsg = addMsg({ role: 'user', content: q, feature: 'deepresearch' });

    const result = await call({ query: q });

    if (!result) {
      // Controlla se è un errore di limite (HTTP 429 o 403) oppure generico
      const isLimitError =
        error === 'errorLimit' ||
        (typeof error === 'string' && (
          error.includes('429') ||
          error.includes('limit') ||
          error.includes('Limite') ||
          error.includes('limite')
        ));

      if (isLimitError) {
        onLimitReached();
      } else {
        const msg = error || 'Errore generico. Riprova tra qualche secondo.';
        addMsg({ role: 'assistant', content: `Errore: ${msg}`, feature: 'deepresearch' });
        setLocalError(msg);
      }
      return;
    }

    onUsageIncrement();
    setLastResult(result);

    // Se il server ci dice che le ricerche sono finite, segna il limite
    if (result.remaining_usage <= 0) {
      onLimitReached();
    }

    const text = buildText(result);
    const isPaid = user?.plan && user.plan !== 'free';
    const docxName = isPaid ? `dr_${Date.now()}.docx` : undefined;

    const aiMsg = addMsg({
      role: 'assistant',
      content: text,
      feature: 'deepresearch',
      docx_filename: docxName,
    });

    onSaveSession({
      id: crypto.randomUUID(),
      feature: 'deepresearch',
      title: q.slice(0, 60),
      created_at: new Date().toISOString(),
      messages: [userMsg, aiMsg],
      docx_filename: docxName,
    });
  };

  const handleDownloadDocx = async () => {
    if (!lastResult) return;
    await generateDocx('Deep Research — Opportunità', [
      { heading: 'Mercato',           content: lastResult.market_context },
      { heading: 'Opportunità',       content: lastResult.opportunities.map((o) => `${o.title}\n${o.why_interesting}`).join('\n\n') },
      { heading: 'Scelta Consigliata', content: lastResult.best_pick },
      { heading: 'Piano d\'Azione',   content: lastResult.action_plan },
      { heading: 'Disclaimer',        content: lastResult.disclaimer },
    ]);
  };

  const isLimitReached = remaining !== undefined && remaining <= 0;

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 900, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(1.4rem, 3vw, 2rem)',
          color: 'var(--text-navy)', marginBottom: 6,
        }}>
          Deep Research Immobiliare
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Descrivi cosa stai cercando — gli agenti AI trovano le opportunità sul mercato per te
        </p>
      </div>

      {/* ── Banner limite raggiunto ── */}
      {isLimitReached && (
        <div
          onClick={onLimitReached}
          style={{
            marginBottom: 20, padding: '14px 18px',
            background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(99,102,241,0.08))',
            border: '1px solid rgba(59,130,246,0.25)',
            borderRadius: 'var(--r-lg)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: 12, cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 18 }}>🔒</span>
            <div>
              <p style={{ color: 'var(--text-navy)', fontWeight: 700, fontSize: '0.9rem', margin: 0 }}>
                Hai esaurito le ricerche di oggi
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                Passa a PRO per continuare · 14 giorni gratis
              </p>
            </div>
          </div>
          <button style={{
            padding: '8px 16px', background: 'var(--c-blue)', border: 'none',
            borderRadius: 'var(--r-md)', color: '#fff', fontWeight: 700,
            fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'var(--font-body)',
            whiteSpace: 'nowrap',
          }}>
            Upgrade →
          </button>
        </div>
      )}

      {/* Chat history */}
      {messages.length > 0 && (
        <div style={{
          marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 18,
          maxHeight: 520, overflowY: 'auto', padding: 20,
          background: 'var(--bg-white)', border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)',
        }}>
          {messages.map((msg) => (
            <ChatBubble
              key={msg.id} message={msg}
              userName={user?.name ?? 'Tu'}
              onDownloadDocx={handleDownloadDocx}
            />
          ))}
          {loading && <AgentThinking feature="deepresearch" visible={loading} />}
          <div ref={chatEndRef} />
        </div>
      )}
      {loading && messages.length === 0 && (
        <div style={{ marginBottom: 24 }}>
          <AgentThinking feature="deepresearch" visible={loading} />
        </div>
      )}

      {/* Opportunity cards */}
      {lastResult && !loading && lastResult.opportunities.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p style={{
            fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12,
          }}>
            {lastResult.opportunities.length} Opportunità Trovate
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
            {lastResult.opportunities.map((opp, i) => (
              <OpportunityCard key={i} opp={opp} index={i} isBest={i === 0} />
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Esempi */}
        {messages.length === 0 && !isLimitReached && (
          <div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: 8 }}>
              💡 Esempi di ricerca:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {getExamples(lang).map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setQuery(ex)}
                  style={{
                    textAlign: 'left', background: 'var(--bg-page)',
                    border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
                    padding: '9px 12px', cursor: 'pointer',
                    fontSize: '0.78rem', color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-body)', transition: 'border-color .15s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--c-blue)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <label style={{
            display: 'block', fontSize: '0.75rem', fontWeight: 700,
            letterSpacing: '.08em', textTransform: 'uppercase',
            color: 'var(--text-muted)', marginBottom: 8,
          }}>
            Cosa stai cercando?
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) handleSubmit(); }}
            disabled={isLimitReached || loading}
            placeholder={
              isLimitReached
                ? '🔒 Limite raggiunto — fai upgrade per continuare'
                : 'Es: Cerco trilocale da ristrutturare a Napoli centro storico, budget 200.000€, obiettivo Airbnb...'
            }
            rows={4}
            style={{
              width: '100%', padding: '12px 14px', borderRadius: 'var(--r-md)',
              border: `1.5px solid ${
                isLimitReached
                  ? 'rgba(239,68,68,.3)'
                  : query.trim().length >= 15
                    ? 'var(--c-blue)'
                    : 'var(--border)'
              }`,
              fontFamily: 'var(--font-body)', fontSize: '0.9rem',
              color: isLimitReached ? 'var(--text-muted)' : 'var(--text-primary)',
              background: isLimitReached ? 'rgba(239,68,68,.03)' : 'var(--bg-white)',
              resize: 'vertical', outline: 'none',
              transition: 'border-color .15s', boxSizing: 'border-box',
              cursor: isLimitReached ? 'not-allowed' : 'text',
            }}
          />
          <p style={{ fontSize: '0.71rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Più dettagli fornisci (zona, budget, obiettivo, mq minimi) → migliore sarà la ricerca
            &nbsp;·&nbsp; Ctrl+Enter per inviare
          </p>
        </div>

        {(localError || (error && error !== 'errorLimit' && !loading)) && (
          <div style={{
            padding: '10px 14px',
            background: 'rgba(239,68,68,.07)',
            border: '1px solid rgba(239,68,68,.2)',
            borderRadius: 'var(--r-md)',
            color: 'var(--c-red)', fontSize: '0.85rem',
          }}>
            {localError || error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {isLimitReached ? (
            <Button variant="primary" size="lg" onClick={onLimitReached}>
              ⚡ Upgrade per continuare →
            </Button>
          ) : (
            <Button
              variant="primary" size="lg"
              onClick={handleSubmit}
              loading={loading}
              disabled={query.trim().length < 15 || loading}
            >
              {loading ? 'Agenti in ricerca...' : 'Avvia Ricerca AI →'}
            </Button>
          )}
          {messages.length > 0 && (
            <Button
              variant="secondary" size="lg"
              onClick={() => { setMessages([]); setLastResult(null); setLocalError(null); }}
            >
              Nuova ricerca
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Opportunity Card ──────────────────────────────────────────
const OpportunityCard: React.FC<{
  opp: FoundOpportunity; index: number; isBest: boolean;
}> = ({ opp, index, isBest }) => {
  const score = opp.opportunity_score;
  const scoreColor = score >= 8 ? '#10b981' : score >= 6 ? 'var(--c-blue)' : 'var(--c-gold)';

  return (
    <div style={{
      padding: 18, position: 'relative',
      background: isBest
        ? 'linear-gradient(135deg, var(--c-navy), var(--c-navy-light))'
        : 'var(--bg-white)',
      border: isBest
        ? '2px solid rgba(201,168,76,.3)'
        : '1px solid var(--border)',
      borderRadius: 'var(--r-lg)',
      boxShadow: isBest ? 'var(--shadow-md)' : 'var(--shadow-sm)',
    }}>
      {isBest && (
        <div style={{
          position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
          background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
          color: 'var(--c-navy-dark)', padding: '2px 12px',
          borderRadius: 'var(--r-full)', fontSize: '0.65rem', fontWeight: 800, whiteSpace: 'nowrap',
        }}>
          ★ Consigliata
        </div>
      )}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginTop: isBest ? 8 : 0, marginBottom: 8,
      }}>
        <span style={{
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
          color: isBest ? 'rgba(255,255,255,.45)' : 'var(--text-muted)',
        }}>
          #{index + 1} · {opp.zone}
        </span>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 700, color: scoreColor }}>
          {score.toFixed(1)}
          <span style={{ fontSize: '0.6rem', fontWeight: 400, color: isBest ? 'rgba(255,255,255,.4)' : 'var(--text-muted)' }}>
            /10
          </span>
        </span>
      </div>
      <p style={{
        fontSize: '0.87rem', fontWeight: 700,
        color: isBest ? '#fff' : 'var(--text-navy)',
        marginBottom: 10, lineHeight: 1.3,
      }}>
        {opp.title}
      </p>
      {[
        ['💶', opp.estimated_price_range],
        ['📐', opp.size_range],
        ['🏠', opp.condition],
        ['📊', `€${opp.price_per_sqm.toLocaleString('it-IT')}/mq`],
        ['📈', opp.roi_potential],
        ['🔨', opp.renovation_estimate],
      ].map(([icon, val]) => (
        <div key={String(icon)} style={{ display: 'flex', gap: 6, marginBottom: 3, fontSize: '0.77rem' }}>
          <span>{icon}</span>
          <span style={{ color: isBest ? 'rgba(255,255,255,.72)' : 'var(--text-secondary)' }}>{val}</span>
        </div>
      ))}
      {opp.key_pros.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {opp.key_pros.map((p) => (
            <div key={p} style={{ fontSize: '0.72rem', color: isBest ? 'rgba(255,255,255,.6)' : '#10b981', marginBottom: 2 }}>
              ✓ {p}
            </div>
          ))}
        </div>
      )}
      {opp.key_cons.length > 0 && (
        <div style={{ marginTop: 5 }}>
          {opp.key_cons.map((c) => (
            <div key={c} style={{ fontSize: '0.72rem', color: isBest ? 'rgba(255,255,255,.45)' : 'var(--c-red)', marginBottom: 2 }}>
              ⚠ {c}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};