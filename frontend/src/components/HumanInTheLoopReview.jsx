import React from 'react';
import { FOOD_CLASSES, FOOD_METADATA } from '../mockData';

export default function HumanInTheLoopReview({
  detections,
  confidenceThreshold,
  onConfidenceChange,
  selectedId,
  onSelectDetection,
  onUpdateDetection,
  onAcceptAllAboveThreshold
}) {
  const visibleDetections = detections.filter((d) => d.confidence >= confidenceThreshold);
  const pendingCount = visibleDetections.filter((d) => d.status !== 'rejected').length;

  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        border: '1px solid #f1f5f9',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        boxSizing: 'border-box'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.3px' }}>
            Items Found in Fridge
          </h2>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
            Check what we spotted and confirm below
          </p>
        </div>

        {pendingCount > 0 && (
          <button
            onClick={onAcceptAllAboveThreshold}
            style={{
              backgroundColor: '#10b981',
              color: '#ffffff',
              border: 'none',
              borderRadius: '10px',
              padding: '9px 16px',
              fontSize: '13px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 4px rgba(16, 185, 129, 0.25)',
              transition: 'all 0.15s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#059669')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#10b981')}
          >
            <span>✓</span> Add All to Fridge
          </button>
        )}
      </div>

      {/* Sensitivity / Filter Controls (Don Norman: Conceptual model made plain) */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          borderRadius: '12px',
          padding: '14px 16px',
          marginBottom: '20px',
          border: '1px solid #e2e8f0'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#334155' }}>
            Scanner Sensitivity
          </span>
          <span
            style={{
              fontSize: '12px',
              fontWeight: '700',
              color: '#2563eb',
              backgroundColor: '#eff6ff',
              padding: '2px 8px',
              borderRadius: '6px'
            }}
          >
            {confidenceThreshold <= 0.40
              ? 'Showing faint & uncertain items'
              : confidenceThreshold >= 0.70
              ? 'Showing clear & obvious items only'
              : 'Balanced detection'}
          </span>
        </div>

        <input
          type="range"
          min="0.20"
          max="0.85"
          step="0.05"
          value={confidenceThreshold}
          onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
          style={{
            width: '100%',
            accentColor: '#2563eb',
            cursor: 'pointer'
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
          <span>Find more items</span>
          <span>Fewer false guesses</span>
        </div>
      </div>

      {/* List of Detections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
        {visibleDetections.map((det) => {
          const isSelected = selectedId === det.id;
          const meta = FOOD_METADATA[det.label] || { name: det.label, emoji: '🥗', defaultDays: 5 };
          const isLowCertainty = det.confidence < 0.60;
          const isJar = det.label === 'jar';
          const isAccepted = det.status === 'accepted';
          const isRejected = det.status === 'rejected';

          if (isRejected) return null;

          return (
            <div
              key={det.id}
              onClick={() => onSelectDetection(det.id)}
              style={{
                borderRadius: '12px',
                border: isSelected ? '2px solid #3b82f6' : isAccepted ? '1px solid #86efac' : '1px solid #e2e8f0',
                backgroundColor: isSelected ? '#eff6ff' : isAccepted ? '#f0fdf4' : '#ffffff',
                padding: '16px',
                boxShadow: isSelected ? '0 4px 12px rgba(59, 130, 246, 0.12)' : '0 1px 3px rgba(0,0,0,0.03)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {/* Item Card Top */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '28px', lineHeight: 1 }}>{meta.emoji}</span>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#1e293b' }}>
                      {meta.name}
                    </h4>
                    <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#64748b' }}>
                      Keeps fresh ~{meta.defaultDays} days in fridge
                    </p>
                  </div>
                </div>

                {/* Clear Affordance Action Buttons */}
                <div style={{ display: 'flex', gap: '8px' }} onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => onUpdateDetection(det.id, { status: isAccepted ? 'pending' : 'accepted' })}
                    style={{
                      backgroundColor: isAccepted ? '#10b981' : '#f1f5f9',
                      color: isAccepted ? '#ffffff' : '#334155',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '7px 12px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      transition: 'all 0.15s'
                    }}
                  >
                    {isAccepted ? '✓ Added' : '+ Add'}
                  </button>

                  <button
                    onClick={() => onUpdateDetection(det.id, { status: 'rejected' })}
                    style={{
                      backgroundColor: 'transparent',
                      color: '#94a3b8',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      padding: '7px 10px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                    title="Not in my fridge"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Norman Principle: Clear Feedback for Ambiguity / Carter's Jar Case */}
              {(isJar || isLowCertainty) && (
                <div
                  style={{
                    backgroundColor: '#fffbeb',
                    border: '1px solid #fde68a',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    marginTop: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#92400e', fontWeight: '700' }}>
                    <span>💡</span>
                    <span>
                      {isJar
                        ? "This looks like a jar or container. What's inside?"
                        : "We're not 100% sure on this one. Is it correct?"}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                    <span style={{ fontSize: '12px', color: '#78350f' }}>Change to:</span>
                    <select
                      value={det.label}
                      onChange={(e) =>
                        onUpdateDetection(det.id, {
                          label: e.target.value,
                          status: 'modified',
                          userCorrected: true
                        })
                      }
                      style={{
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid #d97706',
                        fontSize: '13px',
                        fontWeight: '600',
                        color: '#1e293b',
                        backgroundColor: '#ffffff',
                        cursor: 'pointer'
                      }}
                    >
                      {FOOD_CLASSES.map((cls) => {
                        const m = FOOD_METADATA[cls] || { name: cls, emoji: '' };
                        return (
                          <option key={cls} value={cls}>
                            {m.emoji} {m.name}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
