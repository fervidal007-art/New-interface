import { useState } from 'react';
import { RotateCcw, RotateCw } from 'lucide-react';

function RotationButtons({ onRotate, disabled }) {
  const [pressedButton, setPressedButton] = useState(null);

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    setPressedButton(direction);
    
    // Mapear dirección a nombre de acción
    const action = direction === 'left' ? 'giro_izq' : 'giro_der';
    onRotate(action);
  };

  const handleButtonRelease = () => {
    if (disabled) return;
    // NO enviar comando de stop al soltar - mantener el último comando activo
    // Solo el botón de paro puede detener la rotación
    setPressedButton(null);
    // No llamar a onRotate - mantener el último comando
  };

  return (
    <div className="rotation-buttons">
      <button
        className={`rotation-btn left ${pressedButton === 'left' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('left')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('left')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
      >
        <RotateCcw size={40} />
        <span>Izquierda</span>
      </button>
      
      <button
        className={`rotation-btn right ${pressedButton === 'right' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('right')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('right')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
      >
        <RotateCw size={40} />
        <span>Derecha</span>
      </button>
    </div>
  );
}

export default RotationButtons;

