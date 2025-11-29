import { useState } from 'react';
import { RotateCcw, RotateCw } from 'lucide-react';

function RotationButtons({ onRotate, disabled }) {
  const [pressedButton, setPressedButton] = useState(null);

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    setPressedButton(direction);
    
    const rotation = direction === 'left' ? -1 : 1;
    onRotate({ x: rotation, y: 0 });
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
        <RotateCcw size={32} />
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
        <RotateCw size={32} />
        <span>Derecha</span>
      </button>
    </div>
  );
}

export default RotationButtons;

