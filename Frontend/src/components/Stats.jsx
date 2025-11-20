import { Activity, Zap, Wind } from 'lucide-react';

function Stats({ pose, joystick, rotationInput, omega, batteryVoltage, simulated, quadrantLabel }) {
  const x = Number.isFinite(pose?.x) ? pose.x : 0;
  const y = Number.isFinite(pose?.y) ? pose.y : 0;
  const theta = Number.isFinite(pose?.theta) ? pose.theta : 0;
  const joyX = Number.isFinite(joystick?.x) ? joystick.x : 0;
  const joyY = Number.isFinite(joystick?.y) ? joystick.y : 0;
  const joyRot = Number.isFinite(rotationInput?.x) ? rotationInput.x : 0;
  const omegaValue = Number.isFinite(omega) ? omega : 0;
  const voltage = Number.isFinite(batteryVoltage) ? batteryVoltage : 0;
  const thetaDeg = (theta * (180 / Math.PI)).toFixed(1);

  return (
    <div className="stats-panel">
      <div className="stat-card">
        <div className="stat-icon">
          <Activity size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Posicion (m)</div>
          <div className="stat-values">
            <span>X: {x.toFixed(2)}</span>
            <span>Y: {y.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Zap size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Orientacion</div>
          <div className="stat-value">{thetaDeg} deg</div>
          <div className="stat-subtext">omega cmd: {omegaValue.toFixed(2)} rad/s</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Wind size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Entradas</div>
          <div className="stat-values">
            <span>Joy X: {joyX.toFixed(2)}</span>
            <span>Joy Y: {joyY.toFixed(2)}</span>
            <span>Rot: {joyRot.toFixed(2)}</span>
          </div>
          <div className="stat-subtext">
            Bateria: {voltage.toFixed(1)} V - {simulated ? 'Simulado' : 'Fisico'}
          </div>
          <div className="stat-subtext">
            Cuadrante: {quadrantLabel || 'Fuera del tablero'}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Stats;
