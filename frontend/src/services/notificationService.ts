import { api } from '../api/client'

export interface NotificationItem {
  id: number
  title: string
  message: string
  level: string
  is_read: boolean
  created_at: string
}

export const notificationService = {
  async list(): Promise<NotificationItem[]> {
    const response = await api.get<NotificationItem[]>('/notifications')
    return response.data
  },
  async markRead(id: number) {
    await api.post(`/notifications/${id}/read`)
  },
  async remove(id: number) {
    await api.delete(`/notifications/${id}`)
  },
}
