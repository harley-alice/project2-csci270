import React, { useState } from 'react';
import { FOOD_CLASSES, INITIAL_DETECTIONS } from './mockData';

const SAMPLE_IMAGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

export default function App() {
  // Steps: 1 = Capture, 2 = Confirm items, 3 = Processing, 4 = Tracking
  const [step, setStep] = useState(1);
  const [image, setImage] = useState(SAMPLE_IMAGE);
  const [items, setItems] = useState(INITIAL_DETECTIONS);
  const [tracking, setTracking] = useState([
    { id: 't1', label: 'yogurt', days: 5 },
    { id: 't2', label: 'eggs', days: 12 }
  ]);

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setStep(2);
    }
  };

  const updateLabel = (id, newLabel) => {
    setItems(items.map((it) => (it.id === id ? { ...it, label: newLabel } : it)));
  };

  const removeItem = (id) => {
    setItems(items.filter((it) => it.id !== id));
  };

  const runAiAndTrack = () => {
    setStep(3);
    setTimeout(() => {
      const newTracked = items.map((it) => ({
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
    <div style={{ maxWidth: '720px', margin: '40px auto', padding: '0 20px', fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #000', paddingBottom: '16px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 'bold', letterSpacing: '-0.5px' }}>Fridge Tracker</h1>
        <span style={{ fontSize: '13px' }}>Draft v0.1</span>
      </header>

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
              onClick={() => setStep(2)}
              style={{ background: 'none', border: '1px solid #000', padding: '8px 16px', fontSize: '12px', cursor: 'pointer' }}
            >
              Use sample image
            </button>
          </div>
        </section>
      )}

      {/* Step 2: Confirm Items */}
      {step === 2 && (
        <section>
          <div style={{ position: 'relative', border: '1px solid #000', marginBottom: '24px', background: '#000' }}>
            <img src={image} alt="Fridge" style={{ display: 'block', width: '100%', maxHeight: '420px', objectFit: 'contain' }} />
            <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox="0 0 1000 1000" preserveAspectRatio="none">
              {items.map((it) => {
                const [ymin, xmin, ymax, xmax] = it.bbox;
                return (
                  <g key={it.id}>
                    <rect
                      x={xmin * 1000}
                      y={ymin * 1000}
                      width={(xmax - xmin) * 1000}
                      height={(ymax - ymin) * 1000}
                      fill="none"
                      stroke="#fff"
                      strokeWidth="2"
                    />
                    <text
                      x={xmin * 1000 + 6}
                      y={ymin * 1000 + 16}
                      fill="#fff"
                      fontSize="12"
                      fontWeight="bold"
                      fontFamily="Helvetica"
                    >
                      {it.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <h2 style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '12px' }}>Confirm Items:</h2>

          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px', fontSize: '13px' }}>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px 0' }}>
                    <select
                      value={it.label}
                      onChange={(e) => updateLabel(it.id, e.target.value)}
                      style={{ border: '1px solid #000', padding: '4px 8px', fontSize: '13px', background: '#fff' }}
                    >
                      {FOOD_CLASSES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </td>
                  <td style={{ padding: '8px 0', textAlign: 'right' }}>
                    <button
                      onClick={() => removeItem(it.id)}
                      style={{ background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer', fontSize: '12px' }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={runAiAndTrack}
              style={{ background: '#000', color: '#fff', border: '1px solid #000', padding: '10px 20px', fontSize: '13px', cursor: 'pointer' }}
            >
              Confirm and Track
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
          <p style={{ fontSize: '14px' }}>Processing expiration dates...</p>
        </section>
      )}

      {/* Step 4: Tracking Output */}
      {step === 4 && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: 'bold' }}>Tracking ({tracking.length} items)</h2>
            <button
              onClick={() => setStep(1)}
              style={{ background: '#000', color: '#fff', border: '1px solid #000', padding: '6px 12px', fontSize: '12px', cursor: 'pointer' }}
            >
              + Scan New Photo
            </button>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #000', textAlign: 'left' }}>
                <th style={{ padding: '8px 0' }}>Item</th>
                <th style={{ padding: '8px 0' }}>Days Remaining</th>
                <th style={{ padding: '8px 0', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {tracking.map((t) => (
                <tr key={t.id} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '10px 0', textTransform: 'capitalize' }}>{t.label}</td>
                  <td style={{ padding: '10px 0' }}>{t.days} days</td>
                  <td style={{ padding: '10px 0', textAlign: 'right' }}>
                    <button
                      onClick={() => removeTracked(t.id)}
                      style={{ background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer', fontSize: '12px' }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
