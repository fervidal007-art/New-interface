function ControlPanel({ mode, onModeChange, disableAuto, disableHome }) {
  const isManual = mode === 'manual';

  return (
    <div className="control-panel">
      <div className="control-right">
        <button
          className={`text-btn ${mode === 'home' ? 'active' : ''}`}
          onClick={() => onModeChange('home')}
          disabled={disableHome}
        >
          FLY HOME
        </button>
        <button
          className={`mode-btn ${mode === 'auto' ? 'active' : ''}`}
          onClick={() => onModeChange('auto')}
          disabled={disableAuto}
        >
          AUTO
        </button>
        <button
          className={`mode-btn ${isManual ? 'active' : ''}`}
          onClick={() => onModeChange('manual')}
          disabled={isManual}
        >
          MANUAL
        </button>
      </div>
    </div>
  );
}

export default ControlPanel;
