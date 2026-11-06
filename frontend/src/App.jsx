import React, { useState, useRef, useEffect } from 'react';
import { FOOD_CLASSES, INITIAL_DETECTIONS } from './mockData';
import { estimateShelfLife, sendFeedback } from './services/api';

const SAMPLE_IMAGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

export default function App() {
  // Steps: 1 = Capture, 2 = Review, 3 = Processing, 4 = Inventory
  const [step, setStep] = useState(1);
  const [image, setImage] = useState(SAMPLE_IMAGE);
  const [rawDetections, setRawDetections] = useState(
    INITIAL_DETECTIONS.map((it) => ({
      ...it,
      packageState: 'sealed',
      days: estimateShelfLife(it.label, false)
    }))
  );
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [tracking, setTracking] = useState([
    { id: 't1', label: 'yogurt', packageState: 'sealed', days: 14 },
    { id: 't2', label: 'egg', packageState: 'sealed', days: 21 }
  ]);

  // Live Camera state
  const [isCameraActive, setIsCameraActive] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Stop camera when navigating away from step 1
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    try {
      setIsCameraActive(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Camera access denied or unavailable:', err);
      alert('Camera access could not be started. Check your browser permissions or use file upload.');
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');

    stopCamera();
    setImage(dataUrl);
    setRawDetections(
      INITIAL_DETECTIONS.map((it) => ({
        ...it,
        packageState: 'sealed',
        days: estimateShelfLife(it.label, false)
      }))
    );
    setStep(2);
  };

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      stopCamera();
      setImage(URL.createObjectURL(file));
      setRawDetections(
        INITIAL_DETECTIONS.map((it) => ({
          ...it,
          packageState: 'sealed',
          days: estimateShelfLife(it.label, false)
        }))
      );
      setStep(2);
    }
  };

  // Re-label an existing item
  const updateLabel = (id, newLabel) => {
    const targetItem = rawDetections.find((it) => it.id === id);
    if (!targetItem || targetItem.label === newLabel) return;

    sendFeedback({
      timestamp: new Date().toISOString(),
      type: 'user_correction',
      image_source: image.startsWith('data:') ? 'camera' : 'upload',
      detection_id: id,
      predicted_label: targetItem.label,
      corrected_label: newLabel,
      confidence: targetItem.confidence ?? 1.0,
      bbox: targetItem.bbox
    });

    setRawDetections((prev) =>
      prev.map((it) =>
        it.id === id
          ? {
              ...it,
              label: newLabel,
              userEdited: true,
              days: estimateShelfLife(newLabel, it.packageState === 'opened')
            }
          : it
      )
    );
  };

  // Toggle opened vs sealed package state
  const togglePackageState = (id, newState) => {
    setRawDetections((prev) =>
      prev.map((it) =>
        it.id === id
          ? {
              ...it,
              packageState: newState,
              days: estimateShelfLife(it.label, newState === 'opened')
            }
          : it
      )
    );
  };

  // Reject an incorrect bounding box (false positive)
  const removeItem = (id) => {
    const targetItem = rawDetections.find((it) => it.id === id);
    if (targetItem) {
      sendFeedback({
        timestamp: new Date().toISOString(),
        type: 'false_positive_rejected',
        image_source: image.startsWith('data:') ? 'camera' : 'upload',
        detection_id: id,
        predicted_label: targetItem.label,
        corrected_label: null,
        confidence: targetItem.confidence ?? 1.0,
        bbox: targetItem.bbox
      });
    }

    setRawDetections((prev) => prev.filter((it) => it.id !== id));
  };

  // Add missed item (false negative / active learning hook)
  const addMissedItem = () => {
    const defaultLabel = 'apple';
    const newItem = {
      id: String(Date.now()),
      label: defaultLabel,
      confidence: 1.0,
      packageState: 'sealed',
      days: estimateShelfLife(defaultLabel, false),
      bbox: [0.35, 0.35, 0.65, 0.65], // Center placeholder box
      userEdited: true,
      manuallyAdded: true
    };

    sendFeedback({
      timestamp: new Date().toISOString(),
      type: 'missed_item_added',
      image_source: image.startsWith('data:') ? 'camera' : 'upload',
      detection_id: newItem.id,
      predicted_label: null,
      corrected_label: defaultLabel,
      confidence: 1.0,
      bbox: newItem.bbox
    });

    setRawDetections((prev) => [...prev, newItem]);
  };

  const visibleItems = rawDetections.filter(
    (it) => it.userEdited || (it.confidence ?? 1.0) >= confidenceThreshold
  );

  const confirmAndTrack = () => {
    setStep(3);
    setTimeout(() => {
      const newItems = visibleItems.map((it) => ({
        id: String(Date.now() + Math.random()),
        label: it.label,
        packageState: it.packageState || 'sealed',
        days: it.days
      }));
      setTracking([...tracking, ...newItems]);
      setStep(4);
    }, 900);
  };

  const removeTracked = (id) => {
    setTracking(tracking.filter((t) => t.id !== id));
  };

  return (
    <div style={{ maxWidth: '720px', margin: '48px auto', padding: '0 24px' }}>
      <header style={{ borderBottom: '2px solid var(--color-border)', paddingBottom: '16px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1 style={{ fontSize: '22px', fontWeight: 700, letterSpacing: '-0.5px' }}>Fridge Tracker</h1>
        <span style={{ fontSize: '13px', color: '#555' }}>Food Safety & Inventory</span>
      </header>

      {/* Step 1: Capture / Upload */}
      {step === 1 && (
        <section>
          {isCameraActive ? (
            <div style={{ border: '2px solid var(--color-border)', marginBottom: '24px', background: '#000', textAlign: 'center' }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                style={{ width: '100%', maxHeight: '440px', display: 'block', objectFit: 'cover' }}
              />
              <div style={{ padding: '16px', background: '#ffffff', borderTop: '1px solid var(--color-border)', display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <button
                  onClick={capturePhoto}
                  style={{
                    background: 'var(--color-primary-accent)',
                    color: '#ffffff',
                    border: 'none',
                    padding: '10px 24px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Snap Photo
                </button>
                <button
                  onClick={stopCamera}
                  style={{
                    background: '#ffffff',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)',
                    padding: '10px 18px',
                    fontSize: '13px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div style={{
              border: '2px dashed var(--color-border)',
              padding: '64px 24px',
              textAlign: 'center',
              marginBottom: '24px',
              background: '#fafafa'
            }}>
              <p style={{ marginBottom: '20px', fontSize: '15px' }}>Scan your fridge shelves using your camera or upload a photo.</p>
              
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={startCamera}
                  style={{
                    background: 'var(--color-primary-accent)',
                    color: '#ffffff',
                    padding: '10px 22px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: 'none'
                  }}
                >
                  Open Live Camera
                </button>

                <label style={{
                  display: 'inline-block',
                  background: '#ffffff',
                  color: 'var(--color-text)',
                  border: '1px solid var(--color-border)',
                  padding: '9px 20px',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}>
                  Upload Image
                  <input type="file" accept="image/*" onChange={handleFile} style={{ display: 'none' }} />
                </label>
              </div>
            </div>
          )}

          {!isCameraActive && (
            <div style={{ textAlign: 'center' }}>
              <button
                onClick={() => {
                  setImage(SAMPLE_IMAGE);
                  setRawDetections(
                    INITIAL_DETECTIONS.map((it) => ({
                      ...it,
                      packageState: 'sealed',
                      days: estimateShelfLife(it.label, false)
                    }))
                  );
                  setStep(2);
                }}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--color-border)',
                  padding: '8px 18px',
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
              >
                Use demo fridge image
              </button>
            </div>
          )}
        </section>
      )}

      {/* Step 2: Review Scanned Items */}
      {step === 2 && (
        <section>
          {/* Sensitivity / Detection Slider */}
          <div style={{
            border: '1px solid var(--color-border)',
            padding: '14px 18px',
            marginBottom: '20px',
            background: '#fafafa'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label htmlFor="detection-slider" style={{ fontSize: '13px', fontWeight: 600 }}>
                Detection Sensitivity:
              </label>
              <span style={{ fontSize: '12px', color: '#444' }}>
                Showing {visibleItems.length} of {rawDetections.length} items
              </span>
            </div>
            <input
              id="detection-slider"
              type="range"
              min="0.20"
              max="0.95"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-primary-accent)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#666', marginTop: '4px' }}>
              <span>Show more items</span>
              <span>Only high certainty</span>
            </div>
          </div>

          {/* Photo with Bounding Boxes */}
          <div style={{ position: 'relative', border: '1px solid var(--color-border)', marginBottom: '24px', background: '#000000' }}>
            <img src={image} alt="Fridge" style={{ display: 'block', width: '100%', maxHeight: '420px', objectFit: 'contain' }} />
            <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox="0 0 1000 1000" preserveAspectRatio="none">
              {visibleItems.map((it) => {
                const [ymin, xmin, ymax, xmax] = it.bbox;
                const isUnsure = (it.confidence ?? 1.0) < 0.60;
                const strokeColor = it.userEdited
                  ? 'var(--color-accent)'
                  : isUnsure
                  ? 'var(--color-attention)'
                  : 'var(--color-primary-accent)';

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
                    />
                    <rect
                      x={xmin * 1000}
                      y={Math.max(0, ymin * 1000 - 22)}
                      width={Math.max(70, it.label.length * 10 + 20)}
                      height="22"
                      fill={strokeColor}
                    />
                    <text
                      x={xmin * 1000 + 6}
                      y={Math.max(16, ymin * 1000 - 6)}
                      fill={it.userEdited ? '#000000' : '#ffffff'}
                      fontSize="12"
                      fontWeight="bold"
                    >
                      {it.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700 }}>Review Detected Items</h2>
              <p style={{ fontSize: '13px', color: '#555', marginTop: '2px' }}>
                Verify items and set package state. FoodKeeper guidelines adjust shelf life automatically.
              </p>
            </div>
            <button
              onClick={addMissedItem}
              style={{
                background: 'transparent',
                border: '1px solid var(--color-border)',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              + Add Missed Item
            </button>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', fontSize: '12px', color: '#555' }}>
                <th style={{ padding: '8px 0', width: '34%' }}>Item</th>
                <th style={{ padding: '8px 0', width: '22%' }}>Package State</th>
                <th style={{ padding: '8px 0', width: '20%' }}>Est. Shelf Life</th>
                <th style={{ padding: '8px 0', width: '14%' }}>Certainty</th>
                <th style={{ padding: '8px 0', textAlign: 'right', width: '10%' }}></th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map((it) => {
                const conf = it.confidence ?? 1.0;
                const isUnsure = conf < 0.60;

                return (
                  <tr key={it.id} style={{ borderBottom: '1px solid #e5e5e5' }}>
                    <td style={{ padding: '12px 0' }}>
                      <select
                        value={it.label}
                        onChange={(e) => updateLabel(it.id, e.target.value)}
                        style={{
                          border: it.userEdited
                            ? '2px solid var(--color-primary-accent)'
                            : '1px solid var(--color-border)',
                          padding: '6px 8px',
                          fontSize: '13px',
                          background: it.userEdited ? '#f4f6fb' : '#ffffff',
                          fontWeight: it.userEdited ? 600 : 400,
                          width: '90%'
                        }}
                      >
                        {FOOD_CLASSES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>

                    <td style={{ padding: '12px 0' }}>
                      <select
                        value={it.packageState || 'sealed'}
                        onChange={(e) => togglePackageState(it.id, e.target.value)}
                        style={{
                          border: '1px solid var(--color-border)',
                          padding: '5px 8px',
                          fontSize: '12px',
                          background: '#ffffff'
                        }}
                      >
                        <option value="sealed">Sealed</option>
                        <option value="opened">Opened</option>
                      </select>
                    </td>

                    <td style={{ padding: '12px 0', fontSize: '13px', color: '#333' }}>
                      {it.label === 'jar' ? (
                        <span style={{ color: 'var(--color-attention)' }}>Select contents</span>
                      ) : (
                        `${it.days} days`
                      )}
                    </td>

                    <td style={{ padding: '12px 0', fontSize: '12px' }}>
                      {it.manuallyAdded ? (
                        <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>Added</span>
                      ) : it.userEdited ? (
                        <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>Edited</span>
                      ) : isUnsure ? (
                        <span style={{ color: 'var(--color-attention)', fontWeight: 600 }}>Unsure ({Math.round(conf * 100)}%)</span>
                      ) : (
                        <span style={{ color: '#555' }}>{Math.round(conf * 100)}%</span>
                      )}
                    </td>

                    <td style={{ padding: '12px 0', textAlign: 'right' }}>
                      <button
                        onClick={() => removeItem(it.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-error)',
                          textDecoration: 'underline',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
              {visibleItems.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px 0', color: '#666' }}>
                    No items match this sensitivity level. Drag the slider to the left to show more items, or click "+ Add Missed Item".
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={confirmAndTrack}
              disabled={visibleItems.length === 0}
              style={{
                background: visibleItems.length === 0 ? '#999' : 'var(--color-primary-accent)',
                color: '#ffffff',
                border: 'none',
                padding: '11px 22px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: visibleItems.length === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              Add to Fridge Inventory ({visibleItems.length})
            </button>
            <button
              onClick={() => {
                stopCamera();
                setStep(1);
              }}
              style={{
                background: '#ffffff',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '11px 18px',
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              Back
            </button>
          </div>
        </section>
      )}

      {/* Step 3: Loading */}
      {step === 3 && (
        <section style={{ textAlign: 'center', padding: '80px 0' }}>
          <p style={{ fontSize: '15px', fontWeight: 600, marginBottom: '6px' }}>Updating fridge inventory...</p>
          <p style={{ fontSize: '13px', color: '#666' }}>Applying USDA FoodKeeper guidelines.</p>
        </section>
      )}

      {/* Step 4: Fridge Inventory */}
      {step === 4 && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700 }}>Current Fridge Inventory ({tracking.length} items)</h2>
            <button
              onClick={() => setStep(1)}
              style={{
                background: 'var(--color-primary-accent)',
                color: '#ffffff',
                border: 'none',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              + Scan More Food
            </button>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', fontSize: '12px', color: '#555' }}>
                <th style={{ padding: '8px 0', width: '38%' }}>Food Item</th>
                <th style={{ padding: '8px 0', width: '24%' }}>Package State</th>
                <th style={{ padding: '8px 0', width: '26%' }}>Shelf Life Remaining</th>
                <th style={{ padding: '8px 0', textAlign: 'right', width: '12%' }}></th>
              </tr>
            </thead>
            <tbody>
              {tracking.map((t) => {
                const isUrgent = t.days <= 3;
                return (
                  <tr key={t.id} style={{ borderBottom: '1px solid #e5e5e5' }}>
                    <td style={{ padding: '12px 0', textTransform: 'capitalize', fontWeight: 600 }}>
                      {t.label}
                    </td>
                    <td style={{ padding: '12px 0', textTransform: 'capitalize', color: '#555' }}>
                      {t.packageState || 'Sealed'}
                    </td>
                    <td style={{ padding: '12px 0' }}>
                      <span style={{
                        color: isUrgent ? 'var(--color-attention)' : 'inherit',
                        fontWeight: isUrgent ? 700 : 400
                      }}>
                        {t.days} {t.days === 1 ? 'day' : 'days'}
                        {isUrgent ? ' (use soon)' : ''}
                      </span>
                    </td>
                    <td style={{ padding: '12px 0', textAlign: 'right' }}>
                      <button
                        onClick={() => removeTracked(t.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          textDecoration: 'underline',
                          cursor: 'pointer',
                          fontSize: '12px',
                          color: '#555'
                        }}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}



