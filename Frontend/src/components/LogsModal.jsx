import { X } from 'lucide-react';
import ConversationLog from './ConversationLog';

function LogsModal({ device, messages, isConnected, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Logs de comunicación</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <ConversationLog device={device} messages={messages} isConnected={isConnected} />
      </div>
    </div>
  );
}

export default LogsModal;
