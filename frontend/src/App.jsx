import React, { useState } from 'react';
import BoundingBoxOverlay from './components/BoundingBoxOverlay';
import HumanInTheLoopReview from './components/HumanInTheLoopReview';
import InventoryDashboard from './components/InventoryDashboard';
import { MOCK_DETECTIONS } from './mockData';

// Placeholder stock fridge photo for initial testing
const SAMPLE_IMAGE = 'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1000&q=80';

export default function App() {
  const [imageSrc, setImageSrc] = useState(SAMPLE_IMAGE);
  const [detections, setDetections] = useState(MOCK_DETECTIONS);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [selectedId, setSelectedId] = useState(null);
  const [inventory, setInventory] = useState([
    { id: 'inv-1', label: 'yogurt', daysRemaining: 4, dateAdded: 'Nov 1, 2026' },
    { id: 'inv-2', label: 'bacon', daysRemaining: 1, dateAdded: 'Oct 30, 2026' }
  ]);

  // Handle local image upload
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setImageSrc(url);
      setSelectedId(null);
      // In production, Alice will call CJ's FastAPI endpoint: POST /detect
      // For now, reset detections to mock set to demonstrate interactive UI
      setDetections(MOCK_DETECTIONS.map(d => ({ ...d, status: 'pending' })));
    }
  };

  // Human-in-the-loop: Update detection label or status
  const handleUpdateDetection = (id, changes) => {
    setDetections((prev) =>
      prev.map((det) => (det.id === id ? { ...det, ...changes } : det))
    );

    // If accepted, also sync into digital inventory
    if (changes.status === 'accepted') {
      const det = detections.find(d => d.id === id);
      if (det && !inventory.some(item => item.id === `inv-${id}`)) {
        setInventory(prev => [
          ...prev,
          {
            id: `inv-${id}`,
            label: changes.label || det.label,
            daysRemaining: det.suggestedShelfLifeDays ?? 5,
            dateAdded: 'Today',
            userCorrected: changes.userCorrected || det.userCorrected
          }
        ]);
      }
    }
  };

  // Accept all valid items currently visible above the confidence threshold
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

    const newInventoryItems = visible.map((det) => ({
      id: `inv-${det.id}`,
      label: det.label,
      daysRemaining: det.suggestedShelfLifeDays ?? 5,
      dateAdded: 'Today',
      userCorrected: det.userCorrected
    }));

    setInventory((prev) => {
      const existingIds = new Set(prev.map(item => item.id));
      const filtered = newInventoryItems.filter(item => !existingIds.has(item.id));
      return [...prev, ...filtered];
    });
  };

  const handleRemoveInventoryItem = (id) => {
    setInventory((prev) => prev.filter((item) => item.id !== id));
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f1f5f9', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Top Navbar */}
      <header style={{ backgroundColor: '#0f172a', color: '#ffffff', padding: '16px 32px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: '700', letterSpacing: '-0.5px' }}>
              FreshTrack AI
            </h1>
            <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#94a3b8' }}>
              CSCI 270: Computer Vision & USDA FoodKeeper Expiration Predictor
            </p>
          </div>
          <div style={{ fontSize: '13px', backgroundColor: '#1e293b', padding: '6px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <span>Branch: <code>alice/frontend-setup</code></span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '24px auto', padding: '0 24px' }}>
        {/* Upload Control */}
        <div style={{ backgroundColor: '#ffffff', padding: '16px 20px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#1e293b' }}>
              Fridge Photo Scanner
            </h2>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
              Upload or snap a fridge photo to run YOLO object detection and USDA FoodKeeper matching.
            </p>
          </div>
          <label
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              padding: '8px 16px',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Upload Photo
            <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
          </label>
        </div>

        {/* 2-Column Layout: Visual Detection Canvas & Interactive Review */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', marginBottom: '24px' }}>
          <div>
            <h3 style={{ margin: '0 0 12px', fontSize: '15px', fontWeight: '600', color: '#334155' }}>
              Detection Canvas & Bounding Box Overlays
            </h3>
            <BoundingBoxOverlay
              imageUrl={imageSrc}
              detections={detections}
              confidenceThreshold={confidenceThreshold}
              selectedId={selectedId}
              onSelectDetection={setSelectedId}
            />
          </div>

          <div>
            <h3 style={{ margin: '0 0 12px', fontSize: '15px', fontWeight: '600', color: '#334155' }}>
              Human-in-the-Loop Review & Feedback
            </h3>
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

        {/* Inventory Section */}
        <div>
          <InventoryDashboard
            items={inventory}
            onRemoveItem={handleRemoveInventoryItem}
          />
        </div>
      </main>
    </div>
  );
}
