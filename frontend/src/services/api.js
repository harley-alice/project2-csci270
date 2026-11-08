import { INITIAL_DETECTIONS } from '../mockData';

// When false, throws error instead of silently returning mock detections so failures are visible
let fallbackToMock = false;

export function setFallbackToMock(enable) {
  fallbackToMock = enable;
}

/**
 * Upload an image (File or Blob) to YOLO detection endpoint
 */
export async function detectFridgeItems(imageBlob) {
  try {
    const formData = new FormData();
    formData.append('file', imageBlob, 'fridge_scan.jpg');

    const res = await fetch('/detect', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      let errMsg = `Detection failed with status: ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.error) errMsg = errJson.error;
      } catch (_) {}
      throw new Error(errMsg);
    }
    const data = await res.json();
    return data;
  } catch (err) {
    if (fallbackToMock) {
      console.warn('[API Service] Backend /detect offline, using local mock detections.');
      await new Promise((r) => setTimeout(r, 600));
      return INITIAL_DETECTIONS;
    }
    throw err;
  }
}

/**
 * Send human-in-the-loop correction / false positive payload
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
    // Silently fall back to local logging if server isn't up yet
    console.log('[API Service] Feedback saved locally:', payload);
    return { status: 'logged_locally', payload };
  }
}

/**
 * Fetch user inventory from SQLite backend (or localStorage if offline)
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
 * Save confirmed items to backend SQLite (and backup to local storage)
 */
export async function saveInventory(items) {
  localStorage.setItem('fridge_inventory', JSON.stringify(items));
  try {
    const res = await fetch('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items })
    });
    if (!res.ok) throw new Error('Failed to save to backend');
    return await res.json();
  } catch (err) {
    console.log('[API Service] Saved to local browser storage.');
    return { status: 'saved_locally' };
  }
}

/**
 * Calculate dynamic shelf life from USDA FoodKeeper guidelines
 */
export function estimateShelfLife(itemClass, isOpened = false) {
  // Baseline storage lookup (days) based on USDA FoodKeeper guidelines
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

