import React, { useState, useRef, useEffect } from 'react';
import { FOOD_CLASSES, INITIAL_DETECTIONS } from './mockData';
import { estimateShelfLife, sendFeedback, detectFridgeItems } from './services/api';

const SAMPLE_IMAGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

export default function App() {
  // Steps: 1 = Capture, 2 = Review, 3 = Processing, 4 = Inventory
  const [step, setStep] = useState(1);
  const [image, setImage] = useState(SAMPLE_IMAGE);
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionError, setDetectionError] = useState(null);
  const [rawDetections, setRawDetections] = useState([]);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [tracking, setTracking] = useState([
    { id: 't1', label: 'yogurt', packageState: 'sealed', days: 14 },
    { id: 't2', label: 'egg', packageState: 'sealed', days: 21 }
  ]);

  // Helper to format class labels for friendly frontend display (e.g. 'bell_pepper' -> 'bell pepper')
  const formatLabel = (label) => (label ? label.replace(/_/g, ' ') : '');

  // Live Camera state
  const [isCameraActive, setIsCameraActive] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Drawing bounding box state
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [drawingStart, setDrawingStart] = useState(null);
  const [currentBox, setCurrentBox] = useState(null);
  const imageContainerRef = useRef(null);
  const imgElementRef = useRef(null);

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
    setRawDetections([]);
    setDetectionError(null);
    setIsDetecting(true);
    setStep(2);

    // Run real YOLO detection on captured image
    canvas.toBlob(async (blob) => {
      try {
        const results = await detectFridgeItems(blob);
        setRawDetections(
          results.map((it) => ({
            ...it,
            packageState: it.packageState || 'sealed',
            days: it.days || estimateShelfLife(it.label, false)
          }))
        );
      } catch (err) {
        console.error('Detection failed:', err);
        setDetectionError(err.message || 'Detection failed. Ensure the YOLO server is running on port 8000.');
      } finally {
        setIsDetecting(false);
      }
    }, 'image/jpeg');
  };

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (file) {
      stopCamera();
      setImage(URL.createObjectURL(file));
      setRawDetections([]);
      setDetectionError(null);
      setIsDetecting(true);
      setStep(2);

      try {
        const results = await detectFridgeItems(file);
        setRawDetections(
          results.map((it) => ({
            ...it,
            packageState: it.packageState || 'sealed',
            days: it.days || estimateShelfLife(it.label, false)
          }))
        );
      } catch (err) {
        console.error('Detection failed:', err);
        setDetectionError(err.message || 'Detection failed. Ensure the YOLO server is running on port 8000.');
      } finally {
        setIsDetecting(false);
      }
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

  // Custom edit shelf life days directly in review
  const updateDays = (id, newDays) => {
    const parsed = Math.max(1, parseInt(newDays, 10) || 1);
    setRawDetections((prev) =>
      prev.map((it) => (it.id === id ? { ...it, days: parsed, userEditedDays: true } : it))
    );
  };

  // Edit shelf life days directly in inventory tracking
  const updateTrackingDays = (id, newDays) => {
    const parsed = Math.max(1, parseInt(newDays, 10) || 1);
    setTracking((prev) =>
      prev.map((it) => (it.id === id ? { ...it, days: parsed } : it))
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
  const addMissedItem = (customBbox = [0.35, 0.35, 0.65, 0.65]) => {
    const defaultLabel = 'apple';
    const newItem = {
      id: String(Date.now()),
      label: defaultLabel,
      confidence: 1.0,
      packageState: 'sealed',
      days: estimateShelfLife(defaultLabel, false),
      bbox: customBbox,
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

  const getRelativeCoords = (e) => {
    const rect = imgElementRef.current?.getBoundingClientRect() || imageContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    return { x, y };
  };

  const handleMouseDown = (e) => {
    if (!isDrawingMode) return;
    e.preventDefault();
    const coords = getRelativeCoords(e);
    setDrawingStart(coords);
    setCurrentBox({ xmin: coords.x, ymin: coords.y, xmax: coords.x, ymax: coords.y });
  };

  const handleMouseMove = (e) => {
    if (!isDrawingMode || !drawingStart) return;
    const coords = getRelativeCoords(e);
    setCurrentBox({
      xmin: Math.min(drawingStart.x, coords.x),
      ymin: Math.min(drawingStart.y, coords.y),
      xmax: Math.max(drawingStart.x, coords.x),
      ymax: Math.max(drawingStart.y, coords.y)
    });
  };

  const handleMouseUp = () => {
    if (!isDrawingMode || !drawingStart || !currentBox) {
      setDrawingStart(null);
      setCurrentBox(null);
      return;
    }

    const width = currentBox.xmax - currentBox.xmin;
    const height = currentBox.ymax - currentBox.ymin;

    // Only create box if user actually dragged a reasonable size (at least 2% in width & height)
    if (width > 0.02 && height > 0.02) {
      addMissedItem([currentBox.ymin, currentBox.xmin, currentBox.ymax, currentBox.xmax]);
      setIsDrawingMode(false);
    }

    setDrawingStart(null);
    setCurrentBox(null);
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
        <h1 style={{ fontSize: '24px', fontWeight: 700, letterSpacing: '-0.5px' }}>Fridge Tracker</h1>
        <span style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>Food Safety & Inventory</span>
      </header>

      {/* Step 1: Capture / Upload */}
      {step === 1 && (
        <section aria-labelledby="capture-heading">
          <h2 id="capture-heading" className="sr-only" style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', border: 0 }}>
            Capture or Upload Food Photo
          </h2>
          {isCameraActive ? (
            <div style={{ border: '2px solid var(--color-border)', marginBottom: '24px', background: '#000', textAlign: 'center' }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                aria-label="Live camera preview of fridge shelf"
                style={{ width: '100%', maxHeight: '440px', display: 'block', objectFit: 'cover' }}
              />
              <div style={{ padding: '16px', background: '#ffffff', borderTop: '1px solid var(--color-border)', display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <button
                  type="button"
                  onClick={capturePhoto}
                  style={{
                    background: 'var(--color-primary-accent)',
                    color: '#ffffff',
                    border: 'none',
                    padding: '12px 24px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    minHeight: '44px'
                  }}
                >
                  Snap Photo
                </button>
                <button
                  type="button"
                  onClick={stopCamera}
                  style={{
                    background: '#ffffff',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)',
                    padding: '12px 18px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    minHeight: '44px'
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
              <p style={{ marginBottom: '24px', fontSize: '16px' }}>Scan your fridge shelves using your camera or upload a photo.</p>
              
              <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={startCamera}
                  style={{
                    background: 'var(--color-primary-accent)',
                    color: '#ffffff',
                    padding: '12px 24px',
                    fontSize: '15px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: 'none',
                    minHeight: '44px'
                  }}
                >
                  Open Live Camera
                </button>

                <label style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: '#ffffff',
                  color: 'var(--color-text)',
                  border: '1px solid var(--color-border)',
                  padding: '12px 24px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  minHeight: '44px'
                }}>
                  Upload Image
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/jpg"
                    onChange={handleFile}
                    aria-label="Upload fridge image"
                    style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', border: 0 }}
                  />
                </label>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Step 2: Review Scanned Items */}
      {step === 2 && (
        <section aria-labelledby="review-heading">
          {detectionError && (
            <div
              role="alert"
              style={{
                background: '#fff2f0',
                border: '1px solid var(--color-error)',
                color: 'var(--color-error)',
                padding: '12px 16px',
                marginBottom: '16px',
                fontSize: '14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <span><strong>Detection Error:</strong> {detectionError}</span>
              <button
                type="button"
                onClick={() => setDetectionError(null)}
                aria-label="Dismiss error"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-error)', fontWeight: 'bold', fontSize: '18px', padding: '4px 8px', minHeight: '36px' }}
              >
                ✕
              </button>
            </div>
          )}

          {isDetecting && (
            <div
              role="status"
              aria-live="polite"
              style={{
                background: '#f0f5ff',
                border: '1px solid #adc6ff',
                color: '#1d39c4',
                padding: '12px 16px',
                marginBottom: '16px',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}
            >
              <span aria-hidden="true">⚙️</span>
              <span><strong>Running YOLO model...</strong> Detecting fridge food items in the image.</span>
            </div>
          )}

          {/* Sensitivity / Detection Slider */}
          <div style={{
            border: '1px solid var(--color-border)',
            padding: '16px 18px',
            marginBottom: '20px',
            background: '#fafafa'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label htmlFor="detection-slider" style={{ fontSize: '14px', fontWeight: 600 }}>
                Detection Sensitivity:
              </label>
              <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }} aria-live="polite">
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
              aria-valuemin="0.20"
              aria-valuemax="0.95"
              aria-valuenow={confidenceThreshold}
              aria-valuetext={`${Math.round(confidenceThreshold * 100)} percent confidence`}
              style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--color-primary-accent)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
              <span>Show more items</span>
              <span>Only high certainty</span>
            </div>
          </div>

          {/* Photo with Bounding Boxes */}
          <div
            ref={imageContainerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            style={{
              position: 'relative',
              border: isDrawingMode ? '2px solid var(--color-primary-accent)' : '1px solid var(--color-border)',
              marginBottom: '24px',
              background: '#000000',
              cursor: isDrawingMode ? 'crosshair' : 'default',
              userSelect: 'none'
            }}
          >
            <img
              ref={imgElementRef}
              src={image}
              alt="Scanned fridge interior preview"
              draggable={false}
              style={{ display: 'block', width: '100%', maxHeight: '420px', objectFit: 'contain', pointerEvents: 'none' }}
            />
            <svg
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
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
                      {formatLabel(it.label)}
                    </text>
                  </g>
                );
              })}

              {/* In-progress drawing preview box */}
              {isDrawingMode && currentBox && (
                <rect
                  x={currentBox.xmin * 1000}
                  y={currentBox.ymin * 1000}
                  width={(currentBox.xmax - currentBox.xmin) * 1000}
                  height={(currentBox.ymax - currentBox.ymin) * 1000}
                  fill="rgba(255, 255, 255, 0.15)"
                  stroke="var(--color-accent, #faad14)"
                  strokeWidth="3"
                  strokeDasharray="6,4"
                />
              )}
            </svg>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
            <div>
              <h2 id="review-heading" style={{ fontSize: '18px', fontWeight: 700 }}>Review Detected Items</h2>
              <p style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                {isDrawingMode
                  ? 'Click and drag on the photo above to outline the missed food item.'
                  : 'Verify items and set package state. FoodKeeper guidelines adjust shelf life automatically.'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setIsDrawingMode(!isDrawingMode)}
                style={{
                  background: isDrawingMode ? 'var(--color-primary-accent)' : '#ffffff',
                  color: isDrawingMode ? '#ffffff' : 'var(--color-text)',
                  border: '1px solid var(--color-border)',
                  padding: '8px 14px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  minHeight: '44px'
                }}
              >
                {isDrawingMode ? 'Drawing... (Click & Drag)' : '+ Draw Missed Item'}
              </button>
              {isDrawingMode && (
                <button
                  type="button"
                  onClick={() => {
                    setIsDrawingMode(false);
                    setCurrentBox(null);
                    setDrawingStart(null);
                  }}
                  style={{
                    background: '#ffffff',
                    border: '1px solid var(--color-border)',
                    padding: '8px 12px',
                    fontSize: '13px',
                    cursor: 'pointer',
                    minHeight: '44px'
                  }}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px', fontSize: '13px' }}>
            <caption className="sr-only" style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', border: 0 }}>
              List of food items detected by model for verification
            </caption>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', fontSize: '13px', color: 'var(--color-text)' }}>
                <th scope="col" style={{ padding: '10px 0', width: '34%' }}>Item</th>
                <th scope="col" style={{ padding: '10px 0', width: '22%' }}>Package State</th>
                <th scope="col" style={{ padding: '10px 0', width: '20%' }}>Est. Shelf Life</th>
                <th scope="col" style={{ padding: '10px 0', width: '14%' }}>Certainty</th>
                <th scope="col" style={{ padding: '10px 0', textAlign: 'right', width: '10%' }}>Actions</th>
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
                        aria-label={`Food classification for item ${it.id}`}
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
                          width: '90%',
                          minHeight: '40px',
                          textTransform: 'capitalize'
                        }}
                      >
                        {FOOD_CLASSES.map((c) => (
                          <option key={c} value={c}>
                            {formatLabel(c)}
                          </option>
                        ))}
                      </select>
                    </td>

                    <td style={{ padding: '12px 0' }}>
                      <select
                        aria-label={`Package condition for ${it.label}`}
                        value={it.packageState || 'sealed'}
                        onChange={(e) => togglePackageState(it.id, e.target.value)}
                        style={{
                          border: '1px solid var(--color-border)',
                          padding: '6px 8px',
                          fontSize: '13px',
                          background: '#ffffff',
                          minHeight: '40px'
                        }}
                      >
                        <option value="sealed">Sealed</option>
                        <option value="opened">Opened</option>
                      </select>
                    </td>

                    <td style={{ padding: '12px 0', fontSize: '13px', color: '#111' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input
                          type="number"
                          min="1"
                          max="365"
                          aria-label={`Shelf life days remaining for ${it.label}`}
                          value={it.days}
                          onChange={(e) => updateDays(it.id, e.target.value)}
                          style={{
                            width: '56px',
                            padding: '6px 6px',
                            fontSize: '13px',
                            border: it.userEditedDays ? '2px solid var(--color-primary-accent)' : '1px solid var(--color-border)',
                            background: '#ffffff',
                            borderRadius: 0,
                            minHeight: '40px'
                          }}
                        />
                        <span>days</span>
                      </div>
                      {it.label === 'jar' && (
                        <div style={{ color: 'var(--color-attention)', fontSize: '12px', marginTop: '4px', fontWeight: 600 }}>
                          Select food type
                        </div>
                      )}
                    </td>

                    <td style={{ padding: '12px 0', fontSize: '13px' }}>
                      {it.manuallyAdded ? (
                        <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>Added</span>
                      ) : it.userEdited ? (
                        <span style={{ color: 'var(--color-primary-accent)', fontWeight: 600 }}>Edited</span>
                      ) : isUnsure ? (
                        <span style={{ color: 'var(--color-attention)', fontWeight: 600 }}>Unsure ({Math.round(conf * 100)}%)</span>
                      ) : (
                        <span style={{ color: 'var(--color-text-muted)' }}>{Math.round(conf * 100)}%</span>
                      )}
                    </td>

                    <td style={{ padding: '12px 0', textAlign: 'right' }}>
                      <button
                        type="button"
                        onClick={() => removeItem(it.id)}
                        aria-label={`Remove ${it.label} from detected list`}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-error)',
                          textDecoration: 'underline',
                          cursor: 'pointer',
                          fontSize: '13px',
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
              {visibleItems.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px 0', color: 'var(--color-text-muted)', fontSize: '14px' }}>
                    {isDetecting
                      ? 'Analyzing image with YOLO...'
                      : 'No items match this sensitivity level. Drag the slider to the left to show more items, or click "+ Add Missed Item".'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={confirmAndTrack}
              disabled={visibleItems.length === 0}
              style={{
                background: visibleItems.length === 0 ? '#888888' : 'var(--color-primary-accent)',
                color: '#ffffff',
                border: 'none',
                padding: '12px 24px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: visibleItems.length === 0 ? 'not-allowed' : 'pointer',
                minHeight: '44px'
              }}
            >
              Add to Fridge Inventory ({visibleItems.length})
            </button>
            <button
              type="button"
              onClick={() => {
                stopCamera();
                setStep(1);
              }}
              style={{
                background: '#ffffff',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '12px 20px',
                fontSize: '14px',
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              Back
            </button>
          </div>
        </section>
      )}

      {/* Step 3: Loading */}
      {step === 3 && (
        <section aria-live="assertive" style={{ textAlign: 'center', padding: '80px 0' }}>
          <p style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>Updating fridge inventory...</p>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>Applying USDA FoodKeeper guidelines.</p>
        </section>
      )}

      {/* Step 4: Fridge Inventory */}
      {step === 4 && (
        <section aria-labelledby="inventory-heading">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '20px' }}>
            <h2 id="inventory-heading" style={{ fontSize: '18px', fontWeight: 700 }}>Current Fridge Inventory ({tracking.length} items)</h2>
            <button
              type="button"
              onClick={() => setStep(1)}
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

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <caption className="sr-only" style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', border: 0 }}>
              Current list of tracked fridge items with remaining shelf life
            </caption>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', fontSize: '13px', color: 'var(--color-text)' }}>
                <th scope="col" style={{ padding: '10px 0', width: '38%' }}>Food Item</th>
                <th scope="col" style={{ padding: '10px 0', width: '24%' }}>Package State</th>
                <th scope="col" style={{ padding: '10px 0', width: '26%' }}>Shelf Life Remaining</th>
                <th scope="col" style={{ padding: '10px 0', textAlign: 'right', width: '12%' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tracking.map((t) => {
                const isUrgent = t.days <= 3;
                return (
                  <tr key={t.id} style={{ borderBottom: '1px solid #e5e5e5' }}>
                    <td style={{ padding: '12px 0', textTransform: 'capitalize', fontWeight: 600 }}>
                      {formatLabel(t.label)}
                    </td>
                    <td style={{ padding: '12px 0', textTransform: 'capitalize', color: 'var(--color-text-muted)' }}>
                      {t.packageState || 'Sealed'}
                    </td>
                    <td style={{ padding: '12px 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input
                          type="number"
                          min="1"
                          max="365"
                          aria-label={`Days remaining for ${t.label}`}
                          value={t.days}
                          onChange={(e) => updateTrackingDays(t.id, e.target.value)}
                          style={{
                            width: '56px',
                            padding: '6px 6px',
                            fontSize: '13px',
                            border: '1px solid var(--color-border)',
                            color: isUrgent ? 'var(--color-attention)' : 'inherit',
                            fontWeight: isUrgent ? 700 : 400,
                            minHeight: '40px'
                          }}
                        />
                        <span style={{
                          color: isUrgent ? 'var(--color-attention)' : 'inherit',
                          fontWeight: isUrgent ? 700 : 400
                        }}>
                          {t.days === 1 ? 'day' : 'days'}
                          {isUrgent ? ' (use soon)' : ''}
                        </span>
                      </div>
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
              ⚠️ Food Safety & USDA FoodKeeper Advisory
            </div>
            <p>
              Expiration windows and shelf-life recommendations are advisories calculated using guidelines from the 
              <strong> USDA FSIS FoodKeeper</strong> dataset. These predictions cannot replace sensory inspection 
              (sight, smell, texture). Always inspect perishable items before consumption; when in doubt, discard.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}



