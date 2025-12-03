import { useState } from 'react';
import { AlertOctagon } from 'lucide-react';

function EmergencyButton({ onEmergencyStop, emergencyStopActive, disabled }) {
  const [isPressed, setIsPressed] = useState(false);

  const handlePress = (e) => {
    if (disabled) return;
    // Solo prevenir default si no es un evento pasivo
    if (e.cancelable) {
      e.preventDefault();
    }
    e.stopPropagation();
    
    setIsPressed(true);
    // Ejecutar paro INMEDIATAMENTE sin ningún delay
    onEmergencyStop();
  };

  const handleRelease = (e) => {
    if (disabled) return;
    // Solo prevenir default si no es un evento pasivo
    if (e.cancelable) {
      e.preventDefault();
    }
    e.stopPropagation();
    setIsPressed(false);
  };

  return (
    <button
      className={`emergency-button ${emergencyStopActive ? 'active' : ''} ${isPressed ? 'pressed' : ''}`}
      onMouseDown={handlePress}
      onMouseUp={handleRelease}
      onMouseLeave={handleRelease}
      onTouchStart={handlePress}
      onTouchEnd={handleRelease}
      disabled={disabled}
      aria-label="Paro de emergencia"
      type="button"
    >
      <AlertOctagon size={24} />
      <span className="emergency-text">{emergencyStopActive ? 'ACTIVO' : 'PARO'}</span>
    </button>
  );
}

export default EmergencyButton;

