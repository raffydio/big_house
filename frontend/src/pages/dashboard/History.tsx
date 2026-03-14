// src/pages/dashboard/History.tsx
// Storico sessioni dell'utente con download docx e eliminazione

import React, { useEffect, useState } from 'react';
import type { Lang, ChatSession, ChatFeature } from '../../types';
import { t } from '../../i18n/translations';
import { generateDocx } from '../../hooks/useStorage';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';

interface HistoryProps {
  lang: Lang;
  sessions: ChatSession[];
  onDeleteSession: (id: string) => void;
  onNavigate: (v: any) => void;
}

const FEATURE_LABEL: Record<ChatFeature, string> = {
  deepresearch: 'Deep Research',
  calcola: 'Calcola ROI',
};

const FEATURE_COLOR: Record<ChatFeature, string> = {
  deepresearch: 'var(--c-blue)',
  calcola:      'var(--c-green)',
};

export const HistoryPage: React.FC<HistoryProps> = ({
  lang, sessions, onDeleteSession, onNavigate,
}) => {
  const [filter, setFilter] = useState<ChatFeature | 'all'>('all');
  const [downloading, setDownloading] = useState<string | null>(null);

  const filtered = filter === 'all'
    ? sessions
    : sessions.filter((s) => s.feature === filter);

  const handleDownload = async (session: ChatSession) => {
    setDownloading(session.id);
    const aiMsg = session.messages.find((m) => m.role === 'assistant');
    if (!aiMsg) { setDownloading(null); return; }

    await generateDocx(
      session.title || 'Report Big House AI',
      [
        { heading: 'Query',    content: session.messages.find((m) => m.role === 'user')?.content ?? '' },
        { heading: 'Risposta', content: aiMsg.content },
      ]
    );
    setDownloading(null);
  };

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 860, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.4rem, 3vw, 2rem)', color: 'var(--text-navy)', marginBottom: 6 }}>
            {t(lang, 'navHistory')}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            {sessions.length} sessioni salvate nel tuo cloud
          </p>
        </div>

        {/* Filtri */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(['all', 'deepresearch', 'calcola'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--r-full)',
                border: '1.5px solid',
                cursor: 'pointer',
                fontFamily: 'var(--font-body)',
                fontSize: '0.8rem',
                fontWeight: 600,
                transition: 'all var(--dur-fast)',
                borderColor: filter === f ? 'var(--c-blue)' : 'var(--border)',
                background:  filter === f ? 'var(--c-blue)' : 'var(--bg-white)',
                color:       filter === f ? '#fff' : 'var(--text-secondary)',
              }}
            >
              {f === 'all' ? 'Tutte' : FEATURE_LABEL[f]}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions list */}
      {filtered.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          padding: '60px 24px', gap: 14, textAlign: 'center',
        }}>
          <span style={{ fontSize: 40, opacity: .25 }}>◷</span>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Nessuna sessione ancora. Avvia una Deep Research o un Calcolo ROI.
          </p>
          <Button variant="primary" size="md" onClick={() => onNavigate('deepresearch')}>
            Inizia ora →
          </Button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filtered.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              downloading={downloading === session.id}
              onDownload={() => handleDownload(session)}
              onDelete={() => onDeleteSession(session.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ── Session card ──
const SessionCard: React.FC<{
  session: ChatSession;
  downloading: boolean;
  onDownload: () => void;
  onDelete: () => void;
}> = ({ session, downloading, onDownload, onDelete }) => {
  const [expanded, setExpanded] = useState(false);
  const color = FEATURE_COLOR[session.feature];
  const label = FEATURE_LABEL[session.feature];
  const aiMsg = session.messages.find((m) => m.role === 'assistant');
  const date  = new Date(session.created_at).toLocaleDateString('it-IT', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <Card style={{ transition: 'all var(--dur-base)' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Feature badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '2px 10px',
            background: `${color}12`,
            border: `1px solid ${color}25`,
            borderRadius: 'var(--r-full)',
            fontSize: '0.68rem',
            fontWeight: 700,
            color,
            letterSpacing: '.04em',
            marginBottom: 6,
          }}>
            {session.feature === 'deepresearch' ? '⬡' : '◎'} {label}
          </div>

          <h3 style={{
            fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-navy)',
            fontFamily: 'var(--font-body)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {session.title || 'Sessione senza titolo'}
          </h3>

          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>{date}</p>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button
            onClick={onDownload}
            disabled={downloading}
            title="Scarica .docx"
            style={{
              padding: '6px 12px',
              background: 'rgba(37,99,235,.07)',
              border: '1px solid rgba(37,99,235,.2)',
              borderRadius: 'var(--r-sm)',
              cursor: downloading ? 'not-allowed' : 'pointer',
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--c-blue)',
              fontFamily: 'var(--font-body)',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              opacity: downloading ? 0.6 : 1,
            }}
          >
            {downloading ? <span className="spinner spinner--dark" style={{ width: 12, height: 12 }} /> : '📄'}
            .docx
          </button>

          <button
            onClick={() => setExpanded((e) => !e)}
            style={{
              padding: '6px 10px',
              background: 'var(--bg-muted)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-sm)',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-body)',
              color: 'var(--text-secondary)',
            }}
          >
            {expanded ? '▲' : '▼'}
          </button>

          <button
            onClick={onDelete}
            title="Elimina"
            style={{
              padding: '6px 10px',
              background: 'rgba(239,68,68,.06)',
              border: '1px solid rgba(239,68,68,.15)',
              borderRadius: 'var(--r-sm)',
              cursor: 'pointer',
              fontSize: '0.75rem',
              color: 'var(--c-red)',
              fontFamily: 'var(--font-body)',
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Expanded preview */}
      {expanded && aiMsg && (
        <div style={{
          marginTop: 14,
          padding: 14,
          background: 'var(--bg-muted)',
          borderRadius: 'var(--r-md)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.65,
          maxHeight: 200,
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
        }}>
          {aiMsg.content.slice(0, 600)}{aiMsg.content.length > 600 ? '…' : ''}
        </div>
      )}
    </Card>
  );
};
