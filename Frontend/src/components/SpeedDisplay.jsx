function SpeedDisplay({ speed }) {
  const value = Number.isFinite(speed) ? speed : 0;
  const formattedSpeed = value.toFixed(2);

  return (
    <div className="speed-display">
      <div className="speed-value">{formattedSpeed}</div>
      <div className="speed-unit">m/s</div>
    </div>
  );
}

export default SpeedDisplay;
