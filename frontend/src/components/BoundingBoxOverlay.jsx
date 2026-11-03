import React from 'react';
import { FOOD_METADATA } from '../mockData';

export default function BoundingBoxOverlay({
  imageUrl,
  detections,
  confidenceThreshold,
  selectedId,
  onSelectDetection
}) {
  const visibleDetections = detections.filter(
    (d) => d.confidence >= confidenceThreshold && d.status !== 'rejected'
  );

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        backgroundColor: '#fce7f3',
        borderRadius: '24px',
        overflow: 'hidden',
        boxShadow: '0 12px 30px rgba(244, 114, 182, 0.18)',
        border: '3px solid #fbcfe8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <img
        src={imageUrl}
        alt="Fridge contents"
        style={{
          display: 'block',
          width: '100%',
          maxHeight: '480px',
          objectFit: 'contain',
          userSelect: 'none',
          borderRadius: '20px'
        }}
      />

      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none'
        }}
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
      >
        {visibleDetections.map((det) => {
          const [ymin, xmin, ymax, xmax] = det.bbox;
          const x = xmin * 1000;
          const y = ymin * 1000;
          const width = (xmax - xmin) * 1000;
          const height = (ymax - ymin) * 1000;

          const isSelected = selectedId === det.id;
          const meta = FOOD_METADATA[det.label] || { name: det.label, emoji: '🍓' };
          const isWarning = det.label === 'jar' || det.confidence < 0.60;

          // Cutesy pastel palette:
          // Selected = lavender purple, Warning = pastel apricot/peach, Normal = bubblegum pink/rose
          const strokeColor = isSelected ? '#a855f7' : isWarning ? '#fb923c' : '#ec4899';
          const badgeBg = isSelected ? '#9333ea' : isWarning ? '#f97316' : '#ec4899';

          const labelText = `${meta.emoji} ${meta.name}`;
          const badgeWidth = Math.max(120, labelText.length * 9.5 + 40);

          return (
            <g
              key={det.id}
              style={{ pointerEvents: 'all', cursor: 'pointer' }}
              onClick={() => onSelectDetection(det.id)}
            >
              {/* Cute glow outline */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={isSelected ? 'rgba(168, 85, 247, 0.22)' : 'rgba(236, 72, 153, 0.08)'}
                stroke={strokeColor}
                strokeWidth={isSelected ? 4 : 3}
                strokeDasharray={isWarning ? '8,5' : 'none'}
                rx="14"
              />

              {/* Cute rounded tag */}
              <rect
                x={x}
                y={Math.max(6, y - 32)}
                width={badgeWidth}
                height={30}
                fill={badgeBg}
                rx="15"
                filter="drop-shadow(0 4px 8px rgba(236, 72, 153, 0.3))"
              />

              {/* Tag text */}
              <text
                x={x + 12}
                y={Math.max(6, y - 32) + 20}
                fill="#ffffff"
                fontSize="13"
                fontWeight="700"
                fontFamily="'Fredoka', 'Outfit', sans-serif"
              >
                {labelText} ✨
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
