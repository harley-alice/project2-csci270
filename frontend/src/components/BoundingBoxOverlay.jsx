import React, { useRef, useEffect } from 'react';

/**
 * BoundingBoxOverlay
 * Renders an image along with YOLO bounding boxes, class labels, and confidence tags.
 * Handles responsive scaling between natural image dimensions and display dimensions.
 */
export default function BoundingBoxOverlay({
  imageUrl,
  detections,
  confidenceThreshold,
  selectedId,
  onSelectDetection
}) {
  const containerRef = useRef(null);
  const imgRef = useRef(null);

  // Filter based on active confidence slider
  const visibleDetections = detections.filter(
    (d) => d.confidence >= confidenceThreshold && d.status !== 'rejected'
  );

  return (
    <div 
      ref={containerRef} 
      style={{
        position: 'relative',
        display: 'inline-block',
        maxWidth: '100%',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        backgroundColor: '#1e293b'
      }}
    >
      <img
        ref={imgRef}
        src={imageUrl}
        alt="Fridge Capture"
        style={{
          display: 'block',
          width: '100%',
          maxHeight: '520px',
          objectFit: 'contain'
        }}
      />

      {/* SVG overlay for drawing YOLO bounding boxes */}
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
          // Scale to 0-1000 coordinate space
          const x = xmin * 1000;
          const y = ymin * 1000;
          const width = (xmax - xmin) * 1000;
          const height = (ymax - ymin) * 1000;

          const isSelected = selectedId === det.id;
          const isLowConf = det.confidence < 0.60;
          const isJar = det.label.toLowerCase() === 'jar';

          // Color scheme:
          // Amber for low confidence or jar needing attention, green for high confidence, blue for selected
          let strokeColor = isLowConf || isJar ? '#f59e0b' : '#10b981';
          if (isSelected) strokeColor = '#3b82f6';

          return (
            <g 
              key={det.id}
              style={{ pointerEvents: 'all', cursor: 'pointer' }}
              onClick={() => onSelectDetection(det.id)}
            >
              {/* Bounding rectangle */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={isSelected ? 'rgba(59, 130, 246, 0.15)' : 'rgba(0, 0, 0, 0.05)'}
                stroke={strokeColor}
                strokeWidth={isSelected ? 4 : 2.5}
                strokeDasharray={isLowConf ? '6,3' : 'none'}
                rx="4"
              />

              {/* Tag / Badge background */}
              <rect
                x={x}
                y={Math.max(0, y - 26)}
                width={Math.max(80, (det.label.length * 9) + 55)}
                height={26}
                fill={strokeColor}
                rx="3"
              />

              {/* Tag text */}
              <text
                x={x + 6}
                y={Math.max(0, y - 26) + 18}
                fill="#ffffff"
                fontSize="14"
                fontWeight="600"
                fontFamily="sans-serif"
              >
                {det.label} {Math.round(det.confidence * 100)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
