import React from 'react';
import { FOOD_CLASSES } from '../mockData';

/**
 * HumanInTheLoopReview
 * Core AI interaction interface allowing users to inspect model predictions,
 * adjust the confidence threshold filter, confirm classifications, or correct
 * misclassifications (especially unconfident detections and edge cases like "jar").
 */
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

  return (
    <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '20px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontWeight: '600', color: '#1e293b', fontSize: '15px' }}>
            Model Confidence Threshold:
          </label>
          <span style={{ fontWeight: '700', color: '#2563eb', fontSize: '16px' }}>
            {Math.round(confidenceThreshold * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0.10"
          max="0.95"
          step="0.05"
          value={confidenceThreshold}
          onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
          style={{ width: '100%', cursor: 'pointer' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
          <span>10% (Show all possible detections)</span>
          <span>60% (Recommended)</span>
          <span>95% (High certainty only)</span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#0f172a' }}>
          Detected Food Items ({visibleDetections.length})
        </h3>
        <button
          onClick={onAcceptAllAboveThreshold}
          style={{
            backgroundColor: '#10b981',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            padding: '6px 12px',
            fontSize: '13px',
            fontWeight: '600',
            cursor: 'pointer'
          }}
        >
          Accept All Valid Items
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '420px', overflowY: 'auto' }}>
        {visibleDetections.map((det) => {
          const isSelected = selectedId === det.id;
          const isLowConf = det.confidence < 0.60;
          const isJar = det.label.toLowerCase() === 'jar';

          return (
            <div
              key={det.id}
              onClick={() => onSelectDetection(det.id)}
              style={{
                border: isSelected ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                backgroundColor: isSelected ? '#eff6ff' : '#f8fafc',
                borderRadius: '6px',
                padding: '12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontWeight: '600', fontSize: '15px', textTransform: 'capitalize', color: '#1e293b' }}>
                    {det.label}
                  </span>
                  <span
                    style={{
                      marginLeft: '8px',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: '600',
                      backgroundColor: isLowConf ? '#fef3c7' : '#dcfce7',
                      color: isLowConf ? '#92400e' : '#166534'
                    }}
                  >
                    {Math.round(det.confidence * 100)}% Conf
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateDetection(det.id, { status: 'accepted' });
                    }}
                    style={{
                      backgroundColor: det.status === 'accepted' ? '#10b981' : '#e2e8f0',
                      color: det.status === 'accepted' ? '#ffffff' : '#334155',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    {det.status === 'accepted' ? '✓ Accepted' : 'Accept'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateDetection(det.id, { status: 'rejected' });
                    }}
                    style={{
                      backgroundColor: '#fee2e2',
                      color: '#b91c1c',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    Reject
                  </button>
                </div>
              </div>

              {/* Special warning for Carter's note on "jar" / low confidence */}
              {(isJar || isLowConf) && (
                <div style={{ fontSize: '12px', color: '#b45309', backgroundColor: '#fffbeb', padding: '6px 8px', borderRadius: '4px', marginBottom: '8px' }}>
                  {isJar
                    ? '⚠️ "Jar" is an unidentified container. Please select the specific food item below.'
                    : '⚠️ Low model certainty (< 60%). Please verify or correct the label.'}
                </div>
              )}

              {/* Active Learning: User correction dropdown */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }} onClick={(e) => e.stopPropagation()}>
                <span style={{ color: '#64748b' }}>Correct label:</span>
                <select
                  value={det.label}
                  onChange={(e) => {
                    onUpdateDetection(det.id, {
                      label: e.target.value,
                      status: 'modified',
                      userCorrected: true
                    });
                  }}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    backgroundColor: '#ffffff'
                  }}
                >
                  {FOOD_CLASSES.map((cls) => (
                    <option key={cls} value={cls}>
                      {cls}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
