import { useState, useRef, useEffect } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';

function Joystick({ type = "movement", onMove, icon: Icon }) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);
  const onMoveRef = useRef(onMove);
  
  // Mantener onMove actualizado en el ref
  useEffect(() => {
    onMoveRef.current = onMove;
  }, [onMove]);

  const handleStart = (e) => {
    e.preventDefault();
    setIsDragging(true);
    handleMove(e);
  };

  const handleMove = (e) => {
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

  const handleEnd = (e) => {
    if (e) {
      e.preventDefault();
    }
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    if (onMove) {
      // Enviar múltiples veces para asegurar que se reciba
      onMove({ x: 0, y: 0 });
      setTimeout(() => onMove({ x: 0, y: 0 }), 10);
      setTimeout(() => onMove({ x: 0, y: 0 }), 50);
    }
  };

  useEffect(() => {
    if (isDragging) {
      const moveHandler = (e) => handleMove(e);
      const endHandler = (e) => handleEnd(e);

      window.addEventListener('mousemove', moveHandler);
      window.addEventListener('mouseup', endHandler);
      window.addEventListener('mouseleave', endHandler); // Detectar cuando el mouse sale de la ventana
      window.addEventListener('touchmove', moveHandler, { passive: false });
      window.addEventListener('touchend', endHandler);
      window.addEventListener('touchcancel', endHandler); // Detectar cancelación de touch

      return () => {
        window.removeEventListener('mousemove', moveHandler);
        window.removeEventListener('mouseup', endHandler);
        window.removeEventListener('mouseleave', endHandler);
        window.removeEventListener('touchmove', moveHandler);
        window.removeEventListener('touchend', endHandler);
        window.removeEventListener('touchcancel', endHandler);
        // Asegurar reset al desmontar
        setPosition({ x: 0, y: 0 });
        if (onMoveRef.current) {
          onMoveRef.current({ x: 0, y: 0 });
        }
      };
    }
  }, [isDragging]);

  // Efecto separado para asegurar que el joystick vuelva al centro cuando no está arrastrando
  useEffect(() => {
    if (!isDragging && (position.x !== 0 || position.y !== 0)) {
      setPosition({ x: 0, y: 0 });
      if (onMoveRef.current) {
        onMoveRef.current({ x: 0, y: 0 });
      }
    }
  }, [isDragging, position]);

  return (
    <div className="joystick-container">
      <div 
        className="joystick-outer" 
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
          className="joystick-inner"
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

