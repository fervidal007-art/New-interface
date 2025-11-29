import { useState } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';
import EmergencyButton from './EmergencyButton';

function MovementButtons({ onMove, disabled, onEmergencyStop, emergencyStopActive }) {
  const [pressedButton, setPressedButton] = useState(null);

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    setPressedButton(direction);
    
    let x = 0;
    let y = 0;
    
    switch (direction) {
      case 'up':
        // Arriba = Avanzar (movimiento hacia adelante en Y)
        y = 1;
        x = 0;
        break;
      case 'down':
        // Abajo = Retroceder (movimiento hacia atrás en Y)
        y = -1;
        x = 0;
        break;
      case 'left':
        // Izquierda = Movimiento lateral izquierdo (movimiento en X negativo)
        x = -1;
        y = 0;
        break;
      case 'right':
        // Derecha = Movimiento lateral derecho (movimiento en X positivo)
        x = 1;
        y = 0;
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
        <EmergencyButton 
          onEmergencyStop={onEmergencyStop}
          emergencyStopActive={emergencyStopActive}
        />
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

