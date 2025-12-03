import { RotateCcw, RotateCw } from 'lucide-react';

function RotationButtons({ onRotate, disabled, activeRotation }) {
  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    // Mapear dirección a nombre de acción
    const action = direction === 'left' ? 'giro_izq' : 'giro_der';
    
    // Solo enviar si no es el mismo botón ya activo
    if (activeRotation !== action) {
      onRotate(action);
    }
  };

  const handleButtonRelease = () => {
    // No hacer nada al soltar - el botón permanece activo hasta presionar stop
    // El estado se mantiene basado en activeRotation
  };

  return (
    <div className="rotation-buttons">
      <button
        className={`rotation-btn left ${activeRotation === 'giro_izq' ? 'pressed' : ''}`}
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
        className={`rotation-btn right ${activeRotation === 'giro_der' ? 'pressed' : ''}`}
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

