import { MessageSquare } from 'lucide-react';

function formatTimestamp(ts) {
  const date = new Date(ts);
  return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function ConversationLog({ device, messages, isConnected }) {
  if (!device) {
    return (
      <div className="conversation-panel">
        <div className="conversation-header">
          <MessageSquare size={18} />
          <span>Conversación</span>
        </div>
        <div className="conversation-empty">
          {isConnected
            ? 'Selecciona un dispositivo activo para ver la conversación.'
            : 'Conéctate al backend para mostrar dispositivos activos.'}
        </div>
      </div>
    );
  }

  return (
    <div className="conversation-panel">
      <div className="conversation-header">
        <MessageSquare size={18} />
        <div>
          <div className="conversation-title">Conversación con</div>
          <div className="conversation-device">{device}</div>
        </div>
      </div>
      <div className="conversation-log">
        {messages.length === 0 ? (
          <div className="conversation-empty">Sin mensajes con este dispositivo todavía.</div>
        ) : (
          [...messages].reverse().map((msg, idx) => {
            const isFromDevice = msg.direction === 'from_device';
            return (
              <div
                key={`${msg.ts}-${idx}`}
                className={`conversation-entry ${isFromDevice ? 'from-device' : 'from-operator'}`}
              >
                <div className="conversation-meta">
                  <span>{formatTimestamp(msg.ts)}</span>
                  {msg.origin && <span className="conversation-origin">{msg.origin}</span>}
                </div>
                <div className="conversation-body">
                  <pre>{JSON.stringify(msg.payload, null, 2)}</pre>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default ConversationLog;
