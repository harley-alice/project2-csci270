import React, { useState, useRef, useEffect, useCallback } from 'react';
import heic2any from 'heic2any';
import {
  detectFridgeItems,
  getStorageRules,
  calculateRule,
  sendFeedback,
  getInventory,
  saveInventory,
  deleteInventoryItem
} from './services/api';
import CaptureSection from './components/CaptureSection';
import ReviewSection from './components/ReviewSection';
import InventorySection from './components/InventorySection';
import {
  getTodayDateStr,
  addDaysToDate,
  calculateDaysRemaining
} from './utils/dateUtils';

// Default sample fridge image for initial preview
const SAMPLE_IMAGE =
  'https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=1200&q=80';

/**
 * Main Application Component for Fridge Tracker.
 * Manages the multi-step food expiration workflow:
 * Step 1: Capture or upload fridge photo.
 * Step 2: Review detected food items, choose date opened or conservative "unsure" mode.
 * Step 3: Loading transition while saving to database.
 * Step 4: Digital fridge inventory ordered by expiration date.
 */
export default function App() {
  // Current screen step: 1 = Capture, 2 = Review, 3 = Saving, 4 = Inventory
  const [step, setStep] = useState(1);
  const [image, setImage] = useState(SAMPLE_IMAGE);

  // Detection and loading states
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionError, setDetectionError] = useState(null);
  const [rawDetections, setRawDetections] = useState([]);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.20);

  // Dynamic food classes and rules fetched from Ashton's USDA FoodKeeper database
  const [foodClasses, setFoodClasses] = useState([]);
  const [rulesCache, setRulesCache] = useState([]);

  // Final inventory list and sort order preference
  const [tracking, setTracking] = useState([]);
  const [trackingSortBy, setTrackingSortBy] = useState('expire_soonest');

  // Camera video stream references
  const [isCameraActive, setIsCameraActive] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Manual box drawing state for missed items
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [drawingStart, setDrawingStart] = useState(null);
  const [currentBox, setCurrentBox] = useState(null);
  const imageContainerRef = useRef(null);
  const imgElementRef = useRef(null);

  // 1. Initial Setup: Load FoodKeeper storage rules and existing fridge inventory
  useEffect(() => {
    async function initializeAppData() {
      // Fetch USDA FoodKeeper rules catalog
      try {
        const rules = await getStorageRules();
        if (Array.isArray(rules) && rules.length > 0) {
          setRulesCache(rules);
          const distinctClasses = Array.from(new Set(rules.map((r) => r.food_class))).sort();
          setFoodClasses(distinctClasses);
        }
      } catch (err) {
        console.warn('Could not load FoodKeeper rules from backend:', err);
      }

      // Fetch existing fridge inventory from the database
      try {
        const items = await getInventory();
        if (Array.isArray(items) && items.length > 0) {
          const today = getTodayDateStr();
          setTracking(
            items.map((it) => {
              const daysRemaining =
                it.days_remaining !== undefined
                  ? it.days_remaining
                  : it.shelf_life_days || it.days || 7;
              const expiry = it.expiration_date || addDaysToDate(today, daysRemaining);
              return {
                id: it.id || String(Date.now() + Math.random()),
                label: it.food_class || it.label,
                packageState: it.package_state || it.packageState || 'sealed',
                days: daysRemaining,
                openedDate: it.opened_date || it.openedDate || '',
                addedDate: it.added_date || it.addedDate || today,
                expirationDate: expiry,
                isUnsureOpened: Boolean(it.is_unsure_opened || it.isUnsureOpened)
              };
            })
          );
        }
      } catch (err) {
        console.warn('Could not load existing inventory from backend:', err);
      }
    }

    initializeAppData();

    // Clean up camera on unmount
    return () => {
      stopCamera();
    };
  }, []);

  // Helper: Find shelf life rule for a food item from Ashton's FoodKeeper cache
  const lookupRule = useCallback(
    (foodClass, packageState = 'sealed', isUnsure = false) => {
      const normClass = String(foodClass || '').trim().toLowerCase();
      const normPkg = String(packageState || '').trim().toLowerCase();

      // Find matching rule from Ashton's database
      const match =
        rulesCache.find(
          (r) =>
            r.food_class === normClass &&
            r.package_state === normPkg &&
            r.storage_location === 'refrigerator'
        ) ||
        rulesCache.find(
          (r) => r.food_class === normClass && r.storage_location === 'refrigerator'
        ) ||
        rulesCache.find((r) => r.food_class === normClass);

      if (match) {
        // If user is unsure, return the conservative minimum shelf life
        const conservativeDays = match.shelf_life_days_min || 1;
        const recommendedDays = match.recommended_shelf_life_days || match.shelf_life_days_max || 7;
        return {
          days: isUnsure ? conservativeDays : recommendedDays,
          conservativeDays,
          recommendedDays,
          usdaGuidance: match.usda_guidance || null
        };
      }

      // Conservative fallback if not yet in cache
      return {
        days: isUnsure ? 2 : 5,
        conservativeDays: 2,
        recommendedDays: 5,
        usdaGuidance: null
      };
    },
    [rulesCache]
  );

  // 2. Camera Operations
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
      alert('Camera access could not be started. Check browser permissions or use file upload.');
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

  // Helper to enrich raw detection items with FoodKeeper rules
  const enrichDetections = (items) => {
    const today = getTodayDateStr();
    return items.map((it) => {
      const pkg = it.packageState || 'sealed';
      const rule = lookupRule(it.label, pkg, false);
      const initialDays = it.days || rule.days;
      return {
        ...it,
        packageState: pkg,
        openedDate: '',
        isUnsureOpened: false,
        days: initialDays,
        previewExpiry: addDaysToDate(today, initialDays),
        usdaGuidance: rule.usdaGuidance
      };
    });
  };

  // Capture video frame from camera
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

    canvas.toBlob(async (blob) => {
      try {
        const results = await detectFridgeItems(blob, confidenceThreshold);
        setRawDetections(enrichDetections(results));
      } catch (err) {
        console.error('Detection failed:', err);
        setDetectionError(err.message || 'Detection failed. Ensure the YOLO server is running on port 8000.');
      } finally {
        setIsDetecting(false);
      }
    }, 'image/jpeg');
  };

  // Handle uploaded file (converts HEIC format if needed)
  const handleFile = async (e) => {
    let file = e.target.files[0];
    if (file) {
      stopCamera();
      setRawDetections([]);
      setDetectionError(null);
      setIsDetecting(true);
      setStep(2);

      try {
        const lowerName = file.name.toLowerCase();
        const isHeic =
          file.type === 'image/heic' ||
          file.type === 'image/heif' ||
          lowerName.endsWith('.heic') ||
          lowerName.endsWith('.heif');

        if (isHeic) {
          try {
            const convertedBlob = await heic2any({
              blob: file,
              toType: 'image/jpeg',
              quality: 0.85
            });
            const singleBlob = Array.isArray(convertedBlob) ? convertedBlob[0] : convertedBlob;
            file = new File([singleBlob], file.name.replace(/\.(heic|heif)$/i, '.jpg'), {
              type: 'image/jpeg'
            });
          } catch (heicErr) {
            console.warn('HEIC conversion warning:', heicErr);
          }
        }

        setImage(URL.createObjectURL(file));

        const results = await detectFridgeItems(file, confidenceThreshold);
        setRawDetections(enrichDetections(results));
      } catch (err) {
        console.error('Detection failed:', err);
        setDetectionError(err.message || 'Detection failed. Ensure the YOLO server is running on port 8000.');
      } finally {
        setIsDetecting(false);
      }
    }
  };

  // 3. User Verification & Rule Updates
  const updateLabel = async (id, newLabel) => {
    const targetItem = rawDetections.find((it) => it.id === id);
    if (!targetItem || targetItem.label === newLabel) return;

    // Send active learning correction to backend
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

    const rule = lookupRule(newLabel, targetItem.packageState, targetItem.isUnsureOpened);
    const today = getTodayDateStr();

    setRawDetections((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        const days = rule.days;
        const previewExpiry =
          it.packageState === 'opened' && it.openedDate && !it.isUnsureOpened
            ? addDaysToDate(it.openedDate, days)
            : addDaysToDate(today, days);

        return {
          ...it,
          label: newLabel,
          userEdited: true,
          days,
          previewExpiry,
          usdaGuidance: rule.usdaGuidance
        };
      })
    );
  };

  // Toggle package condition between sealed and opened
  const togglePackageState = (id, newState) => {
    const today = getTodayDateStr();

    setRawDetections((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        let openedDate = it.openedDate;
        let isUnsure = it.isUnsureOpened;

        if (newState === 'opened') {
          if (!openedDate) openedDate = today;
        } else {
          isUnsure = false;
          openedDate = '';
        }

        const rule = lookupRule(it.label, newState, isUnsure);
        const days = rule.days;
        const previewExpiry =
          newState === 'opened' && openedDate && !isUnsure
            ? addDaysToDate(openedDate, days)
            : addDaysToDate(today, days);

        return {
          ...it,
          packageState: newState,
          openedDate,
          isUnsureOpened: isUnsure,
          days,
          previewExpiry,
          usdaGuidance: rule.usdaGuidance,
          userEditedDays: false
        };
      })
    );
  };

  // Update date opened from date picker
  const updateOpenedDate = (id, newDate) => {
    setRawDetections((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        const rule = lookupRule(it.label, 'opened', false);
        const previewExpiry = addDaysToDate(newDate, it.days || rule.days);

        return {
          ...it,
          openedDate: newDate,
          isUnsureOpened: false, // user provided exact date
          previewExpiry
        };
      })
    );
  };

  // Toggle unsure button to apply Ashton's conservative minimum shelf life
  const toggleUnsureOpened = (id) => {
    const today = getTodayDateStr();

    setRawDetections((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        const nextUnsure = !it.isUnsureOpened;
        const rule = lookupRule(it.label, 'opened', nextUnsure);
        const days = rule.days;
        const previewExpiry = addDaysToDate(today, days);

        return {
          ...it,
          isUnsureOpened: nextUnsure,
          days,
          previewExpiry,
          userEditedDays: false
        };
      })
    );
  };

  // Manually update remaining shelf life days in review
  const updateDays = (id, newDays) => {
    const parsed = Math.max(1, parseInt(newDays, 10) || 1);
    const today = getTodayDateStr();

    setRawDetections((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        const previewExpiry =
          it.packageState === 'opened' && it.openedDate && !it.isUnsureOpened
            ? addDaysToDate(it.openedDate, parsed)
            : addDaysToDate(today, parsed);

        return {
          ...it,
          days: parsed,
          userEditedDays: true,
          previewExpiry
        };
      })
    );
  };

  // Update shelf life days for an item in inventory view
  const updateTrackingDays = (id, newDays) => {
    const parsed = Math.max(0, parseInt(newDays, 10) || 0);
    const today = getTodayDateStr();

    setTracking((prev) =>
      prev.map((it) => {
        if (it.id !== id) return it;
        return {
          ...it,
          days: parsed,
          expirationDate: addDaysToDate(today, parsed)
        };
      })
    );
  };

  // Remove an item from the review list
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

  // Add missed item (optionally with drawn bounding box)
  const addMissedItem = (customBbox = null) => {
    const defaultLabel = foodClasses[0] || 'apple';
    const rule = lookupRule(defaultLabel, 'sealed', false);
    const today = getTodayDateStr();

    const newItem = {
      id: String(Date.now()),
      label: defaultLabel,
      confidence: 1.0,
      packageState: 'sealed',
      days: rule.days,
      openedDate: '',
      isUnsureOpened: false,
      previewExpiry: addDaysToDate(today, rule.days),
      usdaGuidance: rule.usdaGuidance,
      bbox: customBbox,
      userEdited: true,
      manuallyAdded: true
    };

    sendFeedback({
      timestamp: new Date().toISOString(),
      type: customBbox ? 'missed_item_added_with_box' : 'missed_item_added_manually',
      image_source: image.startsWith('data:') ? 'camera' : 'upload',
      detection_id: newItem.id,
      predicted_label: null,
      corrected_label: defaultLabel,
      confidence: 1.0,
      bbox: newItem.bbox
    });

    setRawDetections((prev) => [...prev, newItem]);
  };

  // 4. Interactive Box Drawing
  const getRelativeCoords = (e) => {
    const rect =
      imgElementRef.current?.getBoundingClientRect() ||
      imageContainerRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
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

    if (width > 0.02 && height > 0.02) {
      addMissedItem([currentBox.ymin, currentBox.xmin, currentBox.ymax, currentBox.xmax]);
      setIsDrawingMode(false);
    }

    setDrawingStart(null);
    setCurrentBox(null);
  };

  // Filter items based on user sensitivity threshold or user-confirmed status
  const visibleItems = rawDetections.filter(
    (it) => it.userEdited || (it.confidence ?? 1.0) >= confidenceThreshold
  );

  // 5. Confirm items and save to fridge inventory database
  const confirmAndTrack = async () => {
    setStep(3);
    const today = getTodayDateStr();

    const newItems = visibleItems.map((it) => {
      let effectiveRemainingDays = parseInt(it.days, 10) || 7;
      let calculatedExpirationDate = addDaysToDate(today, effectiveRemainingDays);

      // If opened and openedDate provided, calculate exact expiration and remaining days
      if (it.packageState === 'opened' && it.openedDate && !it.isUnsureOpened) {
        const expiryFromOpened = addDaysToDate(it.openedDate, it.days);
        if (expiryFromOpened) {
          calculatedExpirationDate = expiryFromOpened;
          effectiveRemainingDays = Math.max(0, calculateDaysRemaining(calculatedExpirationDate));
        }
      }

      return {
        id: String(Date.now() + Math.random()),
        label: it.label,
        food_class: it.label,
        packageState: it.packageState || 'sealed',
        package_state: it.packageState || 'sealed',
        openedDate: it.packageState === 'opened' ? it.openedDate || today : '',
        addedDate: today,
        expirationDate: calculatedExpirationDate,
        expiration_date: calculatedExpirationDate,
        isUnsureOpened: Boolean(it.isUnsureOpened),
        days: effectiveRemainingDays,
        shelf_life_days: effectiveRemainingDays,
        verified: Boolean(it.userEdited),
        confidence: it.confidence,
        bbox: it.bbox
      };
    });

    try {
      await saveInventory(newItems);
    } catch (err) {
      console.warn('Failed saving items to backend batch inventory:', err);
    }

    setTracking((prev) => [...prev, ...newItems]);
    setStep(4);
  };

  // Remove tracked item from inventory
  const removeTracked = async (id) => {
    try {
      await deleteInventoryItem(id);
    } catch (err) {
      console.warn('Could not delete from backend inventory:', err);
    }
    setTracking((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div style={{ maxWidth: '720px', margin: '48px auto', padding: '0 24px' }}>
      <header
        style={{
          borderBottom: '2px solid var(--color-border)',
          paddingBottom: '16px',
          marginBottom: '32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline'
        }}
      >
        <h1 style={{ fontSize: '24px', fontWeight: 700, letterSpacing: '-0.5px' }}>
          Fridge Tracker
        </h1>
        <span style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
          USDA FoodKeeper & Computer Vision
        </span>
      </header>

      {/* Step 1: Capture / Upload */}
      {step === 1 && (
        <CaptureSection
          isCameraActive={isCameraActive}
          videoRef={videoRef}
          startCamera={startCamera}
          stopCamera={stopCamera}
          capturePhoto={capturePhoto}
          handleFile={handleFile}
        />
      )}

      {/* Step 2: Review Scanned Items */}
      {step === 2 && (
        <ReviewSection
          image={image}
          visibleItems={visibleItems}
          rawDetections={rawDetections}
          confidenceThreshold={confidenceThreshold}
          setConfidenceThreshold={setConfidenceThreshold}
          foodClasses={foodClasses}
          isDetecting={isDetecting}
          detectionError={detectionError}
          setDetectionError={setDetectionError}
          isDrawingMode={isDrawingMode}
          setIsDrawingMode={setIsDrawingMode}
          currentBox={currentBox}
          setCurrentBox={setCurrentBox}
          setDrawingStart={setDrawingStart}
          imageContainerRef={imageContainerRef}
          imgElementRef={imgElementRef}
          handleMouseDown={handleMouseDown}
          handleMouseMove={handleMouseMove}
          handleMouseUp={handleMouseUp}
          updateLabel={updateLabel}
          togglePackageState={togglePackageState}
          updateOpenedDate={updateOpenedDate}
          toggleUnsureOpened={toggleUnsureOpened}
          updateDays={updateDays}
          removeItem={removeItem}
          confirmAndTrack={confirmAndTrack}
          onBack={() => {
            stopCamera();
            setStep(1);
          }}
        />
      )}

      {/* Step 3: Saving transition */}
      {step === 3 && (
        <section aria-live="assertive" style={{ textAlign: 'center', padding: '80px 0' }}>
          <p style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>
            Updating fridge inventory...
          </p>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
            Applying USDA FoodKeeper guidelines.
          </p>
        </section>
      )}

      {/* Step 4: Digital Fridge Inventory */}
      {step === 4 && (
        <InventorySection
          tracking={tracking}
          trackingSortBy={trackingSortBy}
          setTrackingSortBy={setTrackingSortBy}
          updateTrackingDays={updateTrackingDays}
          removeTracked={removeTracked}
          onScanMore={() => setStep(1)}
        />
      )}
    </div>
  );
}
