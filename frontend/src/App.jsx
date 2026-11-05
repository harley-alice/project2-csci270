import React, { useState } from 'react';
import { FOOD_CLASSES, INITIAL_DETECTIONS } from './mockData';

const SAMPLE_IMAGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

export default function App() {
  // Steps: 1 = Capture, 2 = Confirm items, 3 = Processing, 4 = Tracking
  const [step, setStep] = useState(1);
  const [image, setImage] = useState(SAMPLE_IMAGE);
  const [rawDetections, setRawDetections] = useState(INITIAL_DETECTIONS);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [feedbackQueue, setFeedbackQueue] = useState([]);
  const [feedbackToast, setFeedbackToast] = useState(null);
  const [tracking, setTracking] = useState([
    { id: 't1', label: 'yogurt', days: 5 },
    { id: 't2', label: 'eggs', days: 12 }
  ]);

  const showToast = (message) => {
    setFeedbackToast(message);
    setTimeout(() => {
      setFeedbackToast(null);
    }, 3200);
  };

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setStep(2);
    }
  };

  // Log active learning feedback event
  const logFeedback = (feedbackEvent) => {
    setFeedbackQueue((prev) => [...prev, feedbackEvent]);

    // Send payload to backend /feedback endpoint (graceful fallback if backend offline)
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackEvent)
    })
      .then((res) => {
        if (!res.ok) throw new Error('Feedback endpoint unavailable');
        showToast(`Logged feedback for active learning (${feedbackEvent.type})`);
      })
      .catch(() => {
        // Fallback for offline/mock development
        console.log('[Active Learning Payload Logged]:', feedbackEvent);
        showToast(`Recorded "${feedbackEvent.type}" event for retraining dataset`);
      });
  };

  const updateLabel = (id, newLabel) => {
    const targetItem = rawDetections.find((it) => it.id === id);
    if (!targetItem || targetItem.label === newLabel) return;

    const originalLabel = targetItem.originalLabel || targetItem.label;

    logFeedback({
      timestamp: new Date().toISOString(),
      type: 'user_correction',
      image_source: image.startsWith('data:') ? 'camera_upload' : 'sample_or_url',
      detection_id: id,
      predicted_label: targetItem.label,
      corrected_label: newLabel,
      confidence: targetItem.confidence ?? 1.0,
      bbox_normalized: targetItem.bbox // [ymin, xmin, ymax, xmax]
    });

    setRawDetections((prev) =>
      prev.map((it) =>
        it.id === id
          ? {
              ...it,
              label: newLabel,
              originalLabel,
              userEdited: true
            }
          : it
      )
    );
  };

  const removeFalsePositive = (id) => {
    const targetItem = rawDetections.find((it) => it.id === id);
    if (targetItem) {
      logFeedback({
        timestamp: new Date().toISOString(),
        type: 'false_positive_rejected',
        image_source: image.startsWith('data:') ? 'camera_upload' : 'sample_or_url',
        detection_id: id,
        predicted_label: targetItem.label,
        corrected_label: null,
        confidence: targetItem.confidence ?? 1.0,
        bbox_normalized: targetItem.bbox
      });
    }

    setRawDetections((prev) => prev.filter((it) => it.id !== id));
  };

  // Filter items dynamically by the confidence threshold unless manually edited by user
  const visibleItems = rawDetections.filter(
    (it) => it.userEdited || (it.confidence ?? 1.0) >= confidenceThreshold
  );

  const runAiAndTrack = () => {
    setStep(3);
    setTimeout(() => {
      const newTracked = visibleItems.map((it) => ({
        id: String(Date.now() + Math.random()),
        label: it.label,
        days: it.days
      }));
      setTracking([...tracking, ...newTracked]);
      setStep(4);
    }, 1200);
  };

  const removeTracked = (id) => {
    setTracking(tracking.filter((t) => t.id !== id));
  };

  return (
    <div style={{ maxWidth: '760px', margin: '40px auto', padding: '0 20px', fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #000', paddingBottom: '16px', marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 'bold', letterSpacing: '-0.5px' }}>Fridge Tracker</h1>
          <span style={{ fontSize: '12px', color: '#666' }}>CSCI 270 AI Vision & Active Learning Pipeline</span>
        </div>
        <span style={{ fontSize: '13px', border: '1px solid #000', padding: '2px 8px', borderRadius: '12px' }}>
          {feedbackQueue.length} Retraining Samples Logged
        </span>
      </header>

      {/* Floating feedback alert toast */}
      {feedbackToast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          background: 'var(--color-primary-accent, #4A69B3)',
          color: '#fff',
          padding: '12px 18px',
          borderRadius: '4px',
          fontSize: '13px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 1000
        }}>
          ✓ {feedbackToast}
        </div>
      )}

      {/* Step 1: Video / Photo Capture */}
      {step === 1 && (
        <section>
          <div style={{ border: '1px dashed #000', padding: '60px 20px', textAlign: 'center', marginBottom: '24px' }}>
            <p style={{ marginBottom: '16px', fontSize: '14px' }}>Take a picture or record video of your fridge.</p>
            <label style={{ display: 'inline-block', border: '1px solid #000', background: '#000', color: '#fff', padding: '10px 20px', fontSize: '13px', cursor: 'pointer' }}>
              Upload Image or Video
              <input type="file" accept="image/*,video/*" onChange={handleFile} style={{ display: 'none' }} />
            </label>
          </div>

          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => {
                setRawDetections(INITIAL_DETECTIONS);
                setStep(2);
              }}
              style={{ background: 'none', border: '1px solid #000', padding: '8px 16px', fontSize: '12px', cursor: 'pointer' }}
            >
              Use sample image
            </button>
          </div>
        </section>
      )}

      {/* Step 2: Confirm Items & Human-in-the-Loop Threshold Tuning */}
      {step === 2 && (
        <section>
          {/* Confidence Slider Control */}
          <div style={{
            background: '#fafafa',
            border: '1px solid #000',
            padding: '16px 20px',
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="conf-slider" style={{ fontSize: '13px', fontWeight: 'bold' }}>
                AI Confidence Threshold Filter:
              </label>
              <span style={{
                fontSize: '13px',
                fontFamily: 'monospace',
                background: (confidenceThreshold >= 0.60) ? '#eee' : 'var(--color-accent, #FFEC89)',
                padding: '2px 6px',
                border: '1px solid #ccc'
              }}>
                {Math.round(confidenceThreshold * 100)}%
              </span>
            </div>
            <input
              id="conf-slider"
              type="range"
              min="0.20"
              max="0.95"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#666' }}>
              <span>Low (show subtle detections)</span>
              <span>Showing {visibleItems.length} of {rawDetections.length} candidate boxes</span>
              <span>High (strict certainty)</span>
            </div>
          </div>

          {/* Bounding Box Image Preview */}
          <div style={{ position: 'relative', border: '1px solid #000', marginBottom: '24px', background: '#000' }}>
            <img src={image} alt="Fridge" style={{ display: 'block', width: '100%', maxHeight: '420px', objectFit: 'contain' }} />
            <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox="0 0 1000 1000" preserveAspectRatio="none">
              {visibleItems.map((it) => {
                const [ymin, xmin, ymax, xmax] = it.bbox;
                const isLowConf = (it.confidence ?? 1.0) < 0.60;
                const strokeColor = it.userEdited ? '#FFEC89' : (isLowConf ? '#BA3801' : '#4A69B3');
                return (
                  <g key={it.id}>
                    <rect
                      x={xmin * 1000}
                      y={ymin * 1000}
                      width={(xmax - xmin) * 1000}
                      height={(ymax - ymin) * 1000}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth="3"
                      strokeDasharray={isLowConf && !it.userEdited ? "4 3" : "none"}
                    />
                    <rect
                      x={xmin * 1000}
                      y={Math.max(0, ymin * 1000 - 20)}
                      width={Math.max(80, (it.label.length * 9) + 45)}
                      height="20"
                      fill={strokeColor}
                    />
                    <text
                      x={xmin * 1000 + 4}
                      y={Math.max(14, ymin * 1000 - 5)}
                      fill={it.userEdited ? '#000' : '#fff'}
                      fontSize="12"
                      fontWeight="bold"
                      fontFamily="Helvetica"
                    >
                      {it.label} {it.confidence ? `(${Math.round(it.confidence * 100)}%)` : ''}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: 'bold' }}>
              Human-in-the-Loop Review ({visibleItems.length} active detections)
            </h2>
            <span style={{ fontSize: '12px', color: '#666' }}>
              Corrections automatically log for model fine-tuning
            </span>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #000', textAlign: 'left', fontSize: '12px', color: '#444' }}>
                <th style={{ padding: '6px 0' }}>Class Detection</th>
                <th style={{ padding: '6px 0' }}>Certainty</th>
                <th style={{ padding: '6px 0' }}>Status / Action</th>
                <th style={{ padding: '6px 0', textAlign: 'right' }}>False Positive</th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map((it) => {
                const conf = it.confidence ?? 1.0;
                const isLow = conf < 0.60;
                return (
                  <tr key={it.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '10px 0' }}>
                      <select
                        value={it.label}
                        onChange={(e) => updateLabel(it.id, e.target.value)}
                        style={{
                          border: it.userEdited ? '2px solid var(--color-primary-accent, #4A69B3)' : '1px solid #000',
                          padding: '4px 8px',
                          fontSize: '13px',
                          background: it.userEdited ? '#f0f4ff' : '#fff',
                          fontWeight: it.userEdited ? 'bold' : 'normal'
                        }}
                      >
                        {FOOD_CLASSES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                      {it.userEdited && (
                        <span style={{ fontSize: '11px', color: 'var(--color-primary-accent, #4A69B3)', marginLeft: '8px' }}>
                          (Corrected)
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px 0' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 6px',
                        fontSize: '11px',
                        border: '1px solid #ccc',
                        background: isLow ? '#ffebee' : '#f5f5f5',
                        color: isLow ? 'var(--color-attention, #BA3801)' : '#000',
                        fontWeight: isLow ? 'bold' : 'normal'
                      }}>
                        {Math.round(conf * 100)}% {isLow ? '⚠️ Review' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '10px 0', fontSize: '12px', color: '#555' }}>
                      {it.label === 'jar' ? (
                        <span style={{ color: 'var(--color-attention, #BA3801)', fontWeight: '500' }}>
                          Needs specific food choice
                        </span>
                      ) : (
                        `Est. shelf life: ${it.days} days`
                      )}
                    </td>
                    <td style={{ padding: '10px 0', textAlign: 'right' }}>
                      <button
                        onClick={() => removeFalsePositive(it.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-error, #BA3801)',
                          textDecoration: 'underline',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                        title="Reject bounding box & log as false positive"
                      >
                        Reject Box
                      </button>
                    </td>
                  </tr>
                );
              })}
              {visibleItems.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '24px 0', color: '#888' }}>
                    No detections match this confidence threshold. Lower the slider to see lower-certainty boxes.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={runAiAndTrack}
              disabled={visibleItems.length === 0}
              style={{
                background: visibleItems.length === 0 ? '#999' : '#000',
                color: '#fff',
                border: '1px solid #000',
                padding: '10px 20px',
                fontSize: '13px',
                cursor: visibleItems.length === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              Confirm and Track ({visibleItems.length} items)
            </button>
            <button
              onClick={() => setStep(1)}
              style={{ background: '#fff', color: '#000', border: '1px solid #000', padding: '10px 16px', fontSize: '13px', cursor: 'pointer' }}
            >
              Retake
            </button>
          </div>
        </section>
      )}

      {/* Step 3: Processing */}
      {step === 3 && (
        <section style={{ textAlign: 'center', padding: '60px 0' }}>
          <p style={{ fontSize: '14px', marginBottom: '8px' }}>Processing FoodKeeper storage guidelines & shelf life...</p>
          <p style={{ fontSize: '12px', color: '#666' }}>Applying USDA expiration rules to confirmed inventory</p>
        </section>
      )}

      {/* Step 4: Tracking Output */}
      {step === 4 && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: 'bold' }}>Active Refrigerator Inventory ({tracking.length} items)</h2>
            <button
              onClick={() => setStep(1)}
              style={{ background: '#000', color: '#fff', border: '1px solid #000', padding: '6px 12px', fontSize: '12px', cursor: 'pointer' }}
            >
              + Scan New Photo
            </button>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', marginBottom: '32px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #000', textAlign: 'left' }}>
                <th style={{ padding: '8px 0' }}>Item</th>
                <th style={{ padding: '8px 0' }}>Days Remaining</th>
                <th style={{ padding: '8px 0' }}>Safety Status</th>
                <th style={{ padding: '8px 0', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {tracking.map((t) => {
                const isUrgent = t.days <= 3;
                return (
                  <tr key={t.id} style={{ borderBottom: '1px solid #ddd' }}>
                    <td style={{ padding: '10px 0', textTransform: 'capitalize', fontWeight: 'bold' }}>{t.label}</td>
                    <td style={{ padding: '10px 0' }}>{t.days} days</td>
                    <td style={{ padding: '10px 0' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        background: isUrgent ? '#ffebee' : '#e8f5e9',
                        color: isUrgent ? 'var(--color-attention, #BA3801)' : '#2e7d32',
                        fontWeight: 'bold'
                      }}>
                        {isUrgent ? 'Consume Soon' : 'Fresh'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 0', textAlign: 'right' }}>
                      <button
                        onClick={() => removeTracked(t.id)}
                        style={{ background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer', fontSize: '12px' }}
                      >
                        Consume / Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Active Learning Summary Panel */}
          {feedbackQueue.length > 0 && (
            <div style={{ border: '1px solid #ccc', background: '#fafafa', padding: '16px', borderRadius: '4px', fontSize: '12px' }}>
              <h3 style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '8px' }}>
                Active Learning / Human-in-the-Loop Audit Log ({feedbackQueue.length} events logged this session)
              </h3>
              <p style={{ color: '#666', marginBottom: '12px' }}>
                These user annotations are structured for the next model retraining cycle to correct edge cases and reduce false positives:
              </p>
              <ul style={{ paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {feedbackQueue.map((item, idx) => (
                  <li key={idx} style={{ fontFamily: 'monospace' }}>
                    <strong>[{item.type}]</strong> {item.predicted_label}
                    {item.corrected_label ? ` ➔ ${item.corrected_label}` : ' (rejected false positive)'} | Conf: {Math.round(item.confidence * 100)}%
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

