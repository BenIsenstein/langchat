import { useRef, useState } from 'react'
import './App.css'

interface Message {
  id: string
  role: "user" | "ai"
  content: string
}

interface NewStreamResponse {
  stream_id: string
}

interface StreamingMessagePayload {
  message_id: string
  name: string | undefined
  type: "text" | "tool_call_chunk"
  data: string | undefined
}

function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

function jsonDeepCopy<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [formRef, setFormRef] = useState<HTMLFormElement | null>(null)
  const chatId = useRef(uuid())

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: uuid(),
      role: "user",
      content: input.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    // Send the user message to the backend
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/chats/${chatId.current}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage.content }),
      })

      const newStream: NewStreamResponse = await response.json()

      // Open SSE connection to receive AI response
      const eventSource = new EventSource(`${import.meta.env.VITE_BACKEND_URL}/chats/${chatId.current}/streams/${newStream.stream_id}`)

      eventSource.addEventListener("closedConnection", () => {
        eventSource.close()
        setIsLoading(false)
      })

      eventSource.onmessage = (event) => {
        const payload: StreamingMessagePayload = JSON.parse(event.data)
        // @ts-expect-error Leaving these unused payload vars for future me
        const { type, data, name, message_id } = payload
        
        setMessages(prev => {
          const updated = jsonDeepCopy(prev)

          if (updated.length > 0 && updated[updated.length - 1].id === message_id) {
            // Append to the last message
            updated[updated.length - 1].content += data || ""
          } else {
            // Start a new message
            updated.push({
              id: message_id,
              role: "ai",
              content: data || "",
            })
          }

          return updated
        })
      }

      eventSource.onerror = (err) => {
        console.error("EventSource failed:", err)
        // opting to not close the event source or set loading to false every time.
        // more useful tokens may still come in,
        // and the "closedConnection" event from the backend will end the stream eventually.
        
        if ((err as MessageEvent).data.includes("stream not found")) {
          eventSource.close()
          setIsLoading(false)
        }
      }
    } catch (error) { 
      console.error("Failed to send message:", error)
    }
  }

  return (
    <div className="flex flex-col h-[90vh] max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">LangChat</h1>
      <div className="flex flex-col overflow-y-auto mb-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`p-3 rounded-lg ${msg.role === "user" ? "bg-blue-100 self-end" : "bg-gray-200 self-start"}`}>
            <p className="whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}
      </div>
      <form ref={setFormRef} onSubmit={onSubmit} className="flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyUp={(e) => { if (e.key === "Enter") formRef?.submit() }}
          className="flex-1 p-2 border border-gray-300 rounded-lg"
          placeholder="Type your message..."
          autoFocus
          disabled={isLoading}
        />
      </form>
    </div>
  )
}

export default App
