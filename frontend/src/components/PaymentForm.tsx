// src/components/PaymentForm.tsx
// Form carta di credito, Stripe-ready per produzione
// In locale simula il pagamento; in prod integra Stripe Elements

import React, { useState } from 'react';
import type { Plan, BillingCycle, PaymentPayload } from '../types';
import { PLAN_CONFIGS } from '../types';
import { Button } from './ui/Button';
import { Input } from './ui/Input';

interface PaymentFormProps {
  plan: Plan;
  cycle: BillingCycle;
  onSuccess: () => void;
  onCancel: () => void;
}

// Formatta numero carta con spazi ogni 4 cifre
function formatCardNumber(val: string): string {
  return val.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim();
}

// Formatta scadenza MM/AA
function formatExpiry(val: string): string {
  const clean = val.replace(/\D/g, '').slice(0, 4);
  if (clean.length >= 2) return clean.slice(0, 2) + '/' + clean.slice(2);
  return clean;
}

// Rileva brand carta
function detectBrand(num: string): string {
  const n = num.replace(/\s/g, '');
  if (/^4/.test(n)) return 'VISA';
  if (/^5[1-5]|^2[2-7]/.test(n)) return 'MC';
  if (/^3[47]/.test(n)) return 'AMEX';
  return '';
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  plan, cycle, onSuccess, onCancel,
}) => {
  const [form, setForm] = useState({
    cardholder_name: '',
    card_number: '',
    card_expiry: '',
    card_cvc: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');

  const planConfig = PLAN_CONFIGS.find((p) => p.id === plan)!;
  const price = planConfig.prices[cycle];
  const priceLabel = cycle === 'annual'
    ? `€${price}/mese · fatturato €${price * 12}/anno`
    : `€${price}/mese`;

  const brand = detectBrand(form.card_number);

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!form.cardholder_name.trim()) e.cardholder_name = 'Campo obbligatorio';
    const rawNum = form.card_number.replace(/\s/g, '');
    if (rawNum.length < 13) e.card_number = 'Numero carta non valido';
    const exp = form.card_expiry.replace('/', '');
    if (exp.length < 4) e.card_expiry = 'Scadenza non valida';
    if (form.card_cvc.length < 3) e.card_cvc = 'CVC non valido';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;

    setLoading(true);
    try {
      // In locale: simulazione 1.5s
      // In produzione: chiamata a /billing/subscribe con Stripe token
      await new Promise((r) => setTimeout(r, 1500));

      // Simulated upgrade call
      const token = localStorage.getItem('bh_token');
      const res = await fetch(`${import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'}/users/billing/upgrade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          plan,
          billing_cycle: cycle,
          // In produzione: stripe_payment_method_id invece dei dati carta grezzi
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setApiError(data?.detail ?? 'Errore durante il pagamento. Riprova.');
        return;
      }

      onSuccess();
    } catch {
      setApiError('Errore di rete. Controlla la connessione.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      background: 'var(--bg-white)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--r-xl)',
      padding: 32,
      maxWidth: 460,
      width: '100%',
      margin: '0 auto',
      boxShadow: 'var(--shadow-xl)',
      animation: 'fadeIn .3s ease both',
    }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.3rem',
          color: 'var(--text-navy)',
          marginBottom: 6,
        }}>
          Completa il pagamento
        </h3>
        {/* Piano selezionato */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          background: 'var(--bg-muted)',
          borderRadius: 'var(--r-md)',
          marginTop: 12,
        }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Piano </span>
            <span style={{ fontWeight: 700, color: 'var(--text-navy)', textTransform: 'uppercase' }}>
              {plan}
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              {' '}· {cycle === 'annual' ? 'annuale' : 'mensile'}
            </span>
          </div>
          <span style={{ fontWeight: 800, color: 'var(--c-blue)', fontFamily: 'var(--font-display)' }}>
            €{price}<span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-muted)' }}>/mese</span>
          </span>
        </div>
        {cycle === 'annual' && (
          <p style={{ fontSize: '0.75rem', color: 'var(--c-green)', marginTop: 6, textAlign: 'right' }}>
            ✓ Stai risparmiando €{(planConfig.prices.monthly - price) * 12}/anno (25%)
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Nome titolare */}
          <Input
            label="Titolare della carta"
            placeholder="Mario Rossi"
            value={form.cardholder_name}
            onChange={(e) => setForm((f) => ({ ...f, cardholder_name: e.target.value }))}
            error={errors.cardholder_name}
            autoComplete="cc-name"
          />

          {/* Numero carta */}
          <div>
            <div style={{ position: 'relative' }}>
              <Input
                label="Numero carta"
                placeholder="1234 5678 9012 3456"
                value={form.card_number}
                onChange={(e) =>
                  setForm((f) => ({ ...f, card_number: formatCardNumber(e.target.value) }))
                }
                error={errors.card_number}
                autoComplete="cc-number"
                inputMode="numeric"
              />
              {brand && (
                <div style={{
                  position: 'absolute',
                  right: 12,
                  top: errors.card_number ? 'calc(50% - 8px)' : '50%',
                  transform: 'translateY(-50%)',
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  color: 'var(--text-muted)',
                  letterSpacing: '.04em',
                }}>
                  {brand}
                </div>
              )}
            </div>
          </div>

          {/* Scadenza + CVC */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input
              label="Scadenza"
              placeholder="MM/AA"
              value={form.card_expiry}
              onChange={(e) =>
                setForm((f) => ({ ...f, card_expiry: formatExpiry(e.target.value) }))
              }
              error={errors.card_expiry}
              autoComplete="cc-exp"
              inputMode="numeric"
            />
            <Input
              label="CVC"
              placeholder="123"
              value={form.card_cvc}
              onChange={(e) =>
                setForm((f) => ({ ...f, card_cvc: e.target.value.replace(/\D/g, '').slice(0, 4) }))
              }
              error={errors.card_cvc}
              autoComplete="cc-csc"
              inputMode="numeric"
              type="password"
            />
          </div>
        </div>

        {/* API error */}
        {apiError && (
          <div style={{
            marginTop: 14,
            padding: '10px 14px',
            background: 'rgba(239,68,68,.07)',
            border: '1px solid rgba(239,68,68,.2)',
            borderRadius: 'var(--r-md)',
            fontSize: '0.84rem',
            color: 'var(--c-red)',
          }}>
            {apiError}
          </div>
        )}

        {/* Security note */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 16,
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
        }}>
          <span>🔒</span>
          <span>Pagamento sicuro · Dati crittografati · Cancella in qualsiasi momento</span>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <Button variant="secondary" size="md" type="button" onClick={onCancel} style={{ flex: 1 }}>
            Annulla
          </Button>
          <Button variant="primary" size="md" type="submit" loading={loading} style={{ flex: 2 }}>
            {loading ? 'Elaborazione...' : `Paga ${priceLabel}`}
          </Button>
        </div>
      </form>

      {/* DEV notice */}
      {import.meta.env.DEV && (
        <p style={{
          marginTop: 12,
          fontSize: '0.68rem',
          color: 'var(--text-muted)',
          textAlign: 'center',
          fontStyle: 'italic',
        }}>
          [Modalità dev — nessun addebito reale. Usa qualsiasi numero carta.]
        </p>
      )}
    </div>
  );
};
