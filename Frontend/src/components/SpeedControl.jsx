import { Gauge } from 'lucide-react';

function SpeedControl({ speedLevel, onSpeedChange, disabled }) {
  return (
    <div className="speed-control">
      <div className="speed-control-header">
        <Gauge size={20} />
        <span>Velocidad</span>
      </div>
      <div className="speed-levels">
        {[1, 2, 3, 4, 5].map(level => (
          <button
            key={level}
            className={`speed-level-btn ${speedLevel === level ? 'active' : ''}`}
            onClick={() => onSpeedChange(level)}
            disabled={disabled}
            aria-label={`Velocidad ${level}`}
          >
            {level}
          </button>
        ))}
      </div>
      <div className="speed-percentage">
        {(speedLevel * 20)}%
      </div>
    </div>
  );
}

export default SpeedControl;







