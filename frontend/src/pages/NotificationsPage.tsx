import { Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { notificationService, type NotificationItem } from '../services/notificationService'

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([])

  async function load() {
    const list = await notificationService.list()
    setItems(list)
  }

  useEffect(() => {
    load()
  }, [])

  async function markRead(id: number) {
    await notificationService.markRead(id)
    load()
  }

  async function remove(id: number) {
    await notificationService.remove(id)
    setItems((prev) => prev.filter((i) => i.id !== id))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Notifications</h1>
      {items.length === 0 ? (
        <div className="glass rounded-3xl p-10 text-center text-sm text-slate-400">No notifications.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className={`glass flex items-start justify-between gap-3 rounded-2xl p-4 ${item.is_read ? 'opacity-70' : ''}`}
            >
              <div>
                <div className="text-sm font-medium text-slate-100">{item.title}</div>
                <div className="text-xs text-slate-400">{item.message}</div>
                <div className="mt-1 text-[10px] uppercase text-slate-500">{item.created_at}</div>
              </div>
              <div className="flex gap-2">
                {!item.is_read && (
                  <button onClick={() => markRead(item.id)} className="rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-300">
                    Mark read
                  </button>
                )}
                <button onClick={() => remove(item.id)} className="rounded-lg p-2 text-slate-400 hover:text-red-300">
                  <Trash2 size={14} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
