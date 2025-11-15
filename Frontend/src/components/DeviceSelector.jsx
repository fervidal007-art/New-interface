import { Zap, RefreshCw } from 'lucide-react';

function DeviceSelector({ devices, selectedDevice, onDeviceChange, onRefresh }) {
  return (
    <div className="device-selector-container">
      <select 
        value={selectedDevice} 
        onChange={(e) => onDeviceChange(e.target.value)}
        disabled={devices.length === 0}
        className="device-select"
      >
        {devices.length > 0 ? (
          devices.map(device => (
            <option key={device} value={device}>
              {device}
            </option>
          ))
        ) : (
          <option value="">No hay dispositivos</option>
        )}
      </select>
      <button onClick={onRefresh} className="refresh-btn">
        <RefreshCw size={16} />
      </button>
    </div>
  );
}

export default DeviceSelector;

