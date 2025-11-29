import { AlertOctagon } from 'lucide-react';

function EmergencyButton({ onEmergencyStop, emergencyStopActive }) {
  const handlePress = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Ejecutar paro INMEDIATAMENTE sin ningún delay
    onEmergencyStop();
  };

  return (
    <button
      className={`emergency-button ${emergencyStopActive ? 'active' : ''}`}
      onClick={handlePress}
      onMouseDown={handlePress}
      onTouchStart={handlePress}
      aria-label="Paro de emergencia"
      type="button"
    >
      <AlertOctagon size={32} />
      <span className="emergency-text">{emergencyStopActive ? 'ACTIVO' : 'PARO'}</span>
    </button>
  );
}

export default EmergencyButton;

