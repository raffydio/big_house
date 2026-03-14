// src/hooks/useStorage.ts
// Gestione storage utente: fetch info, download zip, elimina file

import { useState, useCallback } from 'react';
import type { StorageInfo, StoredFile, ChatSession } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const TOKEN_KEY = 'bh_token';

function getHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Chiave locale per sessioni chat (fallback senza backend storage) ──
const SESSIONS_KEY = 'bh_chat_sessions';

export function useStorage() {
  const [storageInfo, setStorageInfo] = useState<StorageInfo | null>(null);
  const [sessions, setSessions]       = useState<ChatSession[]>([]);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);

  // ── Fetch info storage ──
  const fetchStorageInfo = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/storage/info`, { headers: getHeaders() });
      if (!res.ok) throw new Error('fetch failed');
      const data: StorageInfo = await res.json();
      setStorageInfo(data);
    } catch {
      // Fallback locale: calcola da sessioni salvate
      const local = getLocalSessions();
      const totalBytes = local.reduce((acc, s) => {
        return acc + s.messages.reduce((a, m) => a + m.content.length * 2, 0);
      }, 0);
      setStorageInfo({
        used_bytes:    totalBytes,
        max_bytes:     2 * 1024 * 1024 * 1024,
        used_percent:  (totalBytes / (2 * 1024 * 1024 * 1024)) * 100,
        files:         [],
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Fetch sessioni chat ──
  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/storage/sessions`, { headers: getHeaders() });
      if (!res.ok) throw new Error('fetch failed');
      const data: ChatSession[] = await res.json();
      setSessions(data);
    } catch {
      // Fallback: localStorage
      setSessions(getLocalSessions());
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Salva sessione (locale + tenta backend) ──
  const saveSession = useCallback(async (session: ChatSession) => {
    // Salva sempre in locale
    const existing = getLocalSessions();
    const idx = existing.findIndex((s) => s.id === session.id);
    if (idx >= 0) existing[idx] = session;
    else existing.unshift(session);
    // Max 100 sessioni locali
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(existing.slice(0, 100)));
    setSessions((prev) => {
      const i = prev.findIndex((s) => s.id === session.id);
      if (i >= 0) { const n = [...prev]; n[i] = session; return n; }
      return [session, ...prev];
    });

    // Tenta backend
    try {
      await fetch(`${API_BASE}/storage/sessions`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(session),
      });
    } catch {
      // Silent fail — locale è il fallback
    }
  }, []);

  // ── Elimina sessione ──
  const deleteSession = useCallback(async (sessionId: string) => {
    const updated = getLocalSessions().filter((s) => s.id !== sessionId);
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(updated));
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));

    try {
      await fetch(`${API_BASE}/storage/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });
    } catch { /* silent */ }
  }, []);

  // ── Download ZIP di tutti i dati ──
  const downloadZip = useCallback(async () => {
    setLoading(true);
    try {
      // Prova endpoint backend
      const res = await fetch(`${API_BASE}/storage/download-zip`, {
        headers: getHeaders(),
      });

      if (res.ok) {
        const blob = await res.blob();
        triggerDownload(blob, 'big-house-ai-data.zip');
        return;
      }
    } catch { /* fallback client-side */ }

    // Fallback client-side: crea zip con jszip dalle sessioni locali
    try {
      // @ts-ignore — jszip installato come dipendenza
      const JSZip = (await import('jszip')).default;
      const zip   = new JSZip();
      const localSessions = getLocalSessions();

      localSessions.forEach((session) => {
        const content = session.messages
          .map((m) => `[${m.role.toUpperCase()} - ${m.timestamp}]\n${m.content}`)
          .join('\n\n---\n\n');
        const folder = session.feature === 'deepresearch' ? 'deep-research' : 'calcola-roi';
        zip.folder(folder)!.file(`${session.id}.txt`, content);
      });

      const blob = await zip.generateAsync({ type: 'blob' });
      triggerDownload(blob, 'big-house-ai-data.zip');
    } catch {
      setError('Impossibile generare il file zip. Riprova.');
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    storageInfo,
    sessions,
    loading,
    error,
    fetchStorageInfo,
    fetchSessions,
    saveSession,
    deleteSession,
    downloadZip,
  };
}

// ── Helpers ──
function getLocalSessions(): ChatSession[] {
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement('a');
  a.href    = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── Helper per generare DOCX lato client ──
export async function generateDocx(
  title: string,
  sections: { heading: string; content: string }[]
): Promise<void> {
  try {
    // Usa la libreria 'docx' (npm install docx)
    const {
      Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
    } = await import('docx');

    const children: Paragraph[] = [
      new Paragraph({
        text: title,
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
      }),
      new Paragraph({
        children: [new TextRun({
          text: `Generato da Big House AI · ${new Date().toLocaleDateString('it-IT')}`,
          color: '999999',
          size: 18,
        })],
        alignment: AlignmentType.CENTER,
      }),
      new Paragraph({ text: '' }),
    ];

    sections.forEach((sec) => {
      children.push(
        new Paragraph({ text: sec.heading, heading: HeadingLevel.HEADING_1 }),
        new Paragraph({ text: '' }),
        new Paragraph({
          children: [new TextRun({ text: sec.content, size: 22 })],
        }),
        new Paragraph({ text: '' }),
      );
    });

    const doc  = new Document({ sections: [{ children }] });
    const blob = await Packer.toBlob(doc);
    const safe = title.slice(0, 40).replace(/[^a-z0-9]/gi, '_').toLowerCase();
    triggerDownload(blob, `bighouseai_${safe}.docx`);
  } catch (err) {
    console.error('DOCX generation error:', err);
    alert('Impossibile generare il file .docx. Assicurati che la libreria "docx" sia installata (npm install docx).');
  }
}
