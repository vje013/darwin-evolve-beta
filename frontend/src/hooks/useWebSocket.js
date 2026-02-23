import { useEffect, useRef, useState, useCallback } from 'react'
import { getToken } from '../api/client'

/**
 * useWebSocket — connects to a room's WebSocket for real-time messages.
 *
 * Returns:
 *   lastMessage: the most recent WS message received
 *   onlineUsers: list of currently online users
 *   isConnected: whether the WS is open
 */
export default function useWebSocket(roomId) {
  const wsRef = useRef(null)
  const [lastMessage, setLastMessage] = useState(null)
  const [onlineUsers, setOnlineUsers] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef(null)
  const pingIntervalRef = useRef(null)

  const connect = useCallback(() => {
    if (!roomId) return

    const token = getToken()
    if (!token) return

    // Use ws:// for local dev
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const wsUrl = `${protocol}//${host}:8000/ws/${roomId}?token=${token}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      // Ping every 30s to keep alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // Update online users from join/leave events
        if (data.type === 'user_joined' || data.type === 'user_left') {
          if (data.online_users) {
            setOnlineUsers(data.online_users)
          }
        }

        // Forward all messages to consumers
        setLastMessage(data)
      } catch (err) {
        console.error('WS parse error:', err)
      }
    }

    ws.onclose = (event) => {
      setIsConnected(false)
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }

      // Auto-reconnect after 2 seconds (unless intentional close)
      if (event.code !== 4001 && event.code !== 4003) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 2000)
      }
    }

    ws.onerror = () => {
      // onclose will fire after this
    }
  }, [roomId])

  useEffect(() => {
    connect()

    return () => {
      // Cleanup on unmount or roomId change
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  return { lastMessage, onlineUsers, isConnected }
}
