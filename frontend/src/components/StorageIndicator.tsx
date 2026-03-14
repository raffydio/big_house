// src/components/StorageIndicator.tsx
// Cerchio con GB occupati / disponibili + download zip

import React from 'react';
import type { StorageInfo } from '../types';
import { STORAGE_MAX_BYTES } from '../types';

interface StorageIndicatorProps {
  storageInfo: StorageInfo | null;
  loading?: boolean;
  onDownloadZip?: () => void;
  compact?: boolean; // versione small per sidebar/topbar
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

// SVG circular progress
const CircularProgress: React.FC<{
  percent: number;
  size: number;
  stroke: number;
  color: string;
}> = ({ percent, size, stroke, color }) => {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const filled = circ * (1 - Math.min(percent, 100) / 100);

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      {/* Track */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke="var(--bg-muted)"
        strokeWidth={stroke}
      />
      {/* Progress */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={filled}
        style={{ transition: 'stroke-dashoffset .8s ease' }}
      />
    </svg>
  );
};

function getColor(pct: number): string {
  if (pct < 60) return 'var(--c-green)';
  if (pct < 85) return 'var(--c-orange)';
  return 'var(--c-red)';
}

export const StorageIndicator: React.FC<StorageIndicatorProps> = ({
  storageInfo, loading = false, onDownloadZip, compact = false,
}) => {
  if (compact) {
    // ── Versione compatta per TopBar ──
    const pct = storageInfo ? storageInfo.used_percent : 0;
    const color = getColor(pct);
    return (
      <div
        title={storageInfo
          ? `${formatBytes(storageInfo.used_bytes)} / ${formatBytes(STORAGE_MAX_BYTES)}`
          : 'Caricamento...'}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          cursor: 'default',
        }}
      >
        <div style={{ position: 'relative', width: 28, height: 28 }}>
          <CircularProgress percent={pct} size={28} stroke={3} color={color} />
          <span style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.5rem',
            fontWeight: 700,
            color,
          }}>
            {Math.round(pct)}%
          </span>
        </div>
      </div>
    );
  }

  // ── Versione completa per pagina Storage ──
  const pct   = storageInfo ? storageInfo.used_percent : 0;
  const color = getColor(pct);
  const used  = storageInfo ? storageInfo.used_bytes : 0;
  const max   = STORAGE_MAX_BYTES;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 20,
    }}>
      {/* Big circle */}
      <div style={{ position: 'relative', width: 140, height: 140 }}>
        <CircularProgress percent={pct} size={140} stroke={10} color={color} />
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
        }}>
          {loading ? (
            <div className="spinner spinner--dark" />
          ) : (
            <>
              <span style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.6rem',
                fontWeight: 700,
                color,
                lineHeight: 1,
              }}>
                {Math.round(pct)}%
              </span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>utilizzato</span>
            </>
          )}
        </div>
      </div>

      {/* Labels */}
      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontWeight: 700,
          color: 'var(--text-navy)',
          fontSize: '1rem',
        }}>
          {formatBytes(used)}
          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
            {' '}/ {formatBytes(max)}
          </span>
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
          {formatBytes(max - used)} rimanenti
        </div>
      </div>

      {/* Warning */}
      {pct >= 85 && (
        <div style={{
          padding: '8px 14px',
          background: pct >= 95 ? 'rgba(239,68,68,.08)' : 'rgba(245,158,11,.08)',
          border: `1px solid ${pct >= 95 ? 'rgba(239,68,68,.2)' : 'rgba(245,158,11,.2)'}`,
          borderRadius: 'var(--r-md)',
          fontSize: '0.78rem',
          color: pct >= 95 ? 'var(--c-red)' : 'var(--c-orange)',
          textAlign: 'center',
        }}>
          {pct >= 95
            ? '⚠️ Spazio quasi esaurito — elimina alcuni file'
            : '⚠️ Spazio in esaurimento'}
        </div>
      )}

      {/* Download ZIP */}
      {onDownloadZip && (
        <button
          onClick={onDownloadZip}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 22px',
            background: 'var(--bg-white)',
            border: '1.5px solid var(--border)',
            borderRadius: 'var(--r-md)',
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontWeight: 600,
            color: 'var(--text-navy)',
            fontFamily: 'var(--font-body)',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all var(--dur-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.borderColor = 'var(--c-blue)';
            e.currentTarget.style.color = 'var(--c-blue)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            e.currentTarget.style.borderColor = 'var(--border)';
            e.currentTarget.style.color = 'var(--text-navy)';
          }}
        >
          <span style={{ fontSize: 18 }}>⬇</span>
          Scarica tutti i tuoi dati (.zip)
        </button>
      )}
    </div>
  );
};
