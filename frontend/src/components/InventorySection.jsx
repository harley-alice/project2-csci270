import React from 'react';
import { formatLabel, formatDateDisplay } from '../utils/dateUtils';

/**
 * InventorySection component.
 * Displays all currently tracked food items in the fridge.
 * Features:
 * - Sorting by expiration date (Soonest to Expire first, or Latest, or Alphabetical)
 * - Visual status badges (Fresh, Use Soon, Expired)
 * - Direct shelf life day updates
 * - Removal of tracked items
 * - Disclaimer summarizing USDA FoodKeeper safety guidance
 */
export default function InventorySection({
  tracking,
  trackingSortBy,
  setTrackingSortBy,
  updateTrackingDays,
  removeTracked,
  onScanMore
}) {
  // Sort the inventory items according to the selected user preference
  const sortedItems = [...tracking].sort((a, b) => {
    if (trackingSortBy === 'expire_soonest') {
      const daysA = parseInt(a.days, 10) ?? 999;
      const daysB = parseInt(b.days, 10) ?? 999;
      return daysA - daysB;
    }
    if (trackingSortBy === 'expire_latest') {
      const daysA = parseInt(a.days, 10) ?? 0;
      const daysB = parseInt(b.days, 10) ?? 0;
      return daysB - daysA;
    }
    if (trackingSortBy === 'alphabetical') {
      return (a.label || '').localeCompare(b.label || '');
    }
    return 0;
  });

  return (
    <section aria-labelledby="inventory-heading">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div>
          <h2 id="inventory-heading" style={{ fontSize: '18px', fontWeight: 700 }}>
            Current Fridge Inventory ({tracking.length} items)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
            Track shelf life countdowns and prioritized expiration order.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Order by Date Expire By dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label htmlFor="inventory-sort" style={{ fontSize: '13px', fontWeight: 600 }}>
              Order by:
            </label>
            <select
              id="inventory-sort"
              value={trackingSortBy}
              onChange={(e) => setTrackingSortBy(e.target.value)}
              style={{
                border: '1px solid var(--color-border)',
                padding: '6px 10px',
                fontSize: '13px',
                background: '#ffffff',
                minHeight: '38px',
                fontWeight: 500
              }}
            >
              <option value="expire_soonest">Soonest Expiring First</option>
              <option value="expire_latest">Furthest Expiration First</option>
              <option value="alphabetical">Food Name (A-Z)</option>
            </select>
          </div>

          <button
            type="button"
            onClick={onScanMore}
            style={{
              background: 'var(--color-primary-accent)',
              color: '#ffffff',
              border: 'none',
              padding: '10px 18px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            + Scan More Food
          </button>
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <caption
          className="sr-only"
          style={{
            position: 'absolute',
            width: '1px',
            height: '1px',
            padding: 0,
            margin: '-1px',
            overflow: 'hidden',
            clip: 'rect(0, 0, 0, 0)',
            border: 0
          }}
        >
          Current list of tracked fridge items with remaining shelf life and predicted expiration
          dates
        </caption>
        <thead>
          <tr
            style={{
              borderBottom: '2px solid var(--color-border)',
              textAlign: 'left',
              fontSize: '13px',
              color: 'var(--color-text)'
            }}
          >
            <th scope="col" style={{ padding: '10px 0', width: '26%' }}>
              Food Item
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '18%' }}>
              State & Opened
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '22%' }}>
              Predicted Expiration
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '16%' }}>
              Days Remaining
            </th>
            <th scope="col" style={{ padding: '10px 0', width: '10%' }}>
              Status
            </th>
            <th scope="col" style={{ padding: '10px 0', textAlign: 'right', width: '8%' }}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedItems.map((t) => {
            const daysNum = parseInt(t.days, 10);
            const isExpired = daysNum <= 0;
            const isUrgent = daysNum > 0 && daysNum <= 3;

            // Color badge styles with high contrast
            const badgeStyle = isExpired
              ? { bg: '#fff1f0', color: '#9e2b00', border: '1px solid #ffccc7', text: 'Expired' }
              : isUrgent
              ? { bg: '#fffbe6', color: '#874d00', border: '1px solid #ffe58f', text: 'Use Soon' }
              : { bg: '#f6ffed', color: '#135200', border: '1px solid #b7eb8f', text: 'Fresh' };

            const isOpened = (t.packageState || '').toLowerCase() === 'opened';

            return (
              <tr key={t.id} style={{ borderBottom: '1px solid #e5e5e5' }}>
                <td style={{ padding: '12px 0', textTransform: 'capitalize', fontWeight: 600 }}>
                  <div>{formatLabel(t.label)}</div>
                  {t.isUnsureOpened && (
                    <div style={{ fontSize: '11px', color: 'var(--color-attention)', fontWeight: 400 }}>
                      (Conservative rule applied)
                    </div>
                  )}
                </td>

                <td
                  style={{
                    padding: '12px 0',
                    textTransform: 'capitalize',
                    color: 'var(--color-text-muted)'
                  }}
                >
                  <div>{t.packageState || 'Sealed'}</div>
                  {isOpened && t.openedDate && (
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      Opened: {formatDateDisplay(t.openedDate)}
                    </div>
                  )}
                </td>

                <td style={{ padding: '12px 0' }}>
                  <strong style={{ color: isExpired ? 'var(--color-error)' : 'inherit' }}>
                    {formatDateDisplay(t.expirationDate)}
                  </strong>
                </td>

                <td style={{ padding: '12px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <input
                      type="number"
                      min="0"
                      max="365"
                      aria-label={`Days remaining for ${t.label}`}
                      value={t.days}
                      onChange={(e) => updateTrackingDays(t.id, e.target.value)}
                      style={{
                        width: '56px',
                        padding: '6px 6px',
                        fontSize: '13px',
                        border: '1px solid var(--color-border)',
                        color: 'inherit',
                        fontWeight: isUrgent || isExpired ? 700 : 400,
                        minHeight: '40px'
                      }}
                    />
                    <span style={{ color: 'var(--color-text-muted)' }}>
                      {daysNum === 1 ? 'day' : 'days'}
                    </span>
                  </div>
                </td>

                <td style={{ padding: '12px 0' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: 700,
                      backgroundColor: badgeStyle.bg,
                      color: badgeStyle.color,
                      border: badgeStyle.border,
                      letterSpacing: '0.2px'
                    }}
                  >
                    {badgeStyle.text}
                  </span>
                </td>

                <td style={{ padding: '12px 0', textAlign: 'right' }}>
                  <button
                    type="button"
                    onClick={() => removeTracked(t.id)}
                    aria-label={`Remove tracked ${t.label}`}
                    style={{
                      background: 'none',
                      border: 'none',
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: 'var(--color-error)',
                      fontWeight: 600,
                      minHeight: '40px',
                      padding: '6px'
                    }}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            );
          })}

          {tracking.length === 0 && (
            <tr>
              <td
                colSpan="6"
                style={{
                  textAlign: 'center',
                  padding: '36px 0',
                  color: 'var(--color-text-muted)',
                  fontSize: '14px'
                }}
              >
                Your fridge inventory is currently empty. Click "+ Scan More Food" to scan or add
                items.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Required USDA FoodKeeper Safety & Advisory Disclaimer */}
      <div
        role="note"
        aria-label="Food Safety and USDA FoodKeeper Advisory"
        style={{
          border: '1px solid var(--color-border)',
          background: '#fafafa',
          padding: '16px 18px',
          fontSize: '13px',
          color: 'var(--color-text)',
          lineHeight: '1.5',
          marginTop: '28px'
        }}
      >
        <div style={{ fontWeight: 700, color: 'var(--color-attention)', marginBottom: '4px' }}>
          Notice: Food Safety & USDA FoodKeeper Advisory
        </div>
        <p>
          Expiration windows and shelf-life recommendations are calculated using guidelines from the{' '}
          <strong>USDA FSIS FoodKeeper</strong> dataset curated for this project. These predictions
          cannot replace sensory inspection (sight, smell, texture). Always inspect perishable items
          before consumption; when in doubt, discard.
        </p>
      </div>
    </section>
  );
}
