import { Wifi, WifiOff } from 'lucide-react';

function ConnectionStatus({ isConnected }) {
  return (
    <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
      {isConnected ? (
        <Wifi size={20} />
      ) : (
        <WifiOff size={20} />
      )}
    </div>
  );
}

export default ConnectionStatus;

