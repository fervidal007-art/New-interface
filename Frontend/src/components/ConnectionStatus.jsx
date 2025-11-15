import { Wifi, WifiOff, Zap } from 'lucide-react';

function ConnectionStatus({ isConnected, onConnect }) {
  return (
    <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
      {isConnected ? (
        <>
          <Wifi size={16} />
          <span>Conectado</span>
        </>
      ) : (
        <div className="disconnected-content">
          <div className="disconnected-info">
            <WifiOff size={16} />
            <span>Desconectado</span>
          </div>
          <button onClick={onConnect} className="connect-btn">
            <Zap size={14} />
            Encender
          </button>
        </div>
      )}
    </div>
  );
}

export default ConnectionStatus;

