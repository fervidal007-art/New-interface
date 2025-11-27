import { useState, useRef, useEffect } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';

// Zona muerta: valores menores a esto se consideran 0
const DEADZONE = 0.15;
// Throttle: tiempo mínimo entre envíos de comandos (ms) - aumentado para evitar saturación
const THROTTLE_MS = 100;
// Umbral mínimo de cambio para enviar (evita enviar valores idénticos)
const CHANGE_THRESHOLD = 0.01;

function Joystick({ type = "movement", onMove, icon: Icon }) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);
  const lastSendTime = useRef(0);
  const lastSentValues = useRef({ x: 0, y: 0 });

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
    let normalizedX = x / maxDistance;
    let normalizedY = -y / maxDistance; // Invert Y axis

    // Aplicar zona muerta: si el valor absoluto es menor al deadzone, ponerlo en 0
    if (Math.abs(normalizedX) < DEADZONE) normalizedX = 0;
    if (Math.abs(normalizedY) < DEADZONE) normalizedY = 0;

    // Deduplicación: solo enviar si el valor cambió significativamente
    const xChanged = Math.abs(normalizedX - lastSentValues.current.x) > CHANGE_THRESHOLD;
    const yChanged = Math.abs(normalizedY - lastSentValues.current.y) > CHANGE_THRESHOLD;
    
    // Throttling: solo enviar si ha pasado suficiente tiempo Y el valor cambió
    const now = Date.now();
    if (onMove && (now - lastSendTime.current) >= THROTTLE_MS && (xChanged || yChanged)) {
      lastSendTime.current = now;
      lastSentValues.current = { x: normalizedX, y: normalizedY };
      onMove({ x: normalizedX, y: normalizedY });
    }
  };

  const handleEnd = () => {
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    // Siempre enviar 0 cuando se suelta, sin throttle (pero solo si no estaba ya en 0)
    if (onMove && (lastSentValues.current.x !== 0 || lastSentValues.current.y !== 0)) {
      lastSendTime.current = Date.now();
      lastSentValues.current = { x: 0, y: 0 };
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

