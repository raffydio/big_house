// src/components/ChatBubble.tsx
// Bolla chat stile ChatGPT/Claude per mostrare query e risposte
// Usata sia in DeepResearch che CalcROI

import React from 'react';
import type { ChatMessage } from '../types';

interface ChatBubbleProps {
  message: ChatMessage;
  userName?: string;
  onDownloadDocx?: (filename: string) => void;
}

const MAX_PREVIEW_CHARS = 800; // caratteri visibili prima di "mostra altro"

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message, userName = 'Tu', onDownloadDocx,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const isUser = message.role === 'user';

  const content = message.content;
  const isTruncated = content.length > MAX_PREVIEW_CHARS && !expanded;
  const displayContent = isTruncated
    ? content.slice(0, MAX_PREVIEW_CHARS) + '…'
    : content;

  const time = new Date(message.timestamp).toLocaleTimeString('it-IT', {
    hour: '2-digit', minute: '2-digit',
  });

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 10,
      alignItems: 'flex-start',
      animation: 'slideInUp .3s ease both',
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32,
        borderRadius: '50%',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.8rem',
        fontWeight: 700,
        background: isUser
          ? 'linear-gradient(135deg, var(--c-navy), var(--c-blue))'
          : 'linear-gradient(135deg, var(--c-gold), var(--c-gold-light))',
        color: isUser ? '#fff' : 'var(--c-navy-dark)',
      }}>
        {isUser ? userName.charAt(0).toUpperCase() : '⬡'}
      </div>

      {/* Bubble */}
      <div className="chat-bubble" style={{
        maxWidth: '75%',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        alignItems: isUser ? 'flex-end' : 'flex-start',
      }}>
        {/* Name + time */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          flexDirection: isUser ? 'row-reverse' : 'row',
        }}>
          <span style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
          }}>
            {isUser ? userName : 'Big House AI'}
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{time}</span>
        </div>

        {/* Content box */}
        <div style={{
          padding: '12px 16px',
          borderRadius: isUser
            ? 'var(--r-lg) var(--r-md) var(--r-md) var(--r-lg)'
            : 'var(--r-md) var(--r-lg) var(--r-lg) var(--r-md)',
          background: isUser
            ? 'linear-gradient(135deg, var(--c-navy), var(--c-blue))'
            : 'var(--bg-white)',
          border: isUser ? 'none' : '1px solid var(--border)',
          boxShadow: 'var(--shadow-sm)',
          color: isUser ? '#fff' : 'var(--text-primary)',
          fontSize: '0.88rem',
          lineHeight: 1.65,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {displayContent}

          {/* Show more */}
          {content.length > MAX_PREVIEW_CHARS && (
            <button
              onClick={() => setExpanded((e) => !e)}
              style={{
                display: 'block',
                marginTop: 8,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: isUser ? 'rgba(255,255,255,.7)' : 'var(--c-blue)',
                fontFamily: 'var(--font-body)',
                padding: 0,
              }}
            >
              {expanded ? '▲ Mostra meno' : `▼ Mostra tutto (${content.length} caratteri)`}
            </button>
          )}
        </div>

        {/* DOCX Download button */}
        {message.docx_filename && onDownloadDocx && (
          <button
            onClick={() => onDownloadDocx(message.docx_filename!)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              background: 'rgba(37,99,235,.08)',
              border: '1px solid rgba(37,99,235,.2)',
              borderRadius: 'var(--r-full)',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: 'var(--c-blue)',
              fontFamily: 'var(--font-body)',
              transition: 'all var(--dur-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(37,99,235,.14)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(37,99,235,.08)';
            }}
          >
            <span>📄</span>
            <span>Scarica Report .docx</span>
          </button>
        )}
      </div>
    </div>
  );
};
