// src/pages/dashboard/CalcROI.tsx  v2
// Confronto ROI fino a 5 immobili con tabella comparativa

import React, { useState, useRef, useEffect } from 'react';
import type { Lang, ChatMessage, ChatSession } from '../../types';
import { useApi } from '../../hooks/useApi';
import { generateDocx } from '../../hooks/useStorage';
import { Button } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Input';
import { Card } from '../../components/ui/Card';
import { AgentThinking } from '../../components/AgentThinking';
import { ChatBubble } from '../../components/ChatBubble';

// ── Tipi v2 ──────────────────────────────────────────────
interface PropertyInput {
  label: string;
  address: string;
  purchase_price: number;
  size_sqm: number;
  condition: string;
  rooms: number;
  floor?: number;
  has_elevator: boolean;
  renovation_budget?: number;
  mortgage_rate?: number;
  mortgage_years?: number;
  down_payment_pct?: number;
  notes?: string;
}

interface RenovationScenario {
  name: string;
  renovation_cost: number;
  duration_months: number;
  estimated_value_after: number;
  estimated_rent_after: number;
  roi_percent: number;
  payback_years: number;
  risk_level: string;
  description: string;
}

interface PropertyROIResult {
  label: string;
  address: string;
  purchase_price: number;
  price_per_sqm: number;
  scenarios: RenovationScenario[];
  best_scenario: string;
  total_investment_mid: number;
  net_roi_mid: number;
  payback_mid: number;
  risk_summary: string;
  rank: number;
}

interface CompareROIResponse {
  results: PropertyROIResult[];
  winner_label: string;
  winner_reason: string;
  comparison_summary: string;
  market_notes: string;
  disclaimer: string;
  remaining_usage: number;
}

interface CompareROIRequest {
  properties: PropertyInput[];
  goal: string;
}

interface CalcROIProps {
  lang: Lang;
  user: { name: string; plan: string } | null;
  onLimitReached: () => void;
  onUsageIncrement: () => void;
  onSaveSession: (session: ChatSession) => void;
}

// ── Default property ──────────────────────────────────────
const DEFAULT_PROP = (): PropertyInput => ({
  label: '',
  address: '',
  purchase_price: 0,
  size_sqm: 0,
  condition: 'da ristrutturare',
  rooms: 3,
  has_elevator: false,
  mortgage_rate: 3.5,
  mortgage_years: 20,
  down_payment_pct: 0.20,
});

const GOAL_OPTIONS = [
  { value: 'flipping',       label: '🔄 Flipping — Vendita post-ristrutturazione' },
  { value: 'affitto_lungo',  label: '🏠 Affitto a lungo termine' },
  { value: 'affitto_breve',  label: '🛎️ Affitto breve (Airbnb/Booking)' },
  { value: 'prima_casa',     label: '🔑 Prima casa con valorizzazione' },
];

const CONDITION_OPTIONS = [
  { value: 'ottimo stato',      label: 'Ottimo stato' },
  { value: 'buono stato',       label: 'Buono stato' },
  { value: 'da rinnovare',      label: 'Da rinnovare' },
  { value: 'da ristrutturare',  label: 'Da ristrutturare' },
];

const fmt = (n: number) => n.toLocaleString('it-IT', { maximumFractionDigits: 0 });
const fmtPct = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;

function buildResultText(r: CompareROIResponse): string {
  const lines = [
    `🏆 VINCITORE: ${r.winner_label}`,
    r.winner_reason, '',
    '── CONFRONTO IMMOBILI ──',
    ...r.results.map((res) =>
      `#${res.rank} ${res.label} — ${res.address}\n` +
      `Prezzo: €${fmt(res.purchase_price)} | €${fmt(res.price_per_sqm)}/mq\n` +
      `ROI medio: ${fmtPct(res.net_roi_mid)} | Payback: ${res.payback_mid.toFixed(1)} anni\n` +
      `Investimento totale: €${fmt(res.total_investment_mid)}\n` +
      `Scenario consigliato: ${res.best_scenario}\n` +
      `Rischi: ${res.risk_summary}`
    ),
    '', r.comparison_summary,
    '', r.market_notes,
    '', r.disclaimer,
  ];
  return lines.join('\n');
}

export const CalcROIPage: React.FC<CalcROIProps> = ({
  lang, user, onLimitReached, onUsageIncrement, onSaveSession,
}) => {
  const [properties, setProperties] = useState<PropertyInput[]>([{ ...DEFAULT_PROP(), label: 'Immobile 1' }]);
  const [activeTab, setActiveTab]   = useState(0);
  const [goal, setGoal]             = useState('flipping');
  const [messages, setMessages]     = useState<ChatMessage[]>([]);
  const [lastResult, setLastResult] = useState<CompareROIResponse | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { loading, error, call } = useApi<CompareROIResponse, CompareROIRequest>('/features/calculate');

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const addMsg = (msg: Omit<ChatMessage, 'id' | 'timestamp'>): ChatMessage => {
    const full = { ...msg, id: crypto.randomUUID(), timestamp: new Date().toISOString() } as ChatMessage;
    setMessages((p) => [...p, full]);
    return full;
  };

  const updateProp = (index: number, field: keyof PropertyInput, value: any) => {
    setProperties((ps) => ps.map((p, i) => i === index ? { ...p, [field]: value } : p));
  };

  const addProperty = () => {
    if (properties.length >= 5) return;
    const newProp = { ...DEFAULT_PROP(), label: `Immobile ${properties.length + 1}` };
    setProperties((ps) => [...ps, newProp]);
    setActiveTab(properties.length);
  };

  const removeProperty = (index: number) => {
    if (properties.length <= 1) return;
    setProperties((ps) => ps.filter((_, i) => i !== index));
    setActiveTab(Math.max(0, activeTab - 1));
  };

  const handleSubmit = async () => {
    const valid = properties.every(p => p.address.trim() && p.purchase_price > 0 && p.size_sqm > 0 && p.label.trim());
    if (!valid || loading) return;

    const label = properties.length === 1
      ? `ROI: ${properties[0].label}`
      : `Confronto ${properties.length} immobili`;
    const userMsg = addMsg({ role: 'user', content: label, feature: 'calcola' });

    const result = await call({ properties, goal });

    if (!result) {
      if (error === 'errorLimit') onLimitReached();
      else addMsg({ role: 'assistant', content: `Errore: ${error || 'Errore generico'}`, feature: 'calcola' });
      return;
    }

    onUsageIncrement();
    setLastResult(result);
    const text = buildResultText(result);
    const docxName = `calc_${Date.now()}.docx`;
    const aiMsg = addMsg({ role: 'assistant', content: text, feature: 'calcola', docx_filename: user?.plan !== 'free' ? docxName : undefined });
    onSaveSession({ id: crypto.randomUUID(), feature: 'calcola', title: label.slice(0, 60), created_at: new Date().toISOString(), messages: [userMsg, aiMsg], docx_filename: user?.plan !== 'free' ? docxName : undefined });
  };

  const handleDownloadDocx = async () => {
    if (!lastResult) return;
    await generateDocx('Calcola ROI — Confronto Immobili', [
      { heading: 'Vincitore', content: `${lastResult.winner_label}\n${lastResult.winner_reason}` },
      { heading: 'Confronto', content: lastResult.comparison_summary },
      { heading: 'Note di Mercato', content: lastResult.market_notes },
      { heading: 'Disclaimer', content: lastResult.disclaimer },
    ]);
  };

  const isValid = properties.every(p => p.address.trim() && p.purchase_price > 0 && p.size_sqm > 0 && p.label.trim());

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 960, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: 'var(--text-navy)', marginBottom: 6 }}>
          Calcola ROI — Confronto Immobili
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Inserisci fino a 5 immobili già trovati — gli agenti calcolano e confrontano i ROI affiancati
        </p>
      </div>

      {/* Chat history */}
      {messages.length > 0 && (
        <div style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 18, maxHeight: 480, overflowY: 'auto', padding: 20, background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}>
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} userName={user?.name ?? 'Tu'} onDownloadDocx={handleDownloadDocx} />
          ))}
          {loading && <AgentThinking feature="calcola" visible={loading} />}
          <div ref={chatEndRef} />
        </div>
      )}
      {loading && messages.length === 0 && <div style={{ marginBottom: 24 }}><AgentThinking feature="calcola" visible={loading} /></div>}

      {/* Tabella comparativa risultati */}
      {lastResult && !loading && <ComparisonTable result={lastResult} />}

      {/* ── INPUT FORM ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Obiettivo investimento */}
        <Card>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
            Obiettivo dell'investimento
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {GOAL_OPTIONS.map((g) => (
              <button key={g.value} onClick={() => setGoal(g.value)}
                style={{ padding: '8px 14px', borderRadius: 'var(--r-full)', border: `1.5px solid ${goal === g.value ? 'var(--c-blue)' : 'var(--border)'}`, background: goal === g.value ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: goal === g.value ? 700 : 400, color: goal === g.value ? 'var(--c-blue)' : 'var(--text-secondary)', fontFamily: 'var(--font-body)', transition: 'all .15s' }}>
                {g.label}
              </button>
            ))}
          </div>
        </Card>

        {/* Tab selector immobili */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          {properties.map((p, i) => (
            <button key={i} onClick={() => setActiveTab(i)}
              style={{ padding: '7px 14px', borderRadius: 'var(--r-md)', border: `2px solid ${activeTab === i ? 'var(--c-blue)' : 'var(--border)'}`, background: activeTab === i ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.82rem', fontWeight: activeTab === i ? 700 : 400, color: activeTab === i ? 'var(--c-blue)' : 'var(--text-secondary)', fontFamily: 'var(--font-body)', transition: 'all .15s' }}>
              {p.label || `Immobile ${i + 1}`}
              {properties.length > 1 && (
                <span onClick={(e) => { e.stopPropagation(); removeProperty(i); }}
                  style={{ marginLeft: 6, color: 'var(--c-red)', fontWeight: 700, fontSize: '0.9rem', lineHeight: 1 }}>×</span>
              )}
            </button>
          ))}
          {properties.length < 5 && (
            <button onClick={addProperty}
              style={{ padding: '7px 14px', borderRadius: 'var(--r-md)', border: '2px dashed var(--border)', background: 'none', cursor: 'pointer', fontSize: '0.82rem', color: 'var(--c-blue)', fontFamily: 'var(--font-body)', fontWeight: 600 }}>
              + Aggiungi ({properties.length}/5)
            </button>
          )}
        </div>

        {/* Form immobile attivo */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Input label="Nome immobile (es. Via Roma Milano)" placeholder="Immobile 1"
              value={properties[activeTab]?.label || ''}
              onChange={(e) => updateProp(activeTab, 'label', e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
            {/* Indirizzo — full width */}
            <div style={{ gridColumn: '1 / -1' }}>
              <Input label="Indirizzo completo" placeholder="Via Toledo 120, Napoli"
                value={properties[activeTab]?.address || ''}
                onChange={(e) => updateProp(activeTab, 'address', e.target.value)}
              />
            </div>

            <Input label="Prezzo richiesto (€)" type="number" placeholder="250000"
              value={properties[activeTab]?.purchase_price || ''}
              onChange={(e) => updateProp(activeTab, 'purchase_price', Number(e.target.value))}
            />
            <Input label="Superficie (mq)" type="number" placeholder="80"
              value={properties[activeTab]?.size_sqm || ''}
              onChange={(e) => updateProp(activeTab, 'size_sqm', Number(e.target.value))}
            />
            <Input label="Locali" type="number" placeholder="3"
              value={properties[activeTab]?.rooms || ''}
              onChange={(e) => updateProp(activeTab, 'rooms', Number(e.target.value))}
            />
            <Select label="Condizioni"
              value={properties[activeTab]?.condition || 'da ristrutturare'}
              options={CONDITION_OPTIONS}
              onChange={(e) => updateProp(activeTab, 'condition', e.target.value)}
            />
            <Input label="Piano (opz.)" type="number" placeholder="2"
              value={properties[activeTab]?.floor || ''}
              onChange={(e) => updateProp(activeTab, 'floor', Number(e.target.value) || undefined)}
            />

            {/* Ascensore toggle */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Ascensore</label>
              <button onClick={() => updateProp(activeTab, 'has_elevator', !properties[activeTab]?.has_elevator)}
                style={{ padding: '10px 14px', borderRadius: 'var(--r-md)', border: `1.5px solid ${properties[activeTab]?.has_elevator ? 'var(--c-blue)' : 'var(--border)'}`, background: properties[activeTab]?.has_elevator ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.85rem', fontFamily: 'var(--font-body)', fontWeight: 600, color: properties[activeTab]?.has_elevator ? 'var(--c-blue)' : 'var(--text-muted)' }}>
                {properties[activeTab]?.has_elevator ? '✓ Presente' : '✗ Assente'}
              </button>
            </div>

            <Input label="Budget ristrutturazione (opz.)" type="number" placeholder="60000"
              value={properties[activeTab]?.renovation_budget || ''}
              onChange={(e) => updateProp(activeTab, 'renovation_budget', Number(e.target.value) || undefined)}
            />
            <Input label="Tasso mutuo % (opz.)" type="number" step="0.1" placeholder="3.5"
              value={properties[activeTab]?.mortgage_rate || ''}
              onChange={(e) => updateProp(activeTab, 'mortgage_rate', Number(e.target.value))}
            />

            {/* Note — full width */}
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Note aggiuntive (opz.)</label>
              <textarea
                value={properties[activeTab]?.notes || ''}
                onChange={(e) => updateProp(activeTab, 'notes', e.target.value)}
                placeholder="Vincoli, opportunità, stato impianti, vicinanza servizi..."
                rows={2}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1.5px solid var(--border)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', resize: 'vertical', outline: 'none', boxSizing: 'border-box', color: 'var(--text-primary)', background: 'var(--bg-white)' }}
              />
            </div>
          </div>
        </Card>

        {error && error !== 'errorLimit' && !loading && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 'var(--r-md)', color: 'var(--c-red)', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <Button variant="primary" size="lg" onClick={handleSubmit} loading={loading} disabled={!isValid || loading}>
            {loading ? 'Agenti in calcolo...' : properties.length > 1 ? `Confronta ${properties.length} Immobili →` : 'Calcola ROI →'}
          </Button>
          {messages.length > 0 && (
            <Button variant="secondary" size="lg" onClick={() => { setMessages([]); setLastResult(null); }}>
              Nuova sessione
            </Button>
          )}
          {!isValid && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              ⚠️ Completa indirizzo, prezzo e superficie per ogni immobile
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Tabella comparativa ───────────────────────────────────
const ComparisonTable: React.FC<{ result: CompareROIResponse }> = ({ result }) => {
  const [activeScenario, setActiveScenario] = useState<'Conservativo' | 'Medio' | 'Premium'>('Medio');

  return (
    <div style={{ marginBottom: 28 }}>
      {/* Winner banner */}
      <div style={{ padding: '14px 20px', background: 'linear-gradient(135deg, var(--c-navy), var(--c-navy-light))', borderRadius: 'var(--r-lg)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 24 }}>🏆</span>
        <div>
          <p style={{ color: 'var(--c-gold)', fontWeight: 700, fontSize: '0.82rem', marginBottom: 2 }}>Immobile Consigliato</p>
          <p style={{ color: '#fff', fontWeight: 700, fontSize: '1rem' }}>{result.winner_label}</p>
          <p style={{ color: 'rgba(255,255,255,.65)', fontSize: '0.78rem', marginTop: 2 }}>{result.winner_reason}</p>
        </div>
      </div>

      {/* Scenario tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {(['Conservativo', 'Medio', 'Premium'] as const).map((sc) => (
          <button key={sc} onClick={() => setActiveScenario(sc)}
            style={{ padding: '6px 14px', borderRadius: 'var(--r-full)', border: `1.5px solid ${activeScenario === sc ? 'var(--c-blue)' : 'var(--border)'}`, background: activeScenario === sc ? 'rgba(37,99,235,.08)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.78rem', fontWeight: activeScenario === sc ? 700 : 400, color: activeScenario === sc ? 'var(--c-blue)' : 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
            {sc}
          </button>
        ))}
      </div>

      {/* Cards affiancate */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(result.results.length, 3)}, 1fr)`, gap: 12, overflowX: 'auto' }}>
        {result.results.map((res) => {
          const sc = res.scenarios.find(s => s.name === activeScenario) || res.scenarios[1] || res.scenarios[0];
          const isWinner = res.label === result.winner_label;
          const roiColor = (sc?.roi_percent || 0) > 0 ? '#10b981' : 'var(--c-red)';

          return (
            <div key={res.label} style={{ padding: 16, background: isWinner ? 'linear-gradient(135deg, rgba(26,58,110,.05), rgba(37,99,235,.05))' : 'var(--bg-white)', border: `${isWinner ? '2' : '1'}px solid ${isWinner ? 'var(--c-blue)' : 'var(--border)'}`, borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-sm)', position: 'relative' }}>
              {isWinner && <div style={{ position: 'absolute', top: -8, right: 12, background: 'var(--c-blue)', color: '#fff', padding: '1px 10px', borderRadius: 'var(--r-full)', fontSize: '0.62rem', fontWeight: 700 }}>🏆 #1</div>}

              <div style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--text-muted)', marginBottom: 4 }}>#{res.rank}</div>
              <p style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-navy)', marginBottom: 2, lineHeight: 1.3 }}>{res.label}</p>
              <p style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginBottom: 12 }}>{res.address}</p>

              {/* ROI big number */}
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: roiColor, marginBottom: 10 }}>
                {fmtPct(sc?.roi_percent || 0)}
              </div>

              {[
                ['Prezzo acquisto', `€${fmt(res.purchase_price)}`],
                ['€/mq', `€${fmt(res.price_per_sqm)}`],
                ['Costo rinnovo', `€${fmt(sc?.renovation_cost || 0)}`],
                ['Valore post', `€${fmt(sc?.estimated_value_after || 0)}`],
                ['Affitto/mese', `€${fmt(sc?.estimated_rent_after || 0)}`],
                ['Payback', `${(sc?.payback_years || 0).toFixed(1)} anni`],
                ['Rischio', sc?.risk_level || '—'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: 4, borderBottom: '1px solid var(--border)', paddingBottom: 4 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-navy)' }}>{v}</span>
                </div>
              ))}

              <p style={{ fontSize: '0.71rem', color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.5 }}>
                {res.risk_summary}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
