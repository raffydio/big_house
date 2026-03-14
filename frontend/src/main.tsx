// ─────────────────────────────────────────
// src/main.tsx — AGGIUNGERE GoogleOAuthProvider
//
// Modifica MINIMA al tuo main.tsx esistente:
// Avvolgi <App /> con GoogleOAuthProvider
// ─────────────────────────────────────────

import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App'
import "./styles/globals.css";

// Il CLIENT_ID è pubblico — può stare nel codice frontend
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>
)

// ─────────────────────────────────────────
// AGGIUNGERE AL FILE .env (frontend):
// VITE_GOOGLE_CLIENT_ID=123456789-xxxx.apps.googleusercontent.com
//
// E al .env del backend:
// GOOGLE_CLIENT_ID=123456789-xxxx.apps.googleusercontent.com
// ─────────────────────────────────────────
