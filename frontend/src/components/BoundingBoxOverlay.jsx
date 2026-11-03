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
        backgroundColor: '#0f172a',
        borderRadius: '16px',
        overflow: 'hidden',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <img
        src={imageUrl}
        alt="Fridge Interior"
        style={{
          display: 'block',
          width: '100%',
          maxHeight: '520px',
          objectFit: 'contain',
          userSelect: 'none'
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
          const meta = FOOD_METADATA[det.label] || { name: det.label, emoji: '🥗' };
          const isWarning = det.label === 'jar' || det.confidence < 0.60;

          // Norman Affordance Colors: warm amber for items needing user check, calm emerald for good, vibrant indigo for selected
          const strokeColor = isSelected ? '#3b82f6' : isWarning ? '#f59e0b' : '#10b981';
          const badgeBg = isSelected ? '#2563eb' : isWarning ? '#d97706' : '#059669';

          const labelText = `${meta.emoji} ${meta.name}`;
          const badgeWidth = Math.max(110, labelText.length * 9.5 + 40);

          return (
            <g
              key={det.id}
              style={{ pointerEvents: 'all', cursor: 'pointer' }}
              onClick={() => onSelectDetection(det.id)}
            >
              {/* Highlight background on hover/selection */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={isSelected ? 'rgba(59, 130, 246, 0.22)' : 'rgba(0, 0, 0, 0.08)'}
                stroke={strokeColor}
                strokeWidth={isSelected ? 4 : 2.5}
                strokeDasharray={isWarning ? '6,4' : 'none'}
                rx="6"
              />

              {/* Pill badge */}
              <rect
                x={x}
                y={Math.max(4, y - 30)}
                width={badgeWidth}
                height={30}
                fill={badgeBg}
                rx="6"
                filter="drop-shadow(0px 2px 4px rgba(0,0,0,0.25))"
              />

              {/* Item text */}
              <text
                x={x + 10}
                y={Math.max(4, y - 30) + 20}
                fill="#ffffff"
                fontSize="14"
                fontWeight="700"
                fontFamily="'Plus Jakarta Sans', sans-serif"
              >
                {labelText}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
