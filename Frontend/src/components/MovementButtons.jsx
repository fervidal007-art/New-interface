import { useState } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';
import EmergencyButton from './EmergencyButton';

function MovementButtons({ onMove, disabled, onEmergencyStop }) {
  const [pressedButton, setPressedButton] = useState(null);

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    setPressedButton(direction);
    
    let x = 0;
    let y = 0;
    
    switch (direction) {
      case 'up':
        y = 1;
        break;
      case 'down':
        y = -1;
        break;
      case 'left':
        x = -1;
        break;
      case 'right':
        x = 1;
        break;
      default:
        break;
    }
    
    onMove({ x, y });
  };

  const handleButtonRelease = () => {
    if (disabled) return;
    // NO enviar comando de stop al soltar - mantener el último comando activo
    // Solo el botón de paro puede detener el movimiento
    setPressedButton(null);
    // No llamar a onMove - mantener el último comando
  };

  return (
    <div className="movement-buttons">
      <button
        className={`movement-btn up ${pressedButton === 'up' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('up')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('up')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Arriba"
      >
        <ArrowUp size={28} />
      </button>
      
      <button
        className={`movement-btn left ${pressedButton === 'left' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('left')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('left')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Izquierda"
      >
        <ArrowLeft size={28} />
      </button>
      
      <div className="movement-center">
        <EmergencyButton onEmergencyStop={onEmergencyStop} />
      </div>
      
      <button
        className={`movement-btn right ${pressedButton === 'right' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('right')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('right')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Derecha"
      >
        <ArrowRight size={28} />
      </button>
      
      <button
        className={`movement-btn down ${pressedButton === 'down' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('down')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('down')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Abajo"
      >
        <ArrowDown size={28} />
      </button>
    </div>
  );
}

export default MovementButtons;

