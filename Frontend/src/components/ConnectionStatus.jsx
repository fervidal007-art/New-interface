import { Wifi, WifiOff } from 'lucide-react';

function ConnectionStatus({ isConnected }) {
  return (
    <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
      {isConnected ? (
        <>
          <Wifi size={16} />
          <span>Conectado</span>
        </>
      ) : (
        <>
          <WifiOff size={16} />
          <span>Desconectado</span>
        </>
      )}
    </div>
  );
}

export default ConnectionStatus;

