import React, { useState } from 'react';
import BoundingBoxOverlay from './components/BoundingBoxOverlay';
import HumanInTheLoopReview from './components/HumanInTheLoopReview';
import InventoryDashboard from './components/InventoryDashboard';
import { MOCK_DETECTIONS, FOOD_METADATA } from './mockData';

const SAMPLE_FRIDGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

export default function App() {
  const [imageSrc, setImageSrc] = useState(SAMPLE_FRIDGE);
  const [detections, setDetections] = useState(MOCK_DETECTIONS);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [selectedId, setSelectedId] = useState(null);

  // Digital fridge state
  const [inventory, setInventory] = useState([
    { id: 'inv-1', label: 'milk', daysRemaining: 6, dateAdded: 'Nov 1' },
    { id: 'inv-2', label: 'chicken', daysRemaining: 1, dateAdded: 'Oct 31' },
    { id: 'inv-3', label: 'spinach', daysRemaining: 3, dateAdded: 'Nov 1' }
  ]);

  // Handle image upload from user camera / gallery
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setImageSrc(url);
      setSelectedId(null);
      // Reset detections with pending state
      setDetections(MOCK_DETECTIONS.map((d) => ({ ...d, status: 'pending' })));
    }
  };

  const handleUpdateDetection = (id, changes) => {
    setDetections((prev) =>
      prev.map((det) => (det.id === id ? { ...det, ...changes } : det))
    );

    // If marked as accepted, add to fridge inventory
    if (changes.status === 'accepted') {
      const det = detections.find((d) => d.id === id);
      if (det) {
        const foodKey = changes.label || det.label;
        const meta = FOOD_METADATA[foodKey] || { defaultDays: 5 };
        setInventory((prev) => [
          ...prev,
          {
            id: `inv-${Date.now()}-${id}`,
            label: foodKey,
            daysRemaining: meta.defaultDays,
            dateAdded: 'Today',
            userCorrected: changes.userCorrected
          }
        ]);
      }
    }
  };

  const handleAcceptAllAboveThreshold = () => {
    const visible = detections.filter(
      (d) => d.confidence >= confidenceThreshold && d.status !== 'rejected'
    );

    setDetections((prev) =>
      prev.map((d) =>
        d.confidence >= confidenceThreshold && d.status !== 'rejected'
          ? { ...d, status: 'accepted' }
          : d
      )
    );

    const newItems = visible.map((det) => {
      const meta = FOOD_METADATA[det.label] || { defaultDays: 5 };
      return {
        id: `inv-${Date.now()}-${det.id}`,
        label: det.label,
        daysRemaining: meta.defaultDays,
        dateAdded: 'Today'
      };
    });

    setInventory((prev) => [...prev, ...newItems]);
  };

  const handleRemoveInventoryItem = (id) => {
    setInventory((prev) => prev.filter((item) => item.id !== id));
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc', color: '#1e293b' }}>
      {/* Friendly Top Navigation */}
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '1px solid #f1f5f9',
          padding: '16px 28px',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
        }}
      >
        <div style={{ maxWidth: '1240px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                backgroundColor: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '22px',
                boxShadow: '0 4px 10px rgba(16, 185, 129, 0.25)'
              }}
            >
              🥗
            </div>
            <div>
              <h1 style={{ fontSize: '19px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>
                FreshTrack
              </h1>
              <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
                Smart Food & Fridge Freshness Assistant
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span
              style={{
                fontSize: '13px',
                color: '#64748b',
                backgroundColor: '#f1f5f9',
                padding: '6px 14px',
                borderRadius: '20px',
                fontWeight: '600'
              }}
            >
              🧊 {inventory.length} items in fridge
            </span>
          </div>
        </div>
      </header>

      {/* Main Experience */}
      <main style={{ maxWidth: '1240px', margin: '28px auto', padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {/* Friendly Hero / Photo Action Bar */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            border: '1px solid #f1f5f9',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.03)',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px'
          }}
        >
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.3px', margin: 0 }}>
              Scan Fridge Groceries
            </h2>
            <p style={{ fontSize: '14px', color: '#64748b', margin: '4px 0 0' }}>
              Take or upload a quick photo of your fridge shelf. We'll identify items and tell you how long they last.
            </p>
          </div>

          <label
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              padding: '11px 22px',
              borderRadius: '12px',
              fontSize: '14px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
              transition: 'all 0.15s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#1d4ed8')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#2563eb')}
          >
            <span>📷</span> Upload New Photo
            <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
          </label>
        </div>

        {/* 2-Column Split: Image on Left, Review on Right */}
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 1fr)', gap: '24px', alignItems: 'stretch' }}>
          <div>
            <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '14px', fontWeight: '700', color: '#475569' }}>
                Your Photo (Click any highlighted item)
              </span>
            </div>
            <BoundingBoxOverlay
              imageUrl={imageSrc}
              detections={detections}
              confidenceThreshold={confidenceThreshold}
              selectedId={selectedId}
              onSelectDetection={setSelectedId}
            />
          </div>

          <div>
            <HumanInTheLoopReview
              detections={detections}
              confidenceThreshold={confidenceThreshold}
              onConfidenceChange={setConfidenceThreshold}
              selectedId={selectedId}
              onSelectDetection={setSelectedId}
              onUpdateDetection={handleUpdateDetection}
              onAcceptAllAboveThreshold={handleAcceptAllAboveThreshold}
            />
          </div>
        </div>

        {/* Fridge Digital Inventory */}
        <InventoryDashboard
          items={inventory}
          onRemoveItem={handleRemoveInventoryItem}
        />
      </main>
    </div>
  );
}
