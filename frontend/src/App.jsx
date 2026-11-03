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

  // Initial cute fridge stock
  const [inventory, setInventory] = useState([
    { id: 'inv-1', label: 'strawberries', daysRemaining: 3, dateAdded: 'Nov 1' },
    { id: 'inv-2', label: 'yogurt', daysRemaining: 7, dateAdded: 'Oct 31' },
    { id: 'inv-3', label: 'milk', daysRemaining: 1, dateAdded: 'Oct 28' },
    { id: 'inv-4', label: 'blueberries', daysRemaining: 5, dateAdded: 'Nov 2' }
  ]);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setImageSrc(url);
      setSelectedId(null);
      setDetections(MOCK_DETECTIONS.map((d) => ({ ...d, status: 'pending' })));
    }
  };

  const handleUpdateDetection = (id, changes) => {
    setDetections((prev) =>
      prev.map((det) => (det.id === id ? { ...det, ...changes } : det))
    );

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
    <div style={{ minHeight: '100vh', paddingBottom: '60px' }}>
      {/* Cutesy Header */}
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '2px solid #fce7f3',
          padding: '16px 32px',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          boxShadow: '0 4px 20px rgba(244, 114, 182, 0.08)'
        }}
      >
        <div style={{ maxWidth: '1240px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '16px',
                backgroundColor: '#fce7f3',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '26px',
                boxShadow: '0 4px 12px rgba(236, 72, 153, 0.2)',
                border: '2px solid #fbcfe8'
              }}
            >
              🌸
            </div>
            <div>
              <h1 style={{ fontSize: '22px', fontWeight: '800', color: '#831843', letterSpacing: '-0.3px', margin: 0 }}>
                Freshy
              </h1>
              <p style={{ fontSize: '12px', color: '#be185d', margin: 0, fontWeight: '600' }}>
                Your cute fridge buddy & snack tracker ✨
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                fontSize: '13px',
                color: '#be185d',
                backgroundColor: '#fdf2f8',
                padding: '8px 18px',
                borderRadius: '20px',
                fontWeight: '700',
                border: '1.5px solid #fce7f3',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>🧁</span> {inventory.length} treats inside
            </span>
          </div>
        </div>
      </header>

      {/* Main Page Layout */}
      <main style={{ maxWidth: '1240px', margin: '28px auto', padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '26px' }}>
        {/* Cute Upload Banner */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '24px',
            padding: '24px 28px',
            border: '2px solid #fce7f3',
            boxShadow: '0 10px 25px rgba(244, 114, 182, 0.08)',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px'
          }}
        >
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#831843', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Snap Your Fridge Shelves</span> 📸✨
            </h2>
            <p style={{ fontSize: '14px', color: '#9d4c6d', margin: '4px 0 0' }}>
              Take a quick photo of your goodies and we'll remember when they expire so nothing goes bad!
            </p>
          </div>

          <label
            style={{
              backgroundColor: '#ec4899',
              color: '#ffffff',
              padding: '12px 24px',
              borderRadius: '20px',
              fontSize: '14px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 6px 16px rgba(236, 72, 153, 0.35)',
              transition: 'all 0.15s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#db2777')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#ec4899')}
          >
            <span>✨</span> Take / Upload Photo
            <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
          </label>
        </div>

        {/* 2-Column: Photo & Review */}
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 1fr)', gap: '24px', alignItems: 'stretch' }}>
          <div>
            <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '14px', fontWeight: '700', color: '#831843', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>🎀 Tap any item on the photo</span>
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

        {/* Cute Fridge Inventory */}
        <InventoryDashboard
          items={inventory}
          onRemoveItem={handleRemoveInventoryItem}
        />
      </main>
    </div>
  );
}
