// src/pages/dashboard/DeepResearch.tsx v4 (Async Celery + Redis)
import React, { useState, useRef, useEffect } from 'react';
import type { Lang, ChatMessage, ChatSession } from '../../types';
import { useApi } from '../../hooks/useApi';
import { generateDocx } from '../../hooks/useStorage';
import { Button } from '../../components/ui/Button';
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

// NUOVA STRUTTURA RISULTATO (Sprint 4)
interface DRResponse {
  summary: string;
  market_overview: string;
  properties_analysis: FoundOpportunity[];
  risks_opportunities: string;
  investment_recommendation: string;
  llm_used: string;
}

// RISPOSTA INIZIALE DEL JOB
interface JobInitResponse {
  job_id: string;
  status: string;
  poll_url: string;
  remaining_usage: number;
}

interface DeepResearchProps {
  lang: Lang;
  user: { name: string; plan: string } | null;
  onLimitReached: () => void;
  onUsageIncrement: () => void;
  onSaveSession: (session: ChatSession) => void;
  remaining?: number;
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
    '── VERDETTO ──', r.summary, '',
    '── PANORAMICA MERCATO ──', r.market_overview, '',
    '── OPPORTUNITÀ TROVATE ──',
    ...(r.properties_analysis || []).map((o, i) =>
      `[${i + 1}] ${o.title}\nScore: ${o.opportunity_score}/10 | ${o.estimated_price_range} | ${o.size_range}\n` +
      `${o.zone} | €${o.price_per_sqm?.toLocaleString('it-IT')}/mq | ${o.condition}\n` +
      `ROI: ${o.roi_potential} | Rinnovo: ${o.renovation_estimate}\n` +
      `✅ ${o.key_pros?.join(' · ')}\n⚠️ ${o.key_cons?.join(' · ')}\n${o.why_interesting}`
    ),
    '', '── RISCHI E OPPORTUNITÀ ──', r.risks_opportunities,
    '', '── RACCOMANDAZIONE FINALE ──', r.investment_recommendation,
  ].join('\n');
}

export const DeepResearchPage: React.FC<DeepResearchProps> = ({
  lang, user, onLimitReached, onUsageIncrement, onSaveSession, remaining,
}) => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResult, setLastResult] = useState<DRResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  
  // Stati per il Polling
  const [isPolling, setIsPolling] = useState(false);
  const [pollData, setPollData] = useState({ progress: 0, step: 'In coda...' });
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const { loading, error, call } = useApi<JobInitResponse, { query: string }>('/features/deep-research');

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isPolling]);

  const addMsg = (msg: Omit<ChatMessage, 'id' | 'timestamp'>): ChatMessage => {
    const full = { ...msg, id: crypto.randomUUID(), timestamp: new Date().toISOString() } as ChatMessage;
    setMessages((p) => [...p, full]);
    return full;
  };

  const startPolling = (jobId: string, q: string, userMsg: ChatMessage) => {
    setIsPolling(true);
    setPollData({ progress: 0, step: 'In coda...' });
    setLocalError(null);
    
    const token = localStorage.getItem('bh_token');
    const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
    
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = await res.json();
        
        setPollData({
          progress: data.progress || 0,
          step: data.current_step || 'Elaborazione in corso...'
        });

        if (data.status === 'completed') {
          clearInterval(interval);
          setIsPolling(false);
          setLastResult(data.result);
          onUsageIncrement();
          
          const text = buildText(data.result);
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
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setIsPolling(false);
          setLocalError(data.error || "Errore durante l'analisi degli agenti.");
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 5000); // <--- FIX: Modificato da 2500 a 5000 ms
  };

  const handleSubmit = async () => {
    if (query.trim().length < 15 || loading || isPolling) return;
    setLocalError(null);

    if (remaining !== undefined && remaining <= 0) {
      onLimitReached();
      return;
    }

    const q = query;
    setQuery('');
    const userMsg = addMsg({ role: 'user', content: q, feature: 'deepresearch' });

    // 1. Chiamata iniziale per ottenere il job_id
    const initResult = await call({ query: q });

    if (!initResult) {
      const isLimitError = error === 'errorLimit' || (typeof error === 'string' && (error.includes('429') || error.toLowerCase().includes('limit')));
      if (isLimitError) {
        onLimitReached();
      } else {
        setLocalError(error || 'Errore di connessione al server.');
      }
      return;
    }

    if (initResult.remaining_usage <= 0) {
      onLimitReached();
    }

    // 2. Avvia il polling
    startPolling(initResult.job_id, q, userMsg);
  };

  const handleDownloadDocx = async () => {
    if (!lastResult) return;
    await generateDocx('Deep Research — Opportunità', [
      { heading: 'Verdetto', content: lastResult.summary },
      { heading: 'Panoramica Mercato', content: lastResult.market_overview },
      { heading: 'Opportunità', content: (lastResult.properties_analysis || []).map((o) => `${o.title}\n${o.why_interesting}`).join('\n\n') },
      { heading: 'Rischi e Opportunità', content: lastResult.risks_opportunities },
      { heading: 'Raccomandazione Finale', content: lastResult.investment_recommendation },
    ]);
  };

  const isLimitReached = remaining !== undefined && remaining <= 0;

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: 'var(--text-navy)', marginBottom: 6 }}>
          Deep Research Immobiliare
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Descrivi cosa stai cercando — gli agenti AI trovano le opportunità sul mercato per te
        </p>
      </div>

      {isLimitReached && (
        <div onClick={onLimitReached} style={{ marginBottom: 20, padding: '14px 18px', background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(99,102,241,0.08))', border: '1px solid rgba(59,130,246,0.25)', borderRadius: 'var(--r-lg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, cursor: 'pointer' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 18 }}>🔒</span>
            <div>
              <p style={{ color: 'var(--text-navy)', fontWeight: 700, fontSize: '0.9rem', margin: 0 }}>Hai esaurito le ricerche di oggi</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>Passa a PRO per continuare · 14 giorni gratis</p>
            </div>
          </div>
          <button style={{ padding: '8px 16px', background: 'var(--c-blue)', border: 'none', borderRadius: 'var(--r-md)', color: '#fff', fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'var(--font-body)', whiteSpace: 'nowrap' }}>Upgrade →</button>
        </div>
      )}

      {/* Chat history */}
      {messages.length > 0 && (
        <div style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 18, maxHeight: 520, overflowY: 'auto', padding: 20, background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}>
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} userName={user?.name ?? 'Tu'} onDownloadDocx={handleDownloadDocx} />
          ))}
          
          {/* Progress Bar Asincrona */}
          {isPolling && (
            <div style={{ padding: 20, background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', animation: 'fadeIn 0.3s ease' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-navy)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="spinner spinner--dark" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  {pollData.step}
                </span>
                <span>{pollData.progress}%</span>
              </div>
              <div style={{ height: 8, background: 'rgba(0,0,0,0.05)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pollData.progress}%`, background: 'var(--c-blue)', transition: 'width 0.5s ease' }} />
              </div>
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>
      )}

      {/* Opportunity cards */}
      {lastResult && !isPolling && (lastResult.properties_analysis?.length > 0) && (
        <div style={{ marginBottom: 24 }}>
          <p style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
            {lastResult.properties_analysis.length} Opportunità Trovate
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
            {lastResult.properties_analysis.map((opp, i) => (
              <OpportunityCard key={i} opp={opp} index={i} isBest={i === 0} />
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {messages.length === 0 && !isLimitReached && (
          <div>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: 8 }}>💡 Esempi di ricerca:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {getExamples(lang).map((ex, i) => (
                <button key={i} onClick={() => setQuery(ex)} style={{ textAlign: 'left', background: 'var(--bg-page)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '9px 12px', cursor: 'pointer', fontSize: '0.78rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', transition: 'border-color .15s' }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--c-blue)'; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
            Cosa stai cercando?
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) handleSubmit(); }}
            disabled={isLimitReached || loading || isPolling}
            placeholder={isLimitReached ? '🔒 Limite raggiunto — fai upgrade per continuare' : 'Es: Cerco trilocale da ristrutturare a Napoli centro storico, budget 200.000€, obiettivo Airbnb...'}
            rows={4}
            style={{ width: '100%', padding: '12px 14px', borderRadius: 'var(--r-md)', border: `1.5px solid ${isLimitReached ? 'rgba(239,68,68,.3)' : query.trim().length >= 15 ? 'var(--c-blue)' : 'var(--border)'}`, fontFamily: 'var(--font-body)', fontSize: '0.9rem', color: isLimitReached ? 'var(--text-muted)' : 'var(--text-primary)', background: isLimitReached ? 'rgba(239,68,68,.03)' : 'var(--bg-white)', resize: 'vertical', outline: 'none', transition: 'border-color .15s', boxSizing: 'border-box', cursor: isLimitReached ? 'not-allowed' : 'text' }}
          />
          <p style={{ fontSize: '0.71rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Più dettagli fornisci (zona, budget, obiettivo, mq minimi) → migliore sarà la ricerca &nbsp;·&nbsp; Ctrl+Enter per inviare
          </p>
        </div>

        {(localError || (error && error !== 'errorLimit' && !loading)) && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 'var(--r-md)', color: 'var(--c-red)', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{localError || error}</span>
            {localError && (
              <Button variant="danger" size="sm" onClick={() => setLocalError(null)}>Riprova</Button>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {isLimitReached ? (
            <Button variant="primary" size="lg" onClick={onLimitReached}>⚡ Upgrade per continuare →</Button>
          ) : (
            <Button variant="primary" size="lg" onClick={handleSubmit} loading={loading || isPolling} disabled={query.trim().length < 15 || loading || isPolling}>
              {loading || isPolling ? 'Agenti in ricerca...' : 'Avvia Ricerca AI →'}
            </Button>
          )}
          {messages.length > 0 && !isPolling && (
            <Button variant="secondary" size="lg" onClick={() => { setMessages([]); setLastResult(null); setLocalError(null); }}>
              Nuova ricerca
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Opportunity Card ──
const OpportunityCard: React.FC<{ opp: FoundOpportunity; index: number; isBest: boolean; }> = ({ opp, index, isBest }) => {
  const score = opp.opportunity_score || 0;
  const scoreColor = score >= 8 ? '#10b981' : score >= 6 ? 'var(--c-blue)' : 'var(--c-gold)';
  return (
    <div style={{ padding: 18, position: 'relative', background: isBest ? 'linear-gradient(135deg, var(--c-navy), var(--c-navy-light))' : 'var(--bg-white)', border: isBest ? '2px solid rgba(201,168,76,.3)' : '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: isBest ? 'var(--shadow-md)' : 'var(--shadow-sm)' }}>
      {isBest && <div style={{ position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)', background: 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))', color: 'var(--c-navy-dark)', padding: '2px 12px', borderRadius: 'var(--r-full)', fontSize: '0.65rem', fontWeight: 800, whiteSpace: 'nowrap' }}>★ Consigliata</div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: isBest ? 8 : 0, marginBottom: 8 }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: isBest ? 'rgba(255,255,255,.45)' : 'var(--text-muted)' }}>#{index + 1} · {opp.zone}</span>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 700, color: scoreColor }}>{score.toFixed(1)}<span style={{ fontSize: '0.6rem', fontWeight: 400, color: isBest ? 'rgba(255,255,255,.4)' : 'var(--text-muted)' }}>/10</span></span>
      </div>
      <p style={{ fontSize: '0.87rem', fontWeight: 700, color: isBest ? '#fff' : 'var(--text-navy)', marginBottom: 10, lineHeight: 1.3 }}>{opp.title}</p>
      {[
        ['💶', opp.estimated_price_range],
        ['📐', opp.size_range],
        ['🏗️', opp.condition],
        ['📊', `€${opp.price_per_sqm?.toLocaleString('it-IT')}/mq`],
        ['📈', opp.roi_potential],
        ['🔨', opp.renovation_estimate],
      ].map(([icon, val]) => (
        <div key={String(icon)} style={{ display: 'flex', gap: 6, marginBottom: 3, fontSize: '0.77rem' }}>
          <span>{icon}</span><span style={{ color: isBest ? 'rgba(255,255,255,.72)' : 'var(--text-secondary)' }}>{val}</span>
        </div>
      ))}
      {opp.key_pros?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {opp.key_pros.map((p) => <div key={p} style={{ fontSize: '0.72rem', color: isBest ? 'rgba(255,255,255,.6)' : '#10b981', marginBottom: 2 }}>✓ {p}</div>)}
        </div>
      )}
      {opp.key_cons?.length > 0 && (
        <div style={{ marginTop: 5 }}>
          {opp.key_cons.map((c) => <div key={c} style={{ fontSize: '0.72rem', color: isBest ? 'rgba(255,255,255,.45)' : 'var(--c-red)', marginBottom: 2 }}>⚠️ {c}</div>)}
        </div>
      )}
    </div>
  );
};