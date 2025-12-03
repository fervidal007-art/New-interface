import { useState } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, ArrowUpLeft, ArrowUpRight, ArrowDownLeft, ArrowDownRight } from 'lucide-react';
import EmergencyButton from './EmergencyButton';

function MovementButtons({ onMove, disabled, onEmergencyStop, emergencyStopActive, activeMovement }) {
  // Mapear el movimiento activo a la dirección del botón
  const getActiveButton = () => {
    if (!activeMovement) return null;
    
    // activeMovement es el nombre de la acción (ej: 'adelante', 'izquierda', etc.)
    const actionToDirection = {
      'adelante': 'up',
      'atras': 'down',
      'izquierda': 'left',
      'derecha': 'right',
      'diag_izq_arr': 'up-left',
      'diag_der_arr': 'up-right',
      'diag_izq_abj': 'down-left',
      'diag_der_abj': 'down-right'
    };
    
    return actionToDirection[activeMovement] || null;
  };

  const activeButton = getActiveButton();

  const handleButtonPress = (direction) => {
    if (disabled) return;
    
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
    
    // Solo enviar si no es el mismo botón ya activo
    if (activeMovement !== action) {
      onMove(action);
    }
  };

  const handleButtonRelease = () => {
    // No hacer nada al soltar - el botón permanece activo hasta presionar stop
    // El estado se mantiene basado en activeMovement
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

