function SpeedDisplay({ speed }) {
  // Formatear para que siempre muestre 2 dígitos
  const formattedSpeed = String(speed).padStart(2, '0');
  
  return (
    <div className="speed-display">
      <div className="speed-value">{formattedSpeed}</div>
      <div className="speed-unit">KM/H</div>
    </div>
  );
}

export default SpeedDisplay;

