// src/pages/dashboard/CalcROI.tsx v5 (Async + Plain Text Output Fix)
import React, { useState, useRef, useEffect } from 'react';
import type { Lang, ChatMessage, ChatSession } from '../../types';
import { useApi } from '../../hooks/useApi';
import { generateDocx } from '../../hooks/useStorage';
import { Button } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Input';
import { Card } from '../../components/ui/Card';
import { ChatBubble } from '../../components/ChatBubble';

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

// NUOVA STRUTTURA RISULTATO (Allineata al backend testo puro)
interface CompareROIResponse {
  summary: string;
  investment_goal: string;
  investment_goal_label: string;
  properties_count: number;
  market_analysis: string;
  financial_analysis: string;
  recommended_scenario: string;
  remaining_usage: number;
  llm_used: string;
}

interface JobInitResponse {
  job_id: string;
  status: string;
  poll_url: string;
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

const DEFAULT_PROP = (): PropertyInput => ({
  label: '', address: '', purchase_price: 0, size_sqm: 0, condition: 'da ristrutturare', rooms: 3, has_elevator: false, mortgage_rate: 3.5, mortgage_years: 20, down_payment_pct: 0.20,
});

const GOAL_OPTIONS = [
  { value: 'flipping', label: ' Flipping — Vendita post-ristrutturazione' },
  { value: 'affitto_lungo', label: ' Affitto a lungo termine' },
  { value: 'affitto_breve', label: ' Affitto breve (Airbnb/Booking)' },
  { value: 'prima_casa', label: ' Prima casa con valorizzazione' },
];

const CONDITION_OPTIONS = [
  { value: 'ottimo stato', label: 'Ottimo stato' }, { value: 'buono stato', label: 'Buono stato' }, { value: 'da rinnovare', label: 'Da rinnovare' }, { value: 'da ristrutturare', label: 'Da ristrutturare' },
];

// Funzioni di formattazione sicure (non crashano se n è undefined)
const fmt = (n?: number | null) => (n || 0).toLocaleString('it-IT', { maximumFractionDigits: 0 });
const fmtPct = (n?: number | null) => `${(n || 0) > 0 ? '+' : ''}${(n || 0).toFixed(1)}%`;

function buildResultText(r: CompareROIResponse): string {
  return [
    '── SINTESI ──', r.summary, '',
    '── ANALISI DI MERCATO ──', r.market_analysis, '',
    '── ANALISI FINANZIARIA ──', r.financial_analysis, '',
    '── RACCOMANDAZIONE FINALE ──', r.recommended_scenario,
  ].filter(Boolean).join('\n');
}

export const CalcROIPage: React.FC<CalcROIProps> = ({
  lang, user, onLimitReached, onUsageIncrement, onSaveSession,
}) => {
  const [properties, setProperties] = useState<PropertyInput[]>([{ ...DEFAULT_PROP(), label: 'Immobile 1' }]);
  const [activeTab, setActiveTab] = useState(0);
  const [goal, setGoal] = useState('flipping');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResult, setLastResult] = useState<CompareROIResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const [isPolling, setIsPolling] = useState(false);
  const [pollData, setPollData] = useState({ progress: 0, step: 'In coda...' });

  const chatEndRef = useRef<HTMLDivElement>(null);
  const { loading, error, call } = useApi<JobInitResponse, CompareROIRequest>('/features/calculate');

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isPolling]);

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
    setProperties((ps) => [...ps, { ...DEFAULT_PROP(), label: `Immobile ${properties.length + 1}` }]);
    setActiveTab(properties.length);
  };

  const removeProperty = (index: number) => {
    if (properties.length <= 1) return;
    setProperties((ps) => ps.filter((_, i) => i !== index));
    setActiveTab(Math.max(0, activeTab - 1));
  };

  const startPolling = (jobId: string, label: string, userMsg: ChatMessage) => {
    setIsPolling(true);
    setPollData({ progress: 0, step: 'In coda...' });
    setLocalError(null);
    
    const token = localStorage.getItem('bh_token');
    const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
    
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        
        setPollData({ progress: data.progress || 0, step: data.current_step || 'Calcolo in corso...' });

        if (data.status === 'completed') {
          clearInterval(interval);
          setIsPolling(false);
          setLastResult(data.result);
          onUsageIncrement();
          
          const text = buildResultText(data.result);
          const docxName = user?.plan !== 'free' ? `calc_${Date.now()}.docx` : undefined;
          const aiMsg = addMsg({ role: 'assistant', content: text, feature: 'calcola', docx_filename: docxName });
          
          onSaveSession({ id: crypto.randomUUID(), feature: 'calcola', title: label.slice(0, 60), created_at: new Date().toISOString(), messages: [userMsg, aiMsg], docx_filename: docxName });
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setIsPolling(false);
          setLocalError(data.error || "Errore durante il calcolo del ROI.");
        }
      } catch (err) { console.error("Polling error", err); }
    }, 5000);
  };

  const handleSubmit = async () => {
    const valid = properties.every(p => p.address.trim() && p.purchase_price > 0 && p.size_sqm > 0 && p.label.trim());
    if (!valid || loading || isPolling) return;
    setLocalError(null);

    const label = properties.length === 1 ? `ROI: ${properties[0].label}` : `Confronto ${properties.length} immobili`;
    const userMsg = addMsg({ role: 'user', content: label, feature: 'calcola' });

    const initResult = await call({ properties, goal });

    if (!initResult) {
      if (error === 'errorLimit' || (error && error.includes('429'))) onLimitReached();
      else setLocalError(error || 'Errore di connessione al server.');
      return;
    }

    if (initResult.remaining_usage <= 0) onLimitReached();
    startPolling(initResult.job_id, label, userMsg);
  };

  const handleDownloadDocx = async () => {
    if (!lastResult) return;
    await generateDocx('Calcola ROI — Confronto Immobili', [
      { heading: 'Sintesi', content: lastResult.summary },
      { heading: 'Analisi di Mercato', content: lastResult.market_analysis },
      { heading: 'Analisi Finanziaria', content: lastResult.financial_analysis },
      { heading: 'Raccomandazione Finale', content: lastResult.recommended_scenario },
    ]);
  };
  
  const handleNewAnalysis = () => {
    setMessages([]);
    setLastResult(null);
    setProperties([{ ...DEFAULT_PROP(), label: 'Immobile 1' }]);
    setActiveTab(0);
    setGoal('flipping');
  };

  const isValid = properties.every(p => p.address.trim() && p.purchase_price > 0 && p.size_sqm > 0 && p.label.trim());

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 960, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: 'var(--text-navy)', marginBottom: 6 }}>Calcola ROI — Confronto Immobili</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Inserisci fino a 5 immobili già trovati — gli agenti calcolano e confrontano i ROI affiancati</p>
      </div>

      {messages.length > 0 && (
        <div style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 18, maxHeight: 480, overflowY: 'auto', padding: 20, background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}>
          {messages.map((msg) => <ChatBubble key={msg.id} message={msg} userName={user?.name ?? 'Tu'} onDownloadDocx={handleDownloadDocx} />)}
          
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

      {/* Blocco Azioni post-analisi */}
      {lastResult && !isPolling && (
        <div style={{ marginTop: 24, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <Button variant="primary" size="lg" onClick={handleNewAnalysis}>Nuova Analisi</Button>
          {user?.plan !== 'free' && <Button variant="secondary" size="lg" onClick={handleDownloadDocx}>Scarica Report .docx</Button>}
        </div>
      )}

      {/* ── INPUT FORM (scompare dopo l'analisi) ── */}
      {!lastResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>Obiettivo dell'investimento</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {GOAL_OPTIONS.map((g) => (
                <button key={g.value} onClick={() => setGoal(g.value)} style={{ padding: '8px 14px', borderRadius: 'var(--r-full)', border: `1.5px solid ${goal === g.value ? 'var(--c-blue)' : 'var(--border)'}`, background: goal === g.value ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: goal === g.value ? 700 : 400, color: goal === g.value ? 'var(--c-blue)' : 'var(--text-secondary)', fontFamily: 'var(--font-body)', transition: 'all .15s' }}>{g.label}</button>
              ))}
            </div>
          </Card>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {properties.map((p, i) => (
              <button key={i} onClick={() => setActiveTab(i)} style={{ padding: '7px 14px', borderRadius: 'var(--r-md)', border: `2px solid ${activeTab === i ? 'var(--c-blue)' : 'var(--border)'}`, background: activeTab === i ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.82rem', fontWeight: activeTab === i ? 700 : 400, color: activeTab === i ? 'var(--c-blue)' : 'var(--text-secondary)', fontFamily: 'var(--font-body)', transition: 'all .15s' }}>
                {p.label || `Immobile ${i + 1}`}
                {properties.length > 1 && <span onClick={(e) => { e.stopPropagation(); removeProperty(i); }} style={{ marginLeft: 6, color: 'var(--c-red)', fontWeight: 700, fontSize: '0.9rem', lineHeight: 1 }}>×</span>}
              </button>
            ))}
            {properties.length < 5 && <button onClick={addProperty} style={{ padding: '7px 14px', borderRadius: 'var(--r-md)', border: '2px dashed var(--border)', background: 'none', cursor: 'pointer', fontSize: '0.82rem', color: 'var(--c-blue)', fontFamily: 'var(--font-body)', fontWeight: 600 }}>+ Aggiungi ({properties.length}/5)</button>}
          </div>

          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Input label="Nome immobile" placeholder="Immobile 1" value={properties[activeTab]?.label || ''} onChange={(e) => updateProp(activeTab, 'label', e.target.value)} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
              <div style={{ gridColumn: '1 / -1' }}><Input label="Indirizzo completo" placeholder="Via Toledo 120, Napoli" value={properties[activeTab]?.address || ''} onChange={(e) => updateProp(activeTab, 'address', e.target.value)} /></div>
              <Input label="Prezzo richiesto (€)" type="number" placeholder="250000" value={properties[activeTab]?.purchase_price || ''} onChange={(e) => updateProp(activeTab, 'purchase_price', Number(e.target.value))} />
              <Input label="Superficie (mq)" type="number" placeholder="80" value={properties[activeTab]?.size_sqm || ''} onChange={(e) => updateProp(activeTab, 'size_sqm', Number(e.target.value))} />
              <Input label="Locali" type="number" placeholder="3" value={properties[activeTab]?.rooms || ''} onChange={(e) => updateProp(activeTab, 'rooms', Number(e.target.value))} />
              <Select label="Condizioni" value={properties[activeTab]?.condition || 'da ristrutturare'} options={CONDITION_OPTIONS} onChange={(e) => updateProp(activeTab, 'condition', e.target.value)} />
              <Input label="Piano (opz.)" type="number" placeholder="2" value={properties[activeTab]?.floor || ''} onChange={(e) => updateProp(activeTab, 'floor', Number(e.target.value) || undefined)} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Ascensore</label>
                <button onClick={() => updateProp(activeTab, 'has_elevator', !properties[activeTab]?.has_elevator)} style={{ padding: '10px 14px', borderRadius: 'var(--r-md)', border: `1.5px solid ${properties[activeTab]?.has_elevator ? 'var(--c-blue)' : 'var(--border)'}`, background: properties[activeTab]?.has_elevator ? 'rgba(37,99,235,.07)' : 'var(--bg-white)', cursor: 'pointer', fontSize: '0.85rem', fontFamily: 'var(--font-body)', fontWeight: 600, color: properties[activeTab]?.has_elevator ? 'var(--c-blue)' : 'var(--text-muted)' }}>{properties[activeTab]?.has_elevator ? '✓ Presente' : '✗ Assente'}</button>
              </div>
              <Input label="Budget ristrutturazione (opz.)" type="number" placeholder="60000" value={properties[activeTab]?.renovation_budget || ''} onChange={(e) => updateProp(activeTab, 'renovation_budget', Number(e.target.value) || undefined)} />
              <Input label="Tasso mutuo % (opz.)" type="number" step="0.1" placeholder="3.5" value={properties[activeTab]?.mortgage_rate || ''} onChange={(e) => updateProp(activeTab, 'mortgage_rate', Number(e.target.value))} />
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>Note aggiuntive (opz.)</label>
                <textarea value={properties[activeTab]?.notes || ''} onChange={(e) => updateProp(activeTab, 'notes', e.target.value)} placeholder="Vincoli, opportunità, stato impianti..." rows={2} style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1.5px solid var(--border)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', resize: 'vertical', outline: 'none', boxSizing: 'border-box', color: 'var(--text-primary)', background: 'var(--bg-white)' }} />
              </div>
            </div>
          </Card>

          {(localError || (error && error !== 'errorLimit' && !loading)) && (
            <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 'var(--r-md)', color: 'var(--c-red)', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{localError || error}</span>
              {localError && <Button variant="danger" size="sm" onClick={() => setLocalError(null)}>Riprova</Button>}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <Button variant="primary" size="lg" onClick={handleSubmit} loading={loading || isPolling} disabled={!isValid || loading || isPolling}>
              {loading || isPolling ? 'Agenti in calcolo...' : properties.length > 1 ? `Confronta ${properties.length} Immobili →` : 'Calcola ROI →'}
            </Button>
            {!isValid && <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>⚠️ Completa indirizzo, prezzo e superficie per ogni immobile</span>}
          </div>
        </div>
      )}
    </div>
  );
};