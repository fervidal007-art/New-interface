import { useState, useRef, useEffect } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';

function Joystick({ type = "movement", onMove, icon: Icon, disabled = false }) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);

  const handleStart = (e) => {
    if (disabled) {
      return;
    }
    e.preventDefault();
    setIsDragging(true);
    handleMove(e);
  };

  const handleMove = (e) => {
    if (disabled) {
      return;
    }
    e.preventDefault();
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    // Get position from mouse or touch
    let clientX, clientY;
    if (e.type.includes('touch')) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    let x = clientX - rect.left - centerX;
    let y = clientY - rect.top - centerY;

    // Limit to circle
    const distance = Math.sqrt(x * x + y * y);
    const maxDistance = centerX - 30;

    if (distance > maxDistance) {
      x = (x / distance) * maxDistance;
      y = (y / distance) * maxDistance;
    }

    setPosition({ x, y });

    // Calculate normalized values (-1 to 1)
    const normalizedX = x / maxDistance;
    const normalizedY = -y / maxDistance; // Invert Y axis

    if (onMove) {
      onMove({ x: normalizedX, y: normalizedY });
    }
  };

  const handleEnd = () => {
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    if (onMove) {
      onMove({ x: 0, y: 0 });
    }
  };

  useEffect(() => {
    if (isDragging) {
      const moveHandler = (e) => handleMove(e);
      const endHandler = () => handleEnd();

      window.addEventListener('mousemove', moveHandler);
      window.addEventListener('mouseup', endHandler);
      window.addEventListener('touchmove', moveHandler, { passive: false });
      window.addEventListener('touchend', endHandler);

      return () => {
        window.removeEventListener('mousemove', moveHandler);
        window.removeEventListener('mouseup', endHandler);
        window.removeEventListener('touchmove', moveHandler);
        window.removeEventListener('touchend', endHandler);
      };
    }
  }, [isDragging]);

  useEffect(() => {
    if (disabled) {
      handleEnd();
    }
  }, [disabled]);

  return (
    <div className={`joystick-container ${disabled ? 'joystick-disabled' : ''}`}>
      <div 
        className={`joystick-outer ${disabled ? 'disabled' : ''}`} 
        ref={containerRef}
        onMouseDown={handleStart}
        onTouchStart={handleStart}
      >
        {/* Directional indicators */}
        <div className="joystick-directions">
          <ArrowUp className="dir-indicator up" size={20} />
          <ArrowDown className="dir-indicator down" size={20} />
          <ArrowLeft className="dir-indicator left" size={20} />
          <ArrowRight className="dir-indicator right" size={20} />
        </div>
        
        <div 
          className={`joystick-inner ${disabled ? 'disabled' : ''}`}
          style={{
            transform: `translate(${position.x}px, ${position.y}px)`
          }}
        >
          {Icon && <Icon size={28} />}
        </div>
      </div>
    </div>
  );
}

export default Joystick;
