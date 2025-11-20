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
import { BOARD_SETTINGS, BOARD_HALF_SPAN, worldToQuadrant } from './utils/board';

const getNow = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());
const toBatteryPercent = (voltage = 0) => {
  const minV = 10.5;
  const maxV = 12.0;
  const clamped = Math.min(Math.max(voltage, minV), maxV);
  const percent = Math.round(((clamped - minV) / (maxV - minV)) * 100);
  return Math.min(100, Math.max(0, percent));
};

const MODES = Object.freeze({
  manual: 'manual',
  auto: 'auto',
  home: 'home',
});

const MAX_LINEAR = 0.6;
const MAX_LATERAL = 0.6;
const BOUNDARY_MARGIN = 0.05;
const BOARD_LIMIT = BOARD_HALF_SPAN - BOUNDARY_MARGIN;
const clampCoordinate = (value) => Math.max(-BOARD_LIMIT, Math.min(BOARD_LIMIT, value));
const clampPointToBoard = ({ x, y }) => ({
  x: clampCoordinate(x),
  y: clampCoordinate(y),
});
const normalizeAngle = (angle = 0) => {
  const twoPi = Math.PI * 2;
  let result = angle % twoPi;
  if (result > Math.PI) result -= twoPi;
  if (result < -Math.PI) result += twoPi;
  return result;
};

function App() {
  const [batteryLevel, setBatteryLevel] = useState(0);
  const [batteryVoltage, setBatteryVoltage] = useState(0);
  const [mode, setMode] = useState(MODES.manual);
  const [movementInput, setMovementInput] = useState({ x: 0, y: 0 });
  const [rotationInput, setRotationInput] = useState({ x: 0, y: 0 });
  const [movementHistory, setMovementHistory] = useState([]);
  const [isReturning, setIsReturning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [conversations, setConversations] = useState({});
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [telemetryByDevice, setTelemetryByDevice] = useState({});
  const [positionMap, setPositionMap] = useState({});
  const [pathMap, setPathMap] = useState({});
  const [targetQuadrant, setTargetQuadrant] = useState(null);
  const [autoTarget, setAutoTarget] = useState(null);
  const [isAutoNavigating, setIsAutoNavigating] = useState(false);

  const defaultPathRef = useRef([{ x: 0, y: 0, t: Date.now() }]);
  const commandTrackRef = useRef({ x: 0, y: 0, rotation: 0, startedAt: getNow() });
  const poseRef = useRef({ x: 0, y: 0, theta: 0 });
  const autoIntervalRef = useRef(null);
  const movementRef = useRef(movementInput);
  const rotationRef = useRef(rotationInput);
  const rotationTargetRef = useRef(null);
  const [rotationTarget, setRotationTarget] = useState(null);
  const lastSentCommandRef = useRef({ x: 0, y: 0, rotation: 0 });

const applyBoundsToInput = useCallback((input) => {
  const pose = poseRef.current || { x: 0, y: 0, theta: 0 };
  const heading = -(pose.theta || 0);
  const bodyForward = input.y * MAX_LINEAR;
  const bodyLateral = input.x * MAX_LATERAL;
  const worldVx = bodyForward * Math.cos(heading) - bodyLateral * Math.sin(heading);
  const worldVy = bodyForward * Math.sin(heading) + bodyLateral * Math.cos(heading);
  const dt = 0.15;

  const limitScale = (pos, vel) => {
    if (vel === 0) {
      return 1;
    }
    if ((vel > 0 && pos >= BOARD_LIMIT) || (vel < 0 && pos <= -BOARD_LIMIT)) {
      return 0;
    }
    const remaining = vel > 0 ? BOARD_LIMIT - pos : pos + BOARD_LIMIT;
    const travel = vel * dt;
    if (Math.abs(travel) <= Math.abs(remaining)) {
      return 1;
    }
    const ratio = remaining / travel;
    return Math.max(0, Math.min(1, ratio));
  };

  const scale = Math.min(limitScale(pose.x, worldVx), limitScale(pose.y, worldVy));
  if (scale >= 1) {
    return input;
  }
  return {
    x: input.x * scale,
    y: input.y * scale,
  };
}, []);

  const handleDeviceList = useCallback(
    (data = {}) => {
      const deviceList = Array.isArray(data.devices) ? data.devices : [];
      setDevices(deviceList);

      if (deviceList.length === 0) {
        setSelectedDevice('');
        return;
      }

      if (!selectedDevice || !deviceList.includes(selectedDevice)) {
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

    setConversations((prev) => {
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

  const handleTelemetry = useCallback(
    (data = {}) => {
      const { device, pose = {}, battery = 0 } = data;
      if (!device) {
        return;
      }

      const rawX = typeof pose.x === 'number' ? pose.x : 0;
      const rawY = typeof pose.y === 'number' ? pose.y : 0;
      const theta = typeof pose.theta === 'number' ? pose.theta : 0;
      const safePoint = clampPointToBoard({ x: rawX, y: rawY });
      const x = safePoint.x;
      const y = safePoint.y;

      poseRef.current = { x, y, theta };

      setTelemetryByDevice((prev) => ({
        ...prev,
        [device]: data,
      }));

      setPositionMap((prev) => ({
        ...prev,
        [device]: { x, y, theta },
      }));

      setPathMap((prev) => {
        const existing = prev[device] || [];
        const last = existing[existing.length - 1];

        if (last && Math.abs(last.x - x) < 0.001 && Math.abs(last.y - y) < 0.001) {
          return prev;
        }

        const point = { x, y, t: Date.now() };
        const nextPath =
          existing.length >= 2000
            ? [...existing.slice(1), point]
            : existing.length
            ? [...existing, point]
            : [point];

        return {
          ...prev,
          [device]: nextPath,
        };
      });

      if (!selectedDevice) {
        setSelectedDevice(device);
      }

      if (!selectedDevice || selectedDevice === device) {
        setBatteryVoltage(battery || 0);
        setBatteryLevel(toBatteryPercent(battery || 0));
      }
    },
    [selectedDevice]
  );

  useEffect(() => {
    socketService.connect();

    const handleConnect = () => {
      setIsConnected(true);
      socketService.requestDeviceList();
    };

    const handleDisconnect = () => {
      setIsConnected(false);
    };

    const handleError = (err) => {
      console.error('Socket error:', err);
    };

    socketService.on('connect', handleConnect);
    socketService.on('disconnect', handleDisconnect);
    socketService.on('device_list', handleDeviceList);
    socketService.on('conversation_message', handleConversationMessage);
    socketService.on('telemetry', handleTelemetry);
    socketService.on('error', handleError);

    return () => {
      socketService.off('connect', handleConnect);
      socketService.off('disconnect', handleDisconnect);
      socketService.off('device_list', handleDeviceList);
      socketService.off('conversation_message', handleConversationMessage);
      socketService.off('telemetry', handleTelemetry);
      socketService.off('error', handleError);
      socketService.disconnect();
    };
  }, [handleDeviceList, handleConversationMessage, handleTelemetry]);

  useEffect(() => {
    movementRef.current = movementInput;
  }, [movementInput]);

  useEffect(() => {
    rotationRef.current = rotationInput;
  }, [rotationInput]);

  useEffect(() => {
    rotationTargetRef.current = rotationTarget;
  }, [rotationTarget]);

  const handleConnect = () => {
    socketService.connect();
  };

  const handleRefreshDevices = () => {
    if (socketService.isConnected()) {
      socketService.requestDeviceList();
    }
  };

  const cancelAutoNavigation = useCallback(
    (shouldStop = true) => {
      if (autoIntervalRef.current) {
        clearInterval(autoIntervalRef.current);
        autoIntervalRef.current = null;
      }
      setAutoTarget(null);
      setTargetQuadrant(null);
      setIsAutoNavigating(false);
      if (shouldStop && selectedDevice) {
        socketService.sendStop(selectedDevice);
      }
    },
    [selectedDevice]
  );

  const handleModeChange = useCallback(
    (nextMode) => {
      if (nextMode === mode) {
        return;
      }

      const resetManualInputs = () => {
        setMovementInput({ x: 0, y: 0 });
        setRotationInput({ x: 0, y: 0 });
        movementRef.current = { x: 0, y: 0 };
        rotationRef.current = { x: 0, y: 0 };
        setRotationTarget(null);
        rotationTargetRef.current = null;
      };

      if (nextMode === MODES.manual) {
        cancelAutoNavigation();
        resetManualInputs();
        setMode(MODES.manual);
        return;
      }

      if (nextMode === MODES.auto) {
        cancelAutoNavigation();
        resetManualInputs();
        if (selectedDevice) {
          socketService.sendStop(selectedDevice);
        }
        setTargetQuadrant(null);
        setAutoTarget(null);
        setMode(MODES.auto);
        return;
      }

      if (nextMode === MODES.home) {
        cancelAutoNavigation();
        resetManualInputs();
        setTargetQuadrant(null);
        setMode(MODES.home);
        setAutoTarget({ x: 0, y: 0 });
      }
    },
    [mode, cancelAutoNavigation, selectedDevice]
  );

const handleMovement = (input) => {
  if (mode !== MODES.manual) {
    return;
  }
  if (isAutoNavigating) {
    cancelAutoNavigation();
  }
  if (isReturning) return;
  const correctedInput = { x: -input.x, y: input.y };
  const bounded = applyBoundsToInput(correctedInput);
  movementRef.current = bounded;
  setMovementInput(bounded);

  if (isConnected && selectedDevice) {
    socketService.sendMovement(selectedDevice, bounded.x, bounded.y, rotationInput.x);
  }
};

  const handleRotation = (input) => {
    if (mode !== MODES.manual) {
      return;
    }
    if (isAutoNavigating) {
      cancelAutoNavigation();
    }
    if (isReturning) return;
    setRotationInput(input);

    const magnitude = Math.hypot(input.x, input.y);
    if (magnitude < 0.1) {
      setRotationTarget(null);
      rotationTargetRef.current = null;
      if (isConnected && selectedDevice) {
        socketService.sendMovement(selectedDevice, movementRef.current.x, movementRef.current.y, 0);
      }
      return;
    }

    const desiredHeading = Math.atan2(-input.y, input.x);
    setRotationTarget(desiredHeading);
    rotationTargetRef.current = desiredHeading;

    if (isConnected && selectedDevice) {
      const pose = poseRef.current || { theta: 0 };
      const diff = normalizeAngle(desiredHeading - (pose.theta || 0));
      const rotCommand = Math.max(-1, Math.min(1, diff / Math.PI));
      socketService.sendMovement(
        selectedDevice,
        movementRef.current.x,
        movementRef.current.y,
        rotCommand
      );
      rotationRef.current = { x: rotCommand, y: 0 };
    }
  };

  const currentConversation = useMemo(() => {
    return selectedDevice ? conversations[selectedDevice] || [] : [];
  }, [conversations, selectedDevice]);

  useEffect(() => {
    const now = getNow();
    commandTrackRef.current = { x: 0, y: 0, rotation: 0, startedAt: now };
    setMovementHistory([]);
    cancelAutoNavigation(false);
  }, [selectedDevice]);

  useEffect(() => {
    const now = getNow();
    const prev = commandTrackRef.current;
    const next = { x: movementInput.x, y: movementInput.y, rotation: rotationInput.x };
    const changed =
      Math.abs(prev.x - next.x) > 0.01 ||
      Math.abs(prev.y - next.y) > 0.01 ||
      Math.abs(prev.rotation - next.rotation) > 0.01;

    if (changed) {
      const duration = Math.max(16, now - prev.startedAt);
      if (Math.abs(prev.x) > 0.001 || Math.abs(prev.y) > 0.001 || Math.abs(prev.rotation) > 0.001) {
        setMovementHistory((history) => {
          const nextHistory = [...history, { x: prev.x, y: prev.y, rotation: prev.rotation, duration }];
          if (nextHistory.length > 2000) {
            nextHistory.shift();
          }
          return nextHistory;
        });
      }
      commandTrackRef.current = { ...next, startedAt: now };
    }
  }, [movementInput, rotationInput]);

  const handleReturnToOrigin = useCallback(async () => {
    if (!movementHistory.length || !socketService.isConnected() || !selectedDevice || isReturning) {
      return;
    }
    if (mode !== MODES.manual) {
      handleModeChange(MODES.manual);
    }
    cancelAutoNavigation();
    setIsReturning(true);
    setMovementInput({ x: 0, y: 0 });
    setRotationInput({ x: 0, y: 0 });

    const historySnapshot = [...movementHistory].reverse();
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    for (const cmd of historySnapshot) {
      if (!socketService.isConnected()) {
        break;
      }
      socketService.sendMovement(selectedDevice, -cmd.x, -cmd.y, -cmd.rotation);
      await delay(Math.max(16, cmd.duration ?? 16));
    }

    socketService.sendStop(selectedDevice);
    setMovementHistory([]);
    commandTrackRef.current = { x: 0, y: 0, rotation: 0, startedAt: getNow() };
    setIsReturning(false);
  }, [movementHistory, selectedDevice, isReturning, handleModeChange, mode]);

  useEffect(() => {
    if (!isConnected || !selectedDevice || mode !== MODES.manual || isReturning) {
      return undefined;
    }

    let rafId;

    const step = () => {
      const pose = poseRef.current || { theta: 0 };
      const desiredHeading = rotationTargetRef.current;
      const boundedMove = applyBoundsToInput(movementRef.current);
      movementRef.current = boundedMove;
      let rotationCmd = 0;

      if (desiredHeading != null) {
        const diff = normalizeAngle(desiredHeading - (pose.theta || 0));
        if (Math.abs(diff) < 0.02) {
          rotationCmd = 0;
          setRotationTarget(null);
          rotationTargetRef.current = null;
        } else {
          rotationCmd = Math.max(-1, Math.min(1, diff / Math.PI));
        }
      }

      if (socketService.isConnected()) {
        socketService.sendMovement(selectedDevice, boundedMove.x, boundedMove.y, rotationCmd);
        lastSentCommandRef.current = { x: boundedMove.x, y: boundedMove.y, rotation: rotationCmd };
      }

      if (mode === MODES.manual && !isReturning) {
        rafId = requestAnimationFrame(step);
      }
    };

    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [applyBoundsToInput, isConnected, selectedDevice, mode, isReturning]);

  useEffect(() => {
    if (autoIntervalRef.current) {
      clearInterval(autoIntervalRef.current);
      autoIntervalRef.current = null;
    }

    if (
      !autoTarget ||
      !isConnected ||
      !selectedDevice ||
      (mode !== MODES.auto && mode !== MODES.home)
    ) {
      setIsAutoNavigating(false);
      return;
    }

    setIsAutoNavigating(true);

    autoIntervalRef.current = setInterval(() => {
      const pose = poseRef.current;
      const dx = autoTarget.x - pose.x;
      const dy = autoTarget.y - pose.y;
      const distance = Math.hypot(dx, dy);

      if (distance < 0.05) {
        const headingError = normalizeAngle(pose.theta);
        const headingAligned = Math.abs(headingError) < 0.05;

        if (mode === MODES.home && !headingAligned) {
          const rotCommand = Math.max(-1, Math.min(1, -headingError / Math.PI));
          socketService.sendMovement(selectedDevice, 0, 0, rotCommand);
          return;
        }

        socketService.sendStop(selectedDevice);
        setAutoTarget(null);
        setTargetQuadrant(null);
        setIsAutoNavigating(false);
        setMode(MODES.manual);
        if (autoIntervalRef.current) {
          clearInterval(autoIntervalRef.current);
          autoIntervalRef.current = null;
        }
        return;
      }

      const desiredSpeed = Math.min(0.4, distance);
      const worldVx = (dx / distance) * desiredSpeed;
      const worldVy = (dy / distance) * desiredSpeed;

      const theta = pose.theta || 0;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);

      const bodyVx = worldVy * sinT + worldVx * cosT;
      const bodyVy = worldVy * cosT - worldVx * sinT;
      const maxLinear = 0.6;
      const joyY = Math.max(-1, Math.min(1, bodyVx / maxLinear));
      const joyX = Math.max(-1, Math.min(1, bodyVy / maxLinear));

      socketService.sendMovement(selectedDevice, joyX, joyY, 0);
    }, 120);

    return () => {
      if (autoIntervalRef.current) {
        clearInterval(autoIntervalRef.current);
        autoIntervalRef.current = null;
      }
    };
  }, [autoTarget, isConnected, selectedDevice, mode]);

  const telemetry = selectedDevice ? telemetryByDevice[selectedDevice] : null;
  const position =
    selectedDevice && positionMap[selectedDevice]
      ? positionMap[selectedDevice]
      : { x: 0, y: 0, theta: 0 };
  const path =
    selectedDevice && pathMap[selectedDevice] && pathMap[selectedDevice].length
      ? pathMap[selectedDevice]
      : defaultPathRef.current;

  const currentQuadrant = useMemo(
    () => worldToQuadrant(position.x, position.y, BOARD_SETTINGS),
    [position.x, position.y]
  );

  const handleQuadrantSelect = useCallback(
    (quadrant) => {
      if (!quadrant || mode !== MODES.auto) return;
      cancelAutoNavigation();
      const safeCenter = clampPointToBoard(quadrant.center);
      setTargetQuadrant({ ...quadrant, center: safeCenter });
      setAutoTarget(safeCenter);
    },
    [cancelAutoNavigation, mode]
  );

  const speed = useMemo(() => {
    if (telemetry && telemetry.command) {
      const { vx = 0, vy = 0 } = telemetry.command;
      return Math.sqrt(vx * vx + vy * vy);
    }
    const magnitude = Math.sqrt(movementInput.x ** 2 + movementInput.y ** 2);
    const maxLinear = 0.6;
    return magnitude * maxLinear;
  }, [telemetry, movementInput]);

  const isReturnDisabled =
    !movementHistory.length ||
    !selectedDevice ||
    isReturning ||
    !isConnected ||
    isAutoNavigating ||
    mode !== MODES.manual;

  const joystickDisabled = mode !== MODES.manual || isReturning || isAutoNavigating;

  return (
    <div className="app">
      <Header
        batteryLevel={batteryLevel}
        batteryVoltage={batteryVoltage}
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
        pose={position}
        joystick={movementInput}
        rotationInput={rotationInput}
        omega={telemetry?.command?.omega ?? 0}
        batteryVoltage={batteryVoltage}
        simulated={telemetry?.simulated}
        quadrantLabel={currentQuadrant ? currentQuadrant.label : 'Fuera del tablero'}
      />

      <div className="main-content">
        <div className="left-panel">
          <SpeedDisplay speed={speed} />
        </div>

        <div className="center-panel">
          <CarVisualization
            position={position}
            path={path}
            boardSettings={BOARD_SETTINGS}
            currentQuadrant={currentQuadrant}
            targetQuadrant={targetQuadrant}
            onQuadrantSelect={handleQuadrantSelect}
          />
          <div className="quadrant-info">
            <span>Actual: {currentQuadrant ? currentQuadrant.label : 'Fuera del tablero'}</span>
            {targetQuadrant && (
              <span>
                Objetivo: {targetQuadrant.label}{' '}
                {isAutoNavigating ? '(navegando)' : ''}
              </span>
            )}
            {mode === MODES.home && !targetQuadrant && (
              <span>Objetivo: Origen (Fly Home)</span>
            )}
          </div>
          <button className="return-button" disabled={isReturnDisabled} onClick={handleReturnToOrigin}>
            {isReturning ? 'Retornando' : 'Retorno'}
          </button>
        </div>

        <div className="right-panel" />
      </div>

      <div className="joystick-row">
        <Joystick type="movement" icon={Move} onMove={handleMovement} disabled={joystickDisabled} />

        <ControlPanel
          mode={mode}
          onModeChange={handleModeChange}
          disableAuto={mode !== MODES.manual}
          disableHome={mode !== MODES.manual}
        />

        <Joystick type="rotation" icon={RotateCw} onMove={handleRotation} disabled={joystickDisabled} />
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
