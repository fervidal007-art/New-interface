import { Battery, Clock, Maximize2, Minimize2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import ConnectionStatus from './ConnectionStatus';
import DeviceSelector from './DeviceSelector';
import logoITESO from '../Public/Logo-ITESO-Principal-SinFondo.png';

function Header({ batteryLevel, isConnected, onConnect, devices, selectedDevice, onDeviceChange, onRefresh, onOpenLogs, logsDisabled }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (err) {
      console.error('Error al cambiar pantalla completa:', err);
    }
  };

  return (
    <div className="header">
      <div className="header-left">
        <div className="logo-container">
          <img src={logoITESO} alt="ITESO" className="iteso-logo" />
        </div>
        <ConnectionStatus isConnected={isConnected} />
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
          <Clock size={16} />
          <span className="status-time">{currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <div className="status-item">
          <Battery size={16} />
          <span className="status-battery">{batteryLevel}%</span>
        </div>
        <button
          className="header-fullscreen-btn"
          onClick={toggleFullscreen}
          aria-label="Pantalla completa"
          title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
        >
          {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>
        <button
          className="header-logs-btn"
          onClick={onOpenLogs}
          disabled={logsDisabled}
        >
          Logs
        </button>
      </div>
    </div>
  );
}

export default Header;









