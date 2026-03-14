// src/pages/dashboard/StoragePage.tsx
// Pagina gestione storage: cerchio, lista file, download zip

import React, { useEffect } from 'react';
import type { Lang, User, StorageInfo, ChatSession } from '../../types';
import { t } from '../../i18n/translations';
import { StorageIndicator } from '../../components/StorageIndicator';
import { Card, TitledCard } from '../../components/ui/Card';

interface StoragePageProps {
  lang: Lang;
  user: User | null;
  storageInfo: StorageInfo | null;
  sessions: ChatSession[];
  loadingStorage: boolean;
  onFetchStorage: () => void;
  onDownloadZip: () => void;
  onDeleteSession: (id: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(3)} GB`;
}

export const StoragePage: React.FC<StoragePageProps> = ({
  lang, user, storageInfo, sessions, loadingStorage,
  onFetchStorage, onDownloadZip, onDeleteSession,
}) => {
  useEffect(() => { onFetchStorage(); }, []);

  const totalSessions = sessions.length;
  const drSessions    = sessions.filter((s) => s.feature === 'deepresearch').length;
  const calcSessions  = sessions.filter((s) => s.feature === 'calcola').length;

  return (
    <div style={{ padding: 'clamp(16px, 4vw, 32px)', maxWidth: 860, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(1.4rem, 3vw, 2rem)',
          color: 'var(--text-navy)',
          marginBottom: 6,
        }}>
          {t(lang, 'navStorage')}
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Il tuo cloud personale — max 2 GB
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, alignItems: 'start' }}>
        {/* Storage circle card */}
        <Card style={{ minWidth: 220, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32, gap: 0 }}>
          <StorageIndicator
            storageInfo={storageInfo}
            loading={loadingStorage}
            onDownloadZip={onDownloadZip}
          />
        </Card>

        {/* Stats + file list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <StatCard label="Sessioni totali"     value={String(totalSessions)}  icon="◷" color="var(--c-blue)" />
            <StatCard label="Deep Research"        value={String(drSessions)}     icon="⬡" color="var(--c-blue)" />
            <StatCard label="Calcoli ROI"          value={String(calcSessions)}   icon="◎" color="var(--c-green)" />
          </div>

          {/* File list */}
          <TitledCard title="Sessioni salvate" subtitle={`${totalSessions} file`}>
            {sessions.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '20px 0' }}>
                Nessuna sessione salvata.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 320, overflowY: 'auto' }}>
                {sessions.slice(0, 30).map((s) => {
                  const size = s.messages.reduce((acc, m) => acc + m.content.length * 2, 0);
                  const date = new Date(s.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
                  const color = s.feature === 'deepresearch' ? 'var(--c-blue)' : 'var(--c-green)';

                  return (
                    <div key={s.id} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 12px',
                      background: 'var(--bg-muted)',
                      borderRadius: 'var(--r-md)',
                    }}>
                      <span style={{ fontSize: 16, color }}>{s.feature === 'deepresearch' ? '⬡' : '◎'}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: '0.82rem',
                          fontWeight: 600,
                          color: 'var(--text-navy)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {s.title || 'Sessione'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {date} · {formatBytes(size)}
                        </div>
                      </div>
                      <button
                        onClick={() => onDeleteSession(s.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--text-muted)',
                          fontSize: 16,
                          padding: 4,
                          borderRadius: 'var(--r-sm)',
                          flexShrink: 0,
                          transition: 'color var(--dur-fast)',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--c-red)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
                        title="Elimina sessione"
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </TitledCard>
        </div>
      </div>

      {/* Responsive override */}
      <style>{`
        @media (max-width: 640px) {
          .storage-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: string; icon: string; color: string }> = ({
  label, value, icon, color,
}) => (
  <div style={{
    padding: '16px 14px',
    background: 'var(--bg-white)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
    textAlign: 'center',
    boxShadow: 'var(--shadow-sm)',
  }}>
    <div style={{ fontSize: 18, color, marginBottom: 6 }}>{icon}</div>
    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-navy)', marginBottom: 4 }}>
      {value}
    </div>
    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{label}</div>
  </div>
);
