import { INITIAL_DETECTIONS } from '../mockData';

// When false, the client reports errors if the backend is not available
let fallbackToMock = false;

export function setFallbackToMock(enable) {
  fallbackToMock = enable;
}

/**
 * Send an image file to the object detection endpoint.
 */
export async function detectFridgeItems(imageBlob, confidenceThreshold = 0.25) {
  try {
    const formData = new FormData();
    formData.append('file', imageBlob, 'fridge_scan.jpg');

    const queryParams = new URLSearchParams({
      confidence_threshold: confidenceThreshold.toString(),
    });

    // Send the request to the backend server through the local proxy
    const res = await fetch(`/api/detect?${queryParams}`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      let errMsg = `Detection failed with status: ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        else if (errJson && errJson.error) errMsg = errJson.error;
      } catch (_) { }
      throw new Error(errMsg);
    }
    const data = await res.json();
    // Return the detection array from the response object
    return data.detections || data;
  } catch (err) {
    if (fallbackToMock) {
      console.warn('[API Service] Backend /api/detect offline, using local mock detections.');
      await new Promise((r) => setTimeout(r, 600));
      return INITIAL_DETECTIONS;
    }
    throw err;
  }
}

/**
 * Send user corrections and verified items to the feedback endpoint.
 */
export async function sendFeedback(payload) {
  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Failed to record feedback');
    return await res.json();
  } catch (err) {
    // Record data locally if the backend server is not available
    console.log('[API Service] Feedback saved locally:', payload);
    return { status: 'logged_locally', payload };
  }
}

/**
 * Retrieve inventory items from the database or local storage.
 */
export async function getInventory() {
  try {
    const res = await fetch('/api/inventory');
    if (!res.ok) throw new Error('Failed to fetch inventory');
    return await res.json();
  } catch (err) {
    const saved = localStorage.getItem('fridge_inventory');
    return saved ? JSON.parse(saved) : null;
  }
}

/**
 * Save confirmed items to the database and update local storage.
 */
export async function saveInventory(items) {
  localStorage.setItem('fridge_inventory', JSON.stringify(items));
  try {
    const formattedItems = items.map((it) => ({
      food_class: it.label || it.food_class,
      custom_name: it.custom_name || (it.label ? it.label.replace(/_/g, ' ') : null),
      package_state: it.packageState || it.package_state || 'sealed',
      storage_location: it.storage_location || 'refrigerator',
      shelf_life_days: it.days || it.shelf_life_days || 7,
      verified: Boolean(it.verified || it.userEdited),
      confidence: it.confidence !== undefined ? it.confidence : 1.0,
      bbox: it.bbox || null,
      user_notes: it.user_notes || null
    }));

    const res = await fetch('/api/inventory/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: formattedItems })
    });
    if (!res.ok) throw new Error('Failed to save to backend');
    return await res.json();
  } catch (err) {
    console.log('[API Service] Saved to local browser storage.');
    return { status: 'saved_locally' };
  }
}

/**
 * Get shelf life in days from the food safety guidelines table.
 */
export function estimateShelfLife(itemClass, isOpened = false) {
  // Standard storage duration in days based on USDA guidelines
  const shelfLifeRules = {
    milk: { sealed: 7, opened: 4 },
    egg: { sealed: 21, opened: 14 },
    yogurt: { sealed: 14, opened: 7 },
    chicken: { sealed: 2, opened: 1 },
    beef: { sealed: 4, opened: 2 },
    bacon: { sealed: 14, opened: 7 },
    cheese: { sealed: 21, opened: 14 },
    goat_cheese: { sealed: 14, opened: 7 },
    butter: { sealed: 30, opened: 21 },
    cream: { sealed: 10, opened: 5 },
    apple: { sealed: 21, opened: 14 },
    banana: { sealed: 5, opened: 3 },
    strawberries: { sealed: 5, opened: 3 },
    blueberries: { sealed: 7, opened: 4 },
    orange: { sealed: 14, opened: 10 },
    lemon: { sealed: 21, opened: 14 },
    lime: { sealed: 21, opened: 14 },
    tomato: { sealed: 7, opened: 4 },
    bell_pepper: { sealed: 10, opened: 5 },
    carrot: { sealed: 21, opened: 14 },
    spinach: { sealed: 5, opened: 3 },
    mushrooms: { sealed: 5, opened: 3 },
    bread: { sealed: 7, opened: 5 },
    shrimp: { sealed: 2, opened: 1 },
    jar: { sealed: 30, opened: 14 }
  };

  const rule = shelfLifeRules[itemClass] || { sealed: 7, opened: 5 };
  return isOpened ? rule.opened : rule.sealed;
}

