export const FOOD_CLASSES = [
  'apple', 'avocado', 'bacon', 'banana', 'beef', 'bell_pepper',
  'blueberries', 'bread', 'butter', 'carrot', 'cheese', 'chicken',
  'chocolate', 'corn', 'cream', 'egg', 'flour', 'goat_cheese',
  'green_beans', 'ham', 'jar', 'lemon', 'lime', 'mango',
  'milk', 'mushrooms', 'onion', 'orange', 'persimmon', 'pomegranate',
  'potato', 'shrimp', 'spinach', 'strawberries', 'sugar', 'sweet_potato',
  'tomato', 'yogurt'
];

export const FOOD_METADATA = {
  apple: { name: 'Fresh Apples', emoji: '🍎', defaultDays: 21, category: 'Produce' },
  avocado: { name: 'Avocado', emoji: '🥑', defaultDays: 4, category: 'Produce' },
  bacon: { name: 'Bacon', emoji: '🥓', defaultDays: 7, category: 'Meat & Protein' },
  banana: { name: 'Bananas', emoji: '🍌', defaultDays: 5, category: 'Produce' },
  beef: { name: 'Fresh Beef', emoji: '🥩', defaultDays: 3, category: 'Meat & Protein' },
  bell_pepper: { name: 'Bell Pepper', emoji: '🫑', defaultDays: 10, category: 'Produce' },
  blueberries: { name: 'Blueberries', emoji: '🫐', defaultDays: 6, category: 'Produce' },
  bread: { name: 'Bread', emoji: '🍞', defaultDays: 7, category: 'Bakery' },
  butter: { name: 'Butter', emoji: '🧈', defaultDays: 45, category: 'Dairy' },
  carrot: { name: 'Carrots', emoji: '🥕', defaultDays: 25, category: 'Produce' },
  cheese: { name: 'Cheese', emoji: '🧀', defaultDays: 21, category: 'Dairy' },
  chicken: { name: 'Raw Chicken', emoji: '🍗', defaultDays: 2, category: 'Meat & Protein', highRisk: true },
  chocolate: { name: 'Chocolate', emoji: '🍫', defaultDays: 60, category: 'Pantry' },
  corn: { name: 'Sweet Corn', emoji: '🌽', defaultDays: 3, category: 'Produce' },
  cream: { name: 'Heavy Cream', emoji: '🥛', defaultDays: 10, category: 'Dairy' },
  egg: { name: 'Eggs', emoji: '🥚', defaultDays: 28, category: 'Dairy' },
  flour: { name: 'Flour', emoji: '🌾', defaultDays: 180, category: 'Pantry' },
  goat_cheese: { name: 'Goat Cheese', emoji: '🧀', defaultDays: 10, category: 'Dairy' },
  green_beans: { name: 'Green Beans', emoji: '🫘', defaultDays: 6, category: 'Produce' },
  ham: { name: 'Sliced Ham', emoji: '🍖', defaultDays: 5, category: 'Meat & Protein' },
  jar: { name: 'Unopened / Glass Jar', emoji: '🫙', defaultDays: 14, category: 'Pantry', needsClarification: true },
  lemon: { name: 'Lemons', emoji: '🍋', defaultDays: 21, category: 'Produce' },
  lime: { name: 'Limes', emoji: '🍈', defaultDays: 21, category: 'Produce' },
  mango: { name: 'Mango', emoji: '🥭', defaultDays: 6, category: 'Produce' },
  milk: { name: 'Fresh Milk', emoji: '🥛', defaultDays: 7, category: 'Dairy' },
  mushrooms: { name: 'Mushrooms', emoji: '🍄', defaultDays: 5, category: 'Produce' },
  onion: { name: 'Yellow / Red Onions', emoji: '🧅', defaultDays: 30, category: 'Produce' },
  orange: { name: 'Oranges', emoji: '🍊', defaultDays: 20, category: 'Produce' },
  persimmon: { name: 'Persimmon', emoji: '🍑', defaultDays: 8, category: 'Produce' },
  pomegranate: { name: 'Pomegranate', emoji: '🫐', defaultDays: 21, category: 'Produce' },
  potato: { name: 'Potatoes', emoji: '🥔', defaultDays: 30, category: 'Produce' },
  shrimp: { name: 'Fresh Shrimp', emoji: '🦐', defaultDays: 2, category: 'Meat & Protein', highRisk: true },
  spinach: { name: 'Fresh Spinach', emoji: '🥬', defaultDays: 5, category: 'Produce' },
  strawberries: { name: 'Strawberries', emoji: '🍓', defaultDays: 4, category: 'Produce' },
  sugar: { name: 'Sugar', emoji: '🧂', defaultDays: 365, category: 'Pantry' },
  sweet_potato: { name: 'Sweet Potato', emoji: '🍠', defaultDays: 25, category: 'Produce' },
  tomato: { name: 'Tomatoes', emoji: '🍅', defaultDays: 7, category: 'Produce' },
  yogurt: { name: 'Yogurt', emoji: '🥣', defaultDays: 14, category: 'Dairy' }
};

export const MOCK_DETECTIONS = [
  {
    id: 'det-1',
    label: 'milk',
    confidence: 0.94,
    bbox: [0.22, 0.14, 0.76, 0.40],
    status: 'pending'
  },
  {
    id: 'det-2',
    label: 'apple',
    confidence: 0.88,
    bbox: [0.45, 0.42, 0.65, 0.58],
    status: 'pending'
  },
  {
    id: 'det-3',
    label: 'chicken',
    confidence: 0.62,
    bbox: [0.58, 0.62, 0.90, 0.94],
    status: 'pending'
  },
  {
    id: 'det-4',
    label: 'jar',
    confidence: 0.49,
    bbox: [0.12, 0.68, 0.38, 0.84],
    status: 'pending'
  }
];
