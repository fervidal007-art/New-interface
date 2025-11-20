import { Battery, Clock } from 'lucide-react';
import { useState, useEffect } from 'react';
import ConnectionStatus from './ConnectionStatus';
import DeviceSelector from './DeviceSelector';
import logoITESO from '../Public/Logo-ITESO-Principal-SinFondo.png';

function Header({ batteryLevel, batteryVoltage = 0, isConnected, onConnect, devices, selectedDevice, onDeviceChange, onRefresh, onOpenLogs, logsDisabled }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const voltageText = Number.isFinite(batteryVoltage) ? batteryVoltage.toFixed(1) : '0.0';

  return (
    <div className="header">
      <div className="header-left">
        <ConnectionStatus isConnected={isConnected} onConnect={onConnect} />
        <button
          className="header-logs-btn"
          onClick={onOpenLogs}
          disabled={logsDisabled}
        >
          Ver Logs
        </button>
      </div>

      <div className="header-center">
        <DeviceSelector 
          devices={devices}
          selectedDevice={selectedDevice}
          onDeviceChange={onDeviceChange}
          onRefresh={onRefresh}
        />
      </div>

      <div className="header-right">
        <div className="status-item">
          <Clock size={18} />
          <span>{currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <div className="status-item">
          <Battery size={18} />
          <span>{batteryLevel}% ({voltageText} V)</span>
        </div>
        <div className="logo-container">
          <img src={logoITESO} alt="ITESO Logo" className="iteso-logo" />
        </div>
      </div>
    </div>
  );
}

export default Header;








