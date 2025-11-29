import { AlertOctagon } from 'lucide-react';
import { useState } from 'react';

function EmergencyButton({ onEmergencyStop }) {
  const [isPressed, setIsPressed] = useState(false);

  const handlePress = () => {
    // No bloquear si ya está presionado - permitir múltiples pulsaciones
    setIsPressed(true);
    
    // Ejecutar paro INMEDIATAMENTE
    onEmergencyStop();
    
    // Resetear el botón después de 1 segundo (feedback visual)
    setTimeout(() => {
      setIsPressed(false);
    }, 1000);
  };

  return (
    <button
      className={`emergency-button ${isPressed ? 'pressed' : ''}`}
      onClick={handlePress}
      aria-label="Paro de emergencia"
    >
      <AlertOctagon size={32} />
      <span className="emergency-text">PARO</span>
    </button>
  );
}

export default EmergencyButton;

