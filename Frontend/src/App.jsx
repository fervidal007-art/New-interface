import { useState, useEffect } from 'react';
import { Move, RotateCw } from 'lucide-react';
import Header from './components/Header';
import SpeedDisplay from './components/SpeedDisplay';
import Joystick from './components/Joystick';
import CarVisualization from './components/CarVisualization';
import ControlPanel from './components/ControlPanel';
import Stats from './components/Stats';
import socketService from './utils/socket';

function App() {
  const [speed, setSpeed] = useState(0);
  const [direction, setDirection] = useState(45);
  const [gpsCoords, setGpsCoords] = useState({ lat: 41.40338, lng: 2.17403 });
  const [batteryLevel, setBatteryLevel] = useState(55);
  const [mode, setMode] = useState('manual');
  const [movementInput, setMovementInput] = useState({ x: 0, y: 0 });
  const [rotationInput, setRotationInput] = useState({ x: 0, y: 0 });
  const [isConnected, setIsConnected] = useState(false);

  // Initialize Socket.IO connection
  useEffect(() => {
    socketService.connect();
    
    socketService.on('connect', () => {
      setIsConnected(true);
      console.log('✅ Conectado al servidor');
    });

    socketService.on('disconnect', () => {
      setIsConnected(false);
      console.log('❌ Desconectado del servidor');
    });

    socketService.on('command', (data) => {
      console.log('Comando recibido:', data);
      // Aquí puedes manejar comandos del servidor
    });

    return () => {
      socketService.disconnect();
    };
  }, []);

  // Send telemetry periodically
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      socketService.sendTelemetry({
        speed,
        direction,
        gps: gpsCoords,
        battery: batteryLevel,
        mode,
        timestamp: Date.now()
      });
    }, 1000); // Send every second

    return () => clearInterval(interval);
  }, [isConnected, speed, direction, gpsCoords, batteryLevel, mode]);


  // Simulate speed based on movement input
  useEffect(() => {
    const magnitude = Math.sqrt(movementInput.x ** 2 + movementInput.y ** 2);
    const maxSpeed = 82;
    setSpeed(Math.round(magnitude * maxSpeed));
  }, [movementInput]);

  // Handle movement joystick
  const handleMovement = (input) => {
    setMovementInput(input);
    
    // Send movement commands to backend
    if (isConnected) {
      socketService.sendMovement(input.x, input.y, rotationInput.x);
    }
  };

  // Handle rotation joystick
  const handleRotation = (input) => {
    setRotationInput(input);
    
    // Update direction based on rotation input
    setDirection(prev => {
      let newDir = prev + input.x * 5;
      if (newDir < 0) newDir += 360;
      if (newDir >= 360) newDir -= 360;
      return newDir;
    });
    
    // Send rotation commands to backend
    if (isConnected) {
      socketService.sendMovement(movementInput.x, movementInput.y, input.x);
    }
  };

  return (
    <div className="app">
      <Header 
        batteryLevel={batteryLevel}
        isConnected={isConnected}
      />

      {/* Stats Panel */}
      <Stats 
        movementInput={movementInput}
        rotationInput={rotationInput}
        speed={speed}
      />

      <div className="main-content">
        {/* Left side - Speed */}
        <div className="left-panel">
          <SpeedDisplay speed={speed} />
        </div>

        {/* Center - Car visualization */}
        <div className="center-panel">
          <CarVisualization />
        </div>

        {/* Right side - Empty for now */}
        <div className="right-panel">
        </div>
      </div>

      <div className="joystick-row">
        {/* Left Joystick - Movement */}
        <Joystick 
          type="movement" 
          icon={Move}
          onMove={handleMovement}
        />

        {/* Control Panel */}
        <ControlPanel 
          mode={mode}
          onModeChange={setMode}
        />

        {/* Right Joystick - Rotation */}
        <Joystick 
          type="rotation" 
          icon={RotateCw}
          onMove={handleRotation}
        />
      </div>
    </div>
  );
}

export default App;
