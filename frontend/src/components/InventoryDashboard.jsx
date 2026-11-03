import React from 'react';
import { FOOD_METADATA } from '../mockData';

export default function InventoryDashboard({ items, onRemoveItem }) {
  if (items.length === 0) {
    return (
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '24px',
          padding: '48px 24px',
          textAlign: 'center',
          boxShadow: '0 10px 30px rgba(244, 114, 182, 0.1)',
          border: '2px dashed #fbcfe8'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '10px' }}>🍰</div>
        <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#831843' }}>
          Your fridge is totally empty!
        </h3>
        <p style={{ fontSize: '14px', color: '#9d4c6d', maxWidth: '400px', margin: '6px auto 0' }}>
          Snap a picture of your shelves above and let's stock up your cute fridge! 💕
        </p>
      </div>
    );
  }

  const urgentItems = items.filter((item) => (item.daysRemaining ?? 5) <= 2);

  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '24px',
        padding: '28px',
        boxShadow: '0 10px 30px rgba(244, 114, 182, 0.1)',
        border: '2px solid #fce7f3'
      }}
    >
      {/* Fridge Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '22px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: '700', color: '#831843', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>My Cute Fridge</span> 🍧
          </h2>
          <p style={{ fontSize: '13px', color: '#9d4c6d', marginTop: '2px' }}>
            {items.length} items keeping fresh & yummy!
          </p>
        </div>

        {urgentItems.length > 0 && (
          <div
            style={{
              backgroundColor: '#fff1f2',
              color: '#e11d48',
              padding: '8px 16px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              border: '1.5px solid #fecdd3',
              boxShadow: '0 2px 8px rgba(225, 29, 72, 0.1)'
            }}
          >
            <span>🍓</span> {urgentItems.length} {urgentItems.length === 1 ? 'snack needs' : 'snacks need'} eating ASAP!
          </div>
        )}
      </div>

      {/* Grid of Fridge Items */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
        {items.map((item) => {
          const meta = FOOD_METADATA[item.label] || { name: item.label, emoji: '🍓' };
          const daysLeft = item.daysRemaining ?? meta.defaultDays ?? 5;

          const isExpired = daysLeft <= 0;
          const isUrgent = daysLeft <= 2 && !isExpired;

          // Cute status styling
          const pillBg = isExpired ? '#ffe4e6' : isUrgent ? '#fef3c7' : '#ecfdf5';
          const pillColor = isExpired ? '#be123c' : isUrgent ? '#b45309' : '#047857';
          const pillBorder = isExpired ? '#fecdd3' : isUrgent ? '#fde68a' : '#a7f3d0';
          const statusMessage = isExpired
            ? '⚠️ Spoiled or toss time!'
            : isUrgent
            ? `⏳ Eat in ${daysLeft} ${daysLeft === 1 ? 'day' : 'days'}!`
            : `🌸 Fresh for ${daysLeft} days`;

          return (
            <div
              key={item.id}
              style={{
                borderRadius: '20px',
                border: '1.5px solid #fce7f3',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                backgroundColor: '#fffbfa',
                boxShadow: '0 4px 12px rgba(244, 114, 182, 0.06)',
                transition: 'all 0.15s ease'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                      style={{
                        width: '44px',
                        height: '44px',
                        borderRadius: '14px',
                        backgroundColor: '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '24px',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                        border: '1px solid #fce7f3'
                      }}
                    >
                      {meta.emoji}
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#4a2835' }}>
                        {meta.name}
                      </h4>
                      <span style={{ fontSize: '12px', color: '#9d4c6d' }}>
                        Tucked in {item.dateAdded || 'Today'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveItem(item.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#f472b6',
                      fontSize: '18px',
                      cursor: 'pointer',
                      padding: '2px 6px',
                      borderRadius: '6px'
                    }}
                    title="Ate it / Remove"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div
                style={{
                  backgroundColor: pillBg,
                  color: pillColor,
                  border: `1.5px solid ${pillBorder}`,
                  borderRadius: '12px',
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
                <span>{statusMessage}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
