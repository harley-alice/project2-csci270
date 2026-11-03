import React from 'react';

/**
 * InventoryDashboard
 * Renders confirmed fridge items with status badges (Fresh, Approaching Expiration, Expired)
 * based on USDA FoodKeeper guidelines.
 */
export default function InventoryDashboard({ items, onRemoveItem }) {
  if (items.length === 0) {
    return (
      <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '32px', textAlign: 'center', border: '1px solid #e2e8f0', color: '#64748b' }}>
        <p style={{ margin: 0, fontSize: '15px' }}>Your fridge inventory is empty.</p>
        <p style={{ margin: '8px 0 0', fontSize: '13px' }}>Upload a fridge photo above and confirm detected items to stock your digital fridge.</p>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '20px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '17px', fontWeight: '600', color: '#0f172a' }}>
        Current Refrigerator Inventory ({items.length} items)
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
        {items.map((item) => {
          const daysLeft = item.daysRemaining ?? item.suggestedShelfLifeDays ?? 5;
          let badgeColor = '#10b981'; // Fresh
          let badgeText = `${daysLeft} days left (Fresh)`;
          let bgBadge = '#dcfce7';

          if (daysLeft <= 2 && daysLeft > 0) {
            badgeColor = '#d97706'; // Soon
            badgeText = `${daysLeft} days left (Use Soon)`;
            bgBadge = '#fef3c7';
          } else if (daysLeft <= 0) {
            badgeColor = '#dc2626'; // Expired
            badgeText = 'Expired / Spoilage Risk';
            bgBadge = '#fee2e2';
          }

          return (
            <div
              key={item.id}
              style={{
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                padding: '12px',
                backgroundColor: '#ffffff',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontWeight: '600', fontSize: '15px', textTransform: 'capitalize', color: '#1e293b' }}>
                    {item.label}
                  </span>
                  <button
                    onClick={() => onRemoveItem(item.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#94a3b8',
                      cursor: 'pointer',
                      fontSize: '16px',
                      padding: '0 4px'
                    }}
                    title="Remove item"
                  >
                    ×
                  </button>
                </div>

                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>
                  Added: {item.dateAdded || 'Today'}
                  {item.userCorrected && (
                    <span style={{ display: 'block', color: '#2563eb', fontSize: '11px', marginTop: '2px' }}>
                      (User verified label)
                    </span>
                  )}
                </div>
              </div>

              <div
                style={{
                  backgroundColor: bgBadge,
                  color: badgeColor,
                  fontWeight: '600',
                  fontSize: '12px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  textAlign: 'center'
                }}
              >
                {badgeText}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
