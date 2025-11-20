const ROW_LETTERS = Object.freeze(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']);

export const BOARD_SETTINGS = Object.freeze({
  tiles: 12,
  squareSize: 0.5, // metros por cuadrante
  rowLetters: ROW_LETTERS,
  epsilon: 1e-6,
});

export const BOARD_HALF_SPAN = (BOARD_SETTINGS.tiles * BOARD_SETTINGS.squareSize) / 2;

export function worldToQuadrant(x, y, settings = BOARD_SETTINGS) {
  const { tiles, squareSize, rowLetters, epsilon } = settings;
  const half = (tiles * squareSize) / 2;

  const columnIdx = Math.floor(((x + half) - epsilon) / squareSize);
  const rowIdx = Math.floor(((y + half) - epsilon) / squareSize);

  if (
    columnIdx < 0 ||
    columnIdx >= tiles ||
    rowIdx < 0 ||
    rowIdx >= tiles ||
    Number.isNaN(columnIdx) ||
    Number.isNaN(rowIdx)
  ) {
    return null;
  }

  const column = columnIdx + 1;
  const rowLetter = rowLetters[rowIdx] || '';
  const centerX = -half + (columnIdx + 0.5) * squareSize;
  const centerY = -half + (rowIdx + 0.5) * squareSize;

  return {
    label: `${rowLetter}${column}`,
    column,
    columnIdx,
    rowLetter,
    rowIndex: rowIdx + 1, // 1-based desde la parte inferior
    rowIdx,
    center: { x: centerX, y: centerY },
  };
}
