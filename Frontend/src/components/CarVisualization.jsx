import { useMemo, useRef } from 'react';
import { Car } from 'lucide-react';
import { BOARD_SETTINGS } from '../utils/board';

const GRID_SIZE = 520;
const MARGIN = 36;

function CarVisualization({
  position,
  path,
  boardSettings = BOARD_SETTINGS,
  currentQuadrant,
  targetQuadrant,
  onQuadrantSelect,
}) {
  const containerRef = useRef(null);
  const { tiles, squareSize, rowLetters } = boardSettings;
  const boardMeters = tiles * squareSize;
  const boardPixels = GRID_SIZE - MARGIN * 2;
  const pxPerMeter = boardPixels / boardMeters;
  const squarePx = squareSize * pxPerMeter;
  const boardOffset = MARGIN;
  const halfSpan = (tiles * squareSize) / 2;

  const headingDeg = Number.isFinite(position.theta) ? position.theta * (180 / Math.PI) : 0;
  const clipId = useMemo(() => `trail-mask-${Math.random().toString(36).slice(2, 8)}`, []);

  const toCanvasPoint = (point) => ({
    x: boardOffset + (point.x + halfSpan) * pxPerMeter,
    y: boardOffset + (halfSpan - point.y) * pxPerMeter,
  });

  const trailPoints = path
    .map(toCanvasPoint)
    .map((p) => `${p.x},${p.y}`)
    .join(' ');

  const highlightStyle = (quadrant) => {
    if (!quadrant) return null;
    const rowIdx = quadrant.rowIdx ?? quadrant.rowIndex - 1;
    const columnIdx = quadrant.columnIdx ?? quadrant.column - 1;
    if (rowIdx == null || columnIdx == null) return null;
    const displayRow = tiles - (rowIdx + 1);
    return {
      left: boardOffset + columnIdx * squarePx,
      top: boardOffset + displayRow * squarePx,
      width: squarePx,
      height: squarePx,
    };
  };

  const rowLabelData = useMemo(() => {
    return rowLetters.slice(0, tiles).map((letter, bottomIdx) => {
      const displayRow = tiles - bottomIdx - 1;
      return {
        letter,
        y: boardOffset + displayRow * squarePx + squarePx / 2,
      };
    });
  }, [rowLetters, tiles, boardOffset, squarePx]);

  const columnLabelData = useMemo(() => {
    return Array.from({ length: tiles }).map((_, idx) => ({
      number: idx + 1,
      x: boardOffset + idx * squarePx + squarePx / 2,
    }));
  }, [tiles, boardOffset, squarePx]);

  const handleBoardClick = (event) => {
    if (!onQuadrantSelect || !containerRef.current) {
      return;
    }
    const rect = containerRef.current.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;

    if (
      offsetX < boardOffset ||
      offsetX > boardOffset + boardPixels ||
      offsetY < boardOffset ||
      offsetY > boardOffset + boardPixels
    ) {
      return;
    }

    const localX = offsetX - boardOffset;
    const localY = offsetY - boardOffset;
    const worldX = localX / pxPerMeter - halfSpan;
    const worldY = halfSpan - localY / pxPerMeter;

    if (worldX < -halfSpan || worldX > halfSpan || worldY < -halfSpan || worldY > halfSpan) {
      return;
    }

    const columnIdx = Math.floor(((worldX + halfSpan) - 1e-6) / squareSize);
    const rowIdx = Math.floor(((worldY + halfSpan) - 1e-6) / squareSize);

    if (
      columnIdx < 0 ||
      columnIdx >= tiles ||
      rowIdx < 0 ||
      rowIdx >= tiles
    ) {
      return;
    }

    const label = `${rowLetters[rowIdx] || ''}${columnIdx + 1}`;
    const centerX = -halfSpan + (columnIdx + 0.5) * squareSize;
    const centerY = -halfSpan + (rowIdx + 0.5) * squareSize;
    onQuadrantSelect({
      label,
      column: columnIdx + 1,
      columnIdx,
      rowIdx,
      rowIndex: rowIdx + 1,
      rowLetter: rowLetters[rowIdx],
      center: { x: centerX, y: centerY },
    });
  };

  const targetStyle = highlightStyle(targetQuadrant);
  const currentStyle = highlightStyle(currentQuadrant);

  return (
    <div className="car-visualization" ref={containerRef} onClick={handleBoardClick}>
      <div className="grid-background chess" />

      <svg className="board-svg" width={GRID_SIZE} height={GRID_SIZE}>
        {Array.from({ length: tiles }).map((_, row) =>
          Array.from({ length: tiles }).map((__, col) => {
            const x = boardOffset + col * squarePx;
            const y = boardOffset + row * squarePx;
            const dark = (row + col) % 2 === 0;
            return (
              <rect
                key={`${row}-${col}`}
                x={x}
                y={y}
                width={squarePx}
                height={squarePx}
                fill={dark ? 'rgba(15,23,42,0.75)' : 'rgba(30,41,59,0.82)'}
                stroke="rgba(56,189,248,0.08)"
                strokeWidth="1"
              />
            );
          })
        )}
      </svg>

      {targetStyle && <div className="quadrant-highlight target" style={targetStyle} />}
      {currentStyle && <div className="quadrant-highlight current" style={currentStyle} />}

      <svg className="car-trail" width={GRID_SIZE} height={GRID_SIZE}>
        <defs>
          <clipPath id={clipId}>
            <rect
              x={boardOffset}
              y={boardOffset}
              width={boardPixels}
              height={boardPixels}
            />
          </clipPath>
        </defs>
        {path.length > 1 && (
          <polyline
            points={trailPoints}
            fill="none"
            stroke="rgba(59,130,246,0.9)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            clipPath={`url(#${clipId})`}
          />
        )}
      </svg>

      <div
        className="car-marker"
        style={{
          top: `${boardOffset + (halfSpan - position.y) * pxPerMeter}px`,
          left: `${boardOffset + (position.x + halfSpan) * pxPerMeter}px`,
          transform: `translate(-50%, -50%) rotate(${headingDeg}deg)`,
        }}
      >
        <Car size={70} strokeWidth={1.4} />
      </div>

      <div
        className="origin-point"
        style={{
          top: `${boardOffset + (boardPixels / 2)}px`,
          left: `${boardOffset + (boardPixels / 2)}px`,
        }}
      >
        <span />
      </div>

      {rowLabelData.map((row) => (
        <div key={`row-left-${row.letter}`} className="row-label left" style={{ top: `${row.y}px` }}>
          {row.letter}
        </div>
      ))}
      {rowLabelData.map((row) => (
        <div key={`row-right-${row.letter}`} className="row-label right" style={{ top: `${row.y}px` }}>
          {row.letter}
        </div>
      ))}
      {columnLabelData.map((col) => (
        <div key={`col-top-${col.number}`} className="col-label top" style={{ left: `${col.x}px` }}>
          {col.number}
        </div>
      ))}
      {columnLabelData.map((col) => (
        <div
          key={`col-bottom-${col.number}`}
          className="col-label bottom"
          style={{ left: `${col.x}px` }}
        >
          {col.number}
        </div>
      ))}

      <div className="origin-label">Origen</div>
      <div className="scale-indicator">1 cuadrado = {squareSize} m</div>
    </div>
  );
}

export default CarVisualization;
