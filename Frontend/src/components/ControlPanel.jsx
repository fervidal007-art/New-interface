function ControlPanel({ 
  mode, 
  onModeChange 
}) {
  return (
    <div className="control-panel">
      <div className="control-right">
        <button className="text-btn">FLY HOME</button>
        <button 
          className={`mode-btn ${mode === 'auto' ? 'active' : ''}`}
          onClick={() => onModeChange('auto')}
        >
          AUTO
        </button>
        <button 
          className={`mode-btn ${mode === 'manual' ? 'active' : ''}`}
          onClick={() => onModeChange('manual')}
        >
          MANUAL
        </button>
      </div>
    </div>
  );
}

export default ControlPanel;

