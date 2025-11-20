import { Car } from 'lucide-react';

const GRID_SIZE = 420;
const MARGIN = 30;

function CarVisualization({ position, path }) {
  const center = GRID_SIZE / 2;
  const hasMovement = path.length > 1 || Math.abs(position.x) > 1 || Math.abs(position.y) > 1;

  const maxDist = path.reduce(
    (acc, point) => Math.max(acc, Math.abs(point.x - position.x), Math.abs(point.y - position.y)),
    1
  );

  const rawScale = (center - MARGIN) / (maxDist || 1);
  const scale = hasMovement ? Math.min(Math.max(rawScale, 0.05), 6) : 1;

  const cellSize = 50 * scale;
  const mod = (value, modulo) => ((value % modulo) + modulo) % modulo;

  const toCanvasPoint = (point) => ({
    x: center + (point.x - position.x) * scale,
    y: center + (point.y - position.y) * scale,
  });

  const gridOffsetX = mod(-position.x * scale, cellSize);
  const gridOffsetY = mod(-position.y * scale, cellSize);

  const trailPoints = path
    .map(toCanvasPoint)
    .map((p) => `${p.x},${p.y}`)
    .join(' ');

  return (
    <div className="car-visualization">
      <div
        className="grid-background"
        style={{
          backgroundPosition: `${gridOffsetX}px ${gridOffsetY}px`,
          backgroundSize: `${cellSize}px ${cellSize}px`,
        }}
      />

      <svg
        className="car-trail"
        width={GRID_SIZE}
        height={GRID_SIZE}
        viewBox={`0 0 ${GRID_SIZE} ${GRID_SIZE}`}
      >
        {path.length > 1 && (
          <polyline
            points={trailPoints}
            fill="none"
            stroke="rgba(59,130,246,0.9)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
      </svg>

      <div
        className="car-marker"
      >
        <Car size={70} strokeWidth={1.4} />
        <span className="origin-dot" />
      </div>

      <div className="origin-label">Origen</div>
      <div className="scale-indicator">x{scale.toFixed(2)}</div>
    </div>
  );
}

export default CarVisualization;
