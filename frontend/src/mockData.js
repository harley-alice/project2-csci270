/**
 * 38 Food Classes mapped by Carter Blanton from dataset cleaning
 * Reference: project2_work_allocation.md
 */
export const FOOD_CLASSES = [
  'apple', 'avocado', 'bacon', 'banana', 'beef', 'bell_pepper',
  'blueberries', 'bread', 'butter', 'carrot', 'cheese', 'chicken',
  'chocolate', 'corn', 'cream', 'egg', 'flour', 'goat_cheese',
  'green_beans', 'ham', 'jar', 'lemon', 'lime', 'mango',
  'milk', 'mushrooms', 'onion', 'orange', 'persimmon', 'pomegranate',
  'potato', 'shrimp', 'spinach', 'strawberries', 'sugar', 'sweet_potato',
  'tomato', 'yogurt'
];

/**
 * Fallback / mock detection samples for development and offline testing
 * before CJ's FastAPI YOLO inference endpoint is fully hooked up.
 */
export const MOCK_DETECTIONS = [
  {
    id: 'det-1',
    label: 'milk',
    confidence: 0.94,
    // [ymin, xmin, ymax, xmax] normalized 0-1
    bbox: [0.25, 0.15, 0.72, 0.38],
    suggestedShelfLifeDays: 7,
    status: 'pending' // 'pending' | 'accepted' | 'rejected' | 'modified'
  },
  {
    id: 'det-2',
    label: 'apple',
    confidence: 0.88,
    bbox: [0.45, 0.42, 0.65, 0.58],
    suggestedShelfLifeDays: 21,
    status: 'pending'
  },
  {
    id: 'det-3',
    label: 'chicken',
    confidence: 0.62,
    bbox: [0.60, 0.65, 0.88, 0.92],
    suggestedShelfLifeDays: 2,
    status: 'pending'
  },
  {
    id: 'det-4',
    label: 'jar',
    confidence: 0.49,
    bbox: [0.12, 0.68, 0.38, 0.84],
    suggestedShelfLifeDays: null,
    status: 'pending',
    isContainerNote: true
  }
];
