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
        borderRadius: '24px',
        padding: '24px',
        boxShadow: '0 10px 30px rgba(244, 114, 182, 0.12)',
        border: '2px solid #fce7f3',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        boxSizing: 'border-box'
      }}
    >
      {/* Cutesy Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#831843', letterSpacing: '-0.3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Spotted in your Fridge</span> 🎀
          </h2>
          <p style={{ fontSize: '13px', color: '#9d4c6d', marginTop: '3px' }}>
            Tap the ones you want to keep track of!
          </p>
        </div>

        {pendingCount > 0 && (
          <button
            onClick={onAcceptAllAboveThreshold}
            style={{
              backgroundColor: '#ec4899',
              color: '#ffffff',
              border: 'none',
              borderRadius: '20px',
              padding: '10px 18px',
              fontSize: '13px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(236, 72, 153, 0.35)',
              transition: 'all 0.15s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#db2777')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#ec4899')}
          >
            <span>💖</span> Add All to Fridge!
          </button>
        )}
      </div>

      {/* Cutesy Slider: Eye Focus / Scanner */}
      <div
        style={{
          backgroundColor: '#fff1f2',
          borderRadius: '18px',
          padding: '14px 18px',
          marginBottom: '18px',
          border: '1.5px dashed #fecdd3'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#9f1239', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>👀 Scanner Eye</span>
          </span>
          <span
            style={{
              fontSize: '12px',
              fontWeight: '700',
              color: '#be185d',
              backgroundColor: '#ffe4e6',
              padding: '3px 10px',
              borderRadius: '12px'
            }}
          >
            {confidenceThreshold <= 0.40
              ? '✨ Catching everything'
              : confidenceThreshold >= 0.70
              ? '🌸 Only super obvious snacks'
              : '💕 Just right'}
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
            accentColor: '#ec4899',
            cursor: 'pointer'
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#f43f5e', marginTop: '4px', fontWeight: '500' }}>
          <span>Find more goodies</span>
          <span>Only high certainty</span>
        </div>
      </div>

      {/* Detection Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
        {visibleDetections.map((det) => {
          const isSelected = selectedId === det.id;
          const meta = FOOD_METADATA[det.label] || { name: det.label, emoji: '🍓', defaultDays: 5 };
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
                borderRadius: '18px',
                border: isSelected
                  ? '2px solid #ec4899'
                  : isAccepted
                  ? '2px solid #86efac'
                  : '1.5px solid #fce7f3',
                backgroundColor: isSelected
                  ? '#fdf2f8'
                  : isAccepted
                  ? '#f0fdf4'
                  : '#ffffff',
                padding: '16px',
                boxShadow: isSelected
                  ? '0 6px 16px rgba(236, 72, 153, 0.15)'
                  : '0 2px 8px rgba(0,0,0,0.02)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '46px',
                      height: '46px',
                      borderRadius: '14px',
                      backgroundColor: '#fff1f2',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '24px',
                      boxShadow: 'inset 0 2px 4px rgba(244, 114, 182, 0.1)'
                    }}
                  >
                    {meta.emoji}
                  </div>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#4a2835' }}>
                      {meta.name}
                    </h4>
                    <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#9d4c6d' }}>
                      Stays fresh ~{meta.defaultDays} days ✨
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }} onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => onUpdateDetection(det.id, { status: isAccepted ? 'pending' : 'accepted' })}
                    style={{
                      backgroundColor: isAccepted ? '#10b981' : '#fdf2f8',
                      color: isAccepted ? '#ffffff' : '#be185d',
                      border: isAccepted ? 'none' : '1px solid #fbcfe8',
                      borderRadius: '12px',
                      padding: '8px 14px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {isAccepted ? '✓ In Fridge!' : '💖 Keep'}
                  </button>

                  <button
                    onClick={() => onUpdateDetection(det.id, { status: 'rejected' })}
                    style={{
                      backgroundColor: '#fff1f2',
                      color: '#f43f5e',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '8px 10px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                    title="Not in my fridge"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Cute clarification notice */}
              {(isJar || isLowCertainty) && (
                <div
                  style={{
                    backgroundColor: '#fff7ed',
                    border: '1.5px dashed #fed7aa',
                    borderRadius: '14px',
                    padding: '12px',
                    marginTop: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#c2410c', fontWeight: '700' }}>
                    <span>✨</span>
                    <span>
                      {isJar
                        ? "Ooh, a mystery jar! What goodies are inside?"
                        : "Hmm, not totally sure! Did we guess this right?"}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', color: '#9a3412', fontWeight: '600' }}>Actually it's:</span>
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
                        padding: '6px 12px',
                        borderRadius: '10px',
                        border: '1.5px solid #fb923c',
                        fontSize: '13px',
                        fontWeight: '700',
                        color: '#4a2835',
                        backgroundColor: '#ffffff',
                        cursor: 'pointer'
                      }}
                    >
                      {FOOD_CLASSES.map((cls) => {
                        const m = FOOD_METADATA[cls] || { name: cls, emoji: '🍓' };
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
