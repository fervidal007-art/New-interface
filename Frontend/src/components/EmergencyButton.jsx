import { AlertOctagon } from 'lucide-react';
import { useState } from 'react';

function EmergencyButton({ onEmergencyStop }) {
  const [isPressed, setIsPressed] = useState(false);

  const handlePress = () => {
    setIsPressed(true);
    onEmergencyStop();
    
    // Resetear el botón después de 2 segundos
    setTimeout(() => {
      setIsPressed(false);
    }, 2000);
  };

  return (
    <button
      className={`emergency-button ${isPressed ? 'pressed' : ''}`}
      onClick={handlePress}
      disabled={isPressed}
      aria-label="Paro de emergencia"
    >
      <AlertOctagon size={32} />
      <span className="emergency-text">PARO</span>
    </button>
  );
}

export default EmergencyButton;

