import { Activity, Zap, Wind } from 'lucide-react';

function Stats({ movementInput, rotationInput, speed }) {
  return (
    <div className="stats-panel">
      <div className="stat-card">
        <div className="stat-icon">
          <Activity size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Movimiento</div>
          <div className="stat-values">
            <span>X: {movementInput.x.toFixed(2)}</span>
            <span>Y: {movementInput.y.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Zap size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Rotación</div>
          <div className="stat-value">
            {rotationInput.x.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Wind size={20} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Velocidad</div>
          <div className="stat-value">
            {speed} km/h
          </div>
        </div>
      </div>
    </div>
  );
}

export default Stats;

