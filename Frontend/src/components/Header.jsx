import { Battery, Clock } from 'lucide-react';
import { useState, useEffect } from 'react';
import ConnectionStatus from './ConnectionStatus';
import DeviceSelector from './DeviceSelector';
import logoITESO from '../Public/Logo-ITESO-Principal-SinFondo.png';

function Header({ batteryLevel, isConnected, onConnect, devices, selectedDevice, onDeviceChange, onRefresh }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="header">
      <div className="header-left">
        <ConnectionStatus isConnected={isConnected} onConnect={onConnect} />
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
          <span>{batteryLevel}% ({Math.floor(batteryLevel / 25)}h {Math.floor((batteryLevel % 25) * 2.4)}m)</span>
        </div>
        <div className="logo-container">
          <img src={logoITESO} alt="ITESO Logo" className="iteso-logo" />
        </div>
      </div>
    </div>
  );
}

export default Header;










