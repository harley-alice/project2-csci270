import React from 'react';
import { FOOD_METADATA } from '../mockData';

export default function InventoryDashboard({ items, onRemoveItem }) {
  if (items.length === 0) {
    return (
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '16px',
          padding: '48px 24px',
          textAlign: 'center',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
          border: '1px solid #f1f5f9'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🧊</div>
        <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#1e293b' }}>
          Your digital fridge is empty
        </h3>
        <p style={{ fontSize: '14px', color: '#64748b', maxWidth: '420px', margin: '6px auto 0' }}>
          Take a photo of your fridge or scan individual groceries above. We'll automatically keep track of when things expire!
        </p>
      </div>
    );
  }

  // Group by freshness urgency
  const urgentItems = items.filter((item) => (item.daysRemaining ?? 5) <= 2);
  const goodItems = items.filter((item) => (item.daysRemaining ?? 5) > 2);

  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
        border: '1px solid #f1f5f9'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.3px' }}>
            What's In Your Fridge
          </h2>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
            {items.length} items tracked using USDA FoodKeeper freshness guidelines
          </p>
        </div>

        {urgentItems.length > 0 && (
          <div
            style={{
              backgroundColor: '#fef2f2',
              color: '#dc2626',
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              border: '1px solid #fecaca'
            }}
          >
            <span>⚠️</span> {urgentItems.length} {urgentItems.length === 1 ? 'item needs' : 'items need'} eating soon
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
        {items.map((item) => {
          const meta = FOOD_METADATA[item.label] || { name: item.label, emoji: '🥗' };
          const daysLeft = item.daysRemaining ?? meta.defaultDays ?? 5;

          const isExpired = daysLeft <= 0;
          const isUrgent = daysLeft <= 2 && !isExpired;

          // Don Norman Signifiers: unmistakable color + wording
          const statusBg = isExpired ? '#fef2f2' : isUrgent ? '#fffbeb' : '#f0fdf4';
          const statusText = isExpired ? '#b91c1c' : isUrgent ? '#b45309' : '#15803d';
          const statusBorder = isExpired ? '#fecaca' : isUrgent ? '#fde68a' : '#bbf7d0';
          const labelText = isExpired
            ? 'Past safe date'
            : isUrgent
            ? `Eat within ${daysLeft} ${daysLeft === 1 ? 'day' : 'days'}`
            : `Fresh for ${daysLeft} days`;

          return (
            <div
              key={item.id}
              style={{
                borderRadius: '14px',
                border: '1px solid #e2e8f0',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                backgroundColor: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                transition: 'transform 0.1s ease, box-shadow 0.1s ease'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '28px', lineHeight: 1 }}>{meta.emoji}</span>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#1e293b' }}>
                        {meta.name}
                      </h4>
                      <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                        Added {item.dateAdded || 'Today'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveItem(item.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#cbd5e1',
                      fontSize: '18px',
                      cursor: 'pointer',
                      padding: '2px 6px',
                      borderRadius: '4px'
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.color = '#ef4444')}
                    onMouseOut={(e) => (e.currentTarget.style.color = '#cbd5e1')}
                    title="Remove from fridge"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div
                style={{
                  backgroundColor: statusBg,
                  color: statusText,
                  border: `1px solid ${statusBorder}`,
                  borderRadius: '8px',
                  padding: '7px 12px',
                  fontSize: '12px',
                  fontWeight: '700',
                  marginTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <span>{isExpired ? '🚫' : isUrgent ? '⏳' : '✅'}</span>
                <span>{labelText}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
