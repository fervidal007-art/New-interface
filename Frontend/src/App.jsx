import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Move, RotateCw } from 'lucide-react';
import Header from './components/Header';
import SpeedDisplay from './components/SpeedDisplay';
import Joystick from './components/Joystick';
import CarVisualization from './components/CarVisualization';
import ControlPanel from './components/ControlPanel';
import Stats from './components/Stats';
import LogsModal from './components/LogsModal';
import socketService from './utils/socket';

function App() {
  const [speed, setSpeed] = useState(0);
  const [direction, setDirection] = useState(45);
  const [gpsCoords] = useState({ lat: 41.40338, lng: 2.17403 });
  const [batteryLevel, setBatteryLevel] = useState(55);
  const [mode, setMode] = useState('manual');
  const [movementInput, setMovementInput] = useState({ x: 0, y: 0 });
  const [rotationInput, setRotationInput] = useState({ x: 0, y: 0 });
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [path, setPath] = useState([{ x: 0, y: 0, t: Date.now() }]);
  const [movementHistory, setMovementHistory] = useState([]);
  const [isReturning, setIsReturning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [conversations, setConversations] = useState({});
  const [isLogsOpen, setIsLogsOpen] = useState(false);

  const handleDeviceList = useCallback(
    (data = {}) => {
      const deviceList = Array.isArray(data.devices) ? data.devices : [];
      setDevices(deviceList);

      if (deviceList.length === 0) {
        setSelectedDevice('');
        return;
      }

      if (!deviceList.includes(selectedDevice)) {
        setSelectedDevice(deviceList[0]);
      }
    },
    [selectedDevice]
  );

  const handleConversationMessage = useCallback((msg = {}) => {
    const { device, direction, payload, ts, origin } = msg;
    if (!device) {
      return;
    }

    setConversations(prev => {
      const history = prev[device] ? [...prev[device]] : [];
      history.push({
        device,
        direction,
        payload,
        origin,
        ts: typeof ts === 'number' ? ts * 1000 : Date.now(),
      });
      if (history.length > 250) {
        history.shift();
      }
      return {
        ...prev,
        [device]: history,
      };
    });
  }, []);

  useEffect(() => {
    socketService.connect();

    const handleConnect = () => {
      setIsConnected(true);
      console.log('✅ Conectado al servidor');
      socketService.requestDeviceList();
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      console.log('⚠️ Desconectado del servidor');
    };

    const handleError = (err) => {
      console.error('Socket error:', err);
    };

    socketService.on('connect', handleConnect);
    socketService.on('disconnect', handleDisconnect);
    socketService.on('device_list', handleDeviceList);
    socketService.on('conversation_message', handleConversationMessage);
    socketService.on('error', handleError);

    return () => {
      socketService.off('connect', handleConnect);
      socketService.off('disconnect', handleDisconnect);
      socketService.off('device_list', handleDeviceList);
      socketService.off('conversation_message', handleConversationMessage);
      socketService.off('error', handleError);
      socketService.disconnect();
    };
  }, [handleDeviceList, handleConversationMessage]);

  const handleConnect = () => {
    console.log('Attempting to connect...');
    socketService.connect();
  };

  const handleRefreshDevices = () => {
    console.log('Requesting device list...');
    socketService.requestDeviceList();
  };

  useEffect(() => {
    const magnitude = Math.sqrt(movementInput.x ** 2 + movementInput.y ** 2);
    const maxSpeed = 82;
    setSpeed(Math.round(magnitude * maxSpeed));
  }, [movementInput]);

  const COMMAND_THRESHOLD = 0.02;

  const handleMovement = (input) => {
    if (isReturning) return;
    setMovementInput(input);

    if (isConnected) {
      socketService.sendMovement(selectedDevice, input.x, input.y, rotationInput.x);
    }
  };

  const handleRotation = (input) => {
    if (isReturning) return;
    setRotationInput(input);

    setDirection(prev => {
      let newDir = prev + input.x * 5;
      if (newDir < 0) newDir += 360;
      if (newDir >= 360) newDir -= 360;
      return newDir;
    });

    if (isConnected) {
      socketService.sendMovement(selectedDevice, movementInput.x, movementInput.y, input.x);
    }
  };

  const currentConversation = useMemo(() => {
    return selectedDevice ? conversations[selectedDevice] || [] : [];
  }, [conversations, selectedDevice]);

  const movementRef = useRef(movementInput);
  const rotationRef = useRef(rotationInput);
  const positionRef = useRef(position);
  const returningRef = useRef(isReturning);
  useEffect(() => {
    movementRef.current = movementInput;
  }, [movementInput]);

  useEffect(() => {
    rotationRef.current = rotationInput;
  }, [rotationInput]);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  useEffect(() => {
    returningRef.current = isReturning;
  }, [isReturning]);

  useEffect(() => {
    let animationId;
    let last = performance.now();
    const SPEED = 150; // px por segundo a potencia maxima

    const step = (timestamp) => {
      const dt = (timestamp - last) / 1000;
      last = timestamp;
      const { x, y } = movementRef.current;
      const magnitude = Math.hypot(x, y);

      if (!returningRef.current) {
        const startPos = positionRef.current;
        let nextPos = startPos;

        if (Math.abs(x) > 0.001 || Math.abs(y) > 0.001) {
          nextPos = {
            x: startPos.x + x * SPEED * dt,
            y: startPos.y - y * SPEED * dt,
          };
          positionRef.current = nextPos;
          setPosition(nextPos);
        }

        if (magnitude > COMMAND_THRESHOLD) {
          const entry = {
            x,
            y,
            rotation: rotationRef.current,
            duration: Math.max(16, dt * 1000),
            start: startPos,
            end: nextPos,
          };
          setMovementHistory((prev) => {
            const next = [...prev, entry];
            if (next.length > 2000) next.shift();
            return next;
          });
        }
      }

      animationId = requestAnimationFrame(step);
    };

    animationId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationId);
  }, []);

  useEffect(() => {
    if (isReturning) return;
    setPath((prev) => {
      const last = prev[prev.length - 1];
      if (last && Math.abs(last.x - position.x) < 0.1 && Math.abs(last.y - position.y) < 0.1) {
        return prev;
      }
      const next = [...prev, { ...position, t: Date.now() }];
      if (next.length > 2000) {
        next.shift();
      }
      return next;
    });
  }, [position, isReturning]);

  const handleReturnToOrigin = useCallback(async () => {
    if (!movementHistory.length || !socketService.isConnected() || !selectedDevice || isReturning) {
      return;
    }
    setIsReturning(true);
    setMovementInput({ x: 0, y: 0 });
    setRotationInput({ x: 0, y: 0 });
    movementRef.current = { x: 0, y: 0 };

    const historySnapshot = [...movementHistory].reverse();
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    let cancelled = false;

    for (let i = 0; i < historySnapshot.length; i += 1) {
      const cmd = historySnapshot[i];
      if (!socketService.isConnected()) {
        cancelled = true;
        break;
      }

      const duration = Math.max(16, cmd.duration ?? 16);
      const start = cmd.end;
      const target = cmd.start;

      socketService.sendMovement(selectedDevice, -cmd.x, -cmd.y, -cmd.rotation);

      await Promise.all([
        delay(duration),
        new Promise((resolve) => {
          const startTime = performance.now();
          const animate = (now) => {
            if (cancelled) {
              resolve();
              return;
            }
            const progress = duration ? Math.min(1, (now - startTime) / duration) : 1;
            setPosition({
              x: start.x + (target.x - start.x) * progress,
              y: start.y + (target.y - start.y) * progress,
            });
            if (progress < 1) {
              requestAnimationFrame(animate);
            } else {
              setPath((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev));
              resolve();
            }
          };
          requestAnimationFrame(animate);
        }),
      ]);
    }

    if (!cancelled) {
      setMovementHistory([]);
      setPosition({ x: 0, y: 0 });
      setPath([{ x: 0, y: 0, t: Date.now() }]);
    }
    setIsReturning(false);
  }, [movementHistory, selectedDevice, isReturning, isConnected]);

  return (
    <div className="app">
      <Header 
        batteryLevel={batteryLevel}
        isConnected={isConnected}
        onConnect={handleConnect}
        devices={devices}
        selectedDevice={selectedDevice}
        onDeviceChange={setSelectedDevice}
        onRefresh={handleRefreshDevices}
        onOpenLogs={() => setIsLogsOpen(true)}
        logsDisabled={!selectedDevice}
      />

      <Stats 
        movementInput={movementInput}
        rotationInput={rotationInput}
        speed={speed}
      />

      <div className="main-content">
        <div className="left-panel">
          <SpeedDisplay speed={speed} />
        </div>

        <div className="center-panel">
          <CarVisualization position={position} path={path} />
          <button
            className="return-button"
            disabled={!movementHistory.length || !selectedDevice || isReturning || !isConnected}
            onClick={handleReturnToOrigin}
          >
            {isReturning ? 'Retornando' : 'Retorno'}
          </button>
        </div>

        <div className="right-panel" />
      </div>

      <div className="joystick-row">
        <Joystick 
          type="movement" 
          icon={Move}
          onMove={handleMovement}
        />

        <ControlPanel 
          mode={mode}
          onModeChange={setMode}
        />

        <Joystick 
          type="rotation" 
          icon={RotateCw}
          onMove={handleRotation}
        />
      </div>

      {isLogsOpen && (
        <LogsModal
          device={selectedDevice}
          messages={currentConversation}
          isConnected={isConnected}
          onClose={() => setIsLogsOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
