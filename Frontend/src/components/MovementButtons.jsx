import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';

function MovementButtons({ onMove, disabled }) {
  const handleButtonPress = (direction) => {
    if (disabled) return;
    
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
    onMove({ x: 0, y: 0 });
  };

  return (
    <div className="movement-buttons">
      <button
        className="movement-btn up"
        onMouseDown={() => handleButtonPress('up')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('up')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
      >
        <ArrowUp size={32} />
      </button>
      
      <div className="movement-row">
        <button
          className="movement-btn left"
          onMouseDown={() => handleButtonPress('left')}
          onMouseUp={handleButtonRelease}
          onMouseLeave={handleButtonRelease}
          onTouchStart={() => handleButtonPress('left')}
          onTouchEnd={handleButtonRelease}
          disabled={disabled}
        >
          <ArrowLeft size={32} />
        </button>
        
        <button
          className="movement-btn right"
          onMouseDown={() => handleButtonPress('right')}
          onMouseUp={handleButtonRelease}
          onMouseLeave={handleButtonRelease}
          onTouchStart={() => handleButtonPress('right')}
          onTouchEnd={handleButtonRelease}
          disabled={disabled}
        >
          <ArrowRight size={32} />
        </button>
      </div>
      
      <button
        className="movement-btn down"
        onMouseDown={() => handleButtonPress('down')}
        onMouseUp={handleButtonRelease}
        onMouseLeave={handleButtonRelease}
        onTouchStart={() => handleButtonPress('down')}
        onTouchEnd={handleButtonRelease}
        disabled={disabled}
      >
        <ArrowDown size={32} />
      </button>
    </div>
  );
}

export default MovementButtons;

