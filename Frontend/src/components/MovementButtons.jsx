import { useState } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, ArrowUpLeft, ArrowUpRight, ArrowDownLeft, ArrowDownRight } from 'lucide-react';
import EmergencyButton from './EmergencyButton';

function MovementButtons({ onMove, disabled, onEmergencyStop, emergencyStopActive, activeMovement }) {
  const [pressedButton, setPressedButton] = useState(null);

  // Mapear el movimiento activo a la dirección del botón
  const getActiveButton = () => {
    if (!activeMovement) return null;
    
    const { x, y } = activeMovement;
    
    // Mapear coordenadas a dirección del botón
    if (x === 0 && y === 1) return 'up'; // adelante
    if (x === 0 && y === -1) return 'down'; // atras
    if (x === -1 && y === 0) return 'left'; // izquierda
    if (x === 1 && y === 0) return 'right'; // derecha
    if (Math.abs(x - (-0.707)) < 0.01 && Math.abs(y - 0.707) < 0.01) return 'up-left'; // diag_izq_arr
    if (Math.abs(x - 0.707) < 0.01 && Math.abs(y - 0.707) < 0.01) return 'up-right'; // diag_der_arr
    if (Math.abs(x - (-0.707)) < 0.01 && Math.abs(y - (-0.707)) < 0.01) return 'down-left'; // diag_izq_abj
    if (Math.abs(x - 0.707) < 0.01 && Math.abs(y - (-0.707)) < 0.01) return 'down-right'; // diag_der_abj
    
    return null;
  };

  const activeButton = getActiveButton() || pressedButton;

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    setPressedButton(direction);
    
    // Mapear dirección a nombre de acción
    let action = '';
    switch (direction) {
      case 'up':
        action = 'adelante';
        break;
      case 'down':
        action = 'atras';
        break;
      case 'left':
        action = 'izquierda';
        break;
      case 'right':
        action = 'derecha';
        break;
      case 'up-left':
        action = 'diag_izq_arr';
        break;
      case 'up-right':
        action = 'diag_der_arr';
        break;
      case 'down-left':
        action = 'diag_izq_abj';
        break;
      case 'down-right':
        action = 'diag_der_abj';
        break;
      default:
        return;
    }
    
    onMove(action);
  };

  const handleButtonRelease = () => {
    if (disabled) return;
    // NO resetear el botón presionado al soltar - mantener activo hasta presionar paro
    // El botón permanecerá activo visualmente basado en activeMovement
    // No llamar a onMove - mantener el último comando
  };

  return (
    <div className="movement-buttons">
      {/* Diagonal superior izquierda */}
      <button
        className={`movement-btn diagonal up-left ${activeButton === 'up-left' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('up-left')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('up-left')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Diagonal superior izquierda"
      >
        <ArrowUpLeft size={32} />
      </button>
      
      {/* Arriba */}
      <button
        className={`movement-btn up ${activeButton === 'up' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('up')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('up')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Arriba"
      >
        <ArrowUp size={36} />
      </button>
      
      {/* Diagonal superior derecha */}
      <button
        className={`movement-btn diagonal up-right ${activeButton === 'up-right' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('up-right')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('up-right')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Diagonal superior derecha"
      >
        <ArrowUpRight size={24} />
      </button>
      
      {/* Izquierda */}
      <button
        className={`movement-btn left ${activeButton === 'left' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('left')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('left')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Izquierda"
      >
        <ArrowLeft size={36} />
      </button>
      
      {/* Centro - Botón de paro */}
      <div className="movement-center">
        <EmergencyButton 
          onEmergencyStop={onEmergencyStop}
          emergencyStopActive={emergencyStopActive}
          disabled={disabled}
        />
      </div>
      
      {/* Derecha */}
      <button
        className={`movement-btn right ${activeButton === 'right' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('right')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('right')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Derecha"
      >
        <ArrowRight size={36} />
      </button>
      
      {/* Diagonal inferior izquierda */}
      <button
        className={`movement-btn diagonal down-left ${activeButton === 'down-left' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('down-left')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('down-left')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Diagonal inferior izquierda"
      >
        <ArrowDownLeft size={24} />
      </button>
      
      {/* Abajo */}
      <button
        className={`movement-btn down ${activeButton === 'down' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('down')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('down')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Abajo"
      >
        <ArrowDown size={36} />
      </button>
      
      {/* Diagonal inferior derecha */}
      <button
        className={`movement-btn diagonal down-right ${activeButton === 'down-right' ? 'pressed' : ''}`}
        onMouseDown={() => handleButtonPress('down-right')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('down-right')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
        aria-label="Diagonal inferior derecha"
      >
        <ArrowDownRight size={24} />
      </button>
    </div>
  );
}

export default MovementButtons;

