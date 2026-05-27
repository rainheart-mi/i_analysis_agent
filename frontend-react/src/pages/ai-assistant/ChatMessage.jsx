function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function ChatMessage({ message }) {
  const isUser = message.type === 'user'

  return (
    <div style={{
      display: 'flex',
      gap: 10,
      alignItems: 'flex-start',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 16
    }}>
      {!isUser && (
        <div style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: '0.9rem',
          flexShrink: 0
        }}>AI</div>
      )}
      <div style={{
        maxWidth: '70%',
        padding: '12px 16px',
        borderRadius: 16,
        background: isUser
          ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
          : '#fff',
        color: isUser ? '#fff' : '#1a1a2e',
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        wordBreak: 'break-word'
      }}>
        <div>{message.content}</div>
        <div style={{
          fontSize: '0.7rem',
          marginTop: 4,
          opacity: 0.7,
          textAlign: 'right'
        }}>{formatTime(message.timestamp)}</div>
      </div>
    </div>
  )
}

export default ChatMessage