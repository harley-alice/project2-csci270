import { INITIAL_DETECTIONS } from '../mockData';

// Toggle this to false when CJ's FastAPI server is running
const USE_MOCK = true;
const API_BASE_URL = 'http://localhost:8000';

/**
 * Upload an image/blob to YOLO detection endpoint
 */
export async function detectFridgeItems(imageBlob) {
  if (USE_MOCK) {
    // Simulate server latency
    await new Promise((r) => setTimeout(r, 600));
    return INITIAL_DETECTIONS;
  }

  const formData = new FormData();
  formData.append('file', imageBlob);

  const res = await fetch(`${API_BASE_URL}/detect`, {
    method: 'POST',
    body: formData
  });

  if (!res.ok) throw new Error('Detection failed');
  return res.json();
}

/**
 * Send human-in-the-loop correction / false positive payload
 */
export async function sendFeedback(payload) {
  if (USE_MOCK) {
    console.log('[API Service] Feedback logged locally:', payload);
    return { status: 'logged', id: payload.detection_id };
  }

  const res = await fetch(`${API_BASE_URL}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok) throw new Error('Failed to record feedback');
  return res.json();
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

