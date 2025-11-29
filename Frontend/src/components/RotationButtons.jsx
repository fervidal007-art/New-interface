import { RotateCcw, RotateCw } from 'lucide-react';

function RotationButtons({ onRotate, disabled }) {
  const handleButtonPress = (direction) => {
    if (disabled) return;
    
    const rotation = direction === 'left' ? -1 : 1;
    onRotate({ x: rotation, y: 0 });
  };

  const handleButtonRelease = () => {
    if (disabled) return;
    onRotate({ x: 0, y: 0 });
  };

  return (
    <div className="rotation-buttons">
      <button
        className="rotation-btn left"
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
        className="rotation-btn right"
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

