import type { ChatMessage } from '../types/llm'

interface Props {
  messages: ChatMessage[]
}

export default function MessageList({ messages }: Props) {
  return (
    <div className="space-y-3">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
            message.role === 'user'
              ? 'ml-auto bg-cyan-400/10 text-cyan-100'
              : 'bg-slate-800/70 text-slate-100'
          }`}
        >
          <div className="mb-1 text-xs uppercase tracking-wide text-slate-400">{message.role}</div>
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>
      ))}
    </div>
  )
}
