import React from 'react';

/**
 * CSCI 270 - Project 2: Food Expiration Predictor
 * Frontend Lead: Alice Harley
 * 
 * BoundingBoxOverlay Component
 * ==============================================================================
 * Renders the fridge photo with an SVG overlay displaying YOLO bounding boxes,
 * class labels, confidence percentages, and visual certainty indicators.
 * Also supports interactive click-and-drag drawing for human-in-the-loop
 * active learning (capturing false negatives to feed back into model training).
 * ==============================================================================
 */
export default function BoundingBoxOverlay({
  image,
  visibleItems,
  isDrawingMode,
  currentBox,
  imageContainerRef,
  imgElementRef,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  formatLabel = (l) => l
}) {
  return (
    <div style={{ textAlign: 'center', marginBottom: '24px' }}>
      {/* 1. Main image container with relative positioning for SVG coordinate alignment */}
      <div
        ref={imageContainerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{
          display: 'inline-block',
          position: 'relative',
          lineHeight: 0,
          border: isDrawingMode ? '2px solid var(--color-primary-accent, #0052cc)' : '1px solid var(--color-border, #e0e0e0)',
          background: '#000000',
          cursor: isDrawingMode ? 'crosshair' : 'default',
          userSelect: 'none',
          maxWidth: '100%',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
        }}
      >
        {/* Underneath image preview */}
        <img
          ref={imgElementRef}
          src={image}
          alt="Scanned fridge interior preview"
          draggable={false}
          style={{
            display: 'block',
            maxWidth: '100%',
            maxHeight: '520px',
            width: 'auto',
            height: 'auto',
            pointerEvents: 'none'
          }}
        />

        {/* 2. Scaled SVG overlay using normalized 0-1000 coordinate space */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible'
          }}
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {visibleItems.map((it) => {
            // Skip items added manually without bounding box coordinates
            if (!it.bbox || !Array.isArray(it.bbox) || it.bbox.length < 4) return null;
            
            // YOLO normalized coordinates: [ymin, xmin, ymax, xmax] in [0, 1] range
            const [ymin, xmin, ymax, xmax] = it.bbox;
            const conf = it.confidence ?? 1.0;
            const isUnsure = conf < 0.60;

            // Visual signifiers for user trust:
            // - Gold/Amber: User-edited or manually annotated items
            // - Orange/Red: Low confidence (< 60%) needing human verification
            // - Blue: High confidence detections
            const strokeColor = it.userEdited
              ? 'var(--color-accent, #faad14)'
              : isUnsure
              ? 'var(--color-attention, #d4380d)'
              : 'var(--color-primary-accent, #1890ff)';

            // Scale normalized [0, 1] coordinates into the 1000x1000 viewBox
            const x = xmin * 1000;
            const y = ymin * 1000;
            const w = Math.max(4, (xmax - xmin) * 1000);
            const h = Math.max(4, (ymax - ymin) * 1000);
            const labelText = `${formatLabel(it.label)} (${Math.round(conf * 100)}%)`;
            const badgeWidth = Math.max(70, labelText.length * 8.5 + 16);

            return (
              <g key={it.id}>
                {/* Detection bounding box with subtle translucent fill */}
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={isUnsure ? 'rgba(212, 56, 13, 0.12)' : 'rgba(24, 144, 255, 0.12)'}
                  stroke={strokeColor}
                  strokeWidth="3"
                />
                {/* Badge header for readable class name and confidence score */}
                <rect
                  x={x}
                  y={Math.max(0, y - 22)}
                  width={badgeWidth}
                  height="22"
                  fill={strokeColor}
                />
                {/* Text tag */}
                <text
                  x={x + 6}
                  y={Math.max(16, y - 6)}
                  fill={it.userEdited ? '#000000' : '#ffffff'}
                  fontSize="12"
                  fontWeight="bold"
                  fontFamily="system-ui, -apple-system, sans-serif"
                >
                  {labelText}
                </text>
              </g>
            );
          })}

          {/* 3. In-progress dashed preview box while user clicks and drags */}
          {isDrawingMode && currentBox && (
            <rect
              x={currentBox.xmin * 1000}
              y={currentBox.ymin * 1000}
              width={(currentBox.xmax - currentBox.xmin) * 1000}
              height={(currentBox.ymax - currentBox.ymin) * 1000}
              fill="rgba(250, 173, 20, 0.25)"
              stroke="var(--color-accent, #faad14)"
              strokeWidth="3"
              strokeDasharray="6,4"
            />
          )}
        </svg>
      </div>
    </div>
  );
}
