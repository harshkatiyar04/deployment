import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import ChatWidget from './chat/ChatWidget'

function Layout({ children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const location = useLocation()
  
  // Routes where we want edge-to-edge content without typical dashboard padding
  const isFullScreenRoute = location.pathname === '/chat-demo'

  return (
    <div className="h-[100dvh] bg-slate-50 flex flex-col overflow-hidden">
      <Header onMenuToggle={() => setIsSidebarOpen(prev => !prev)} />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
        <main 
          className={`flex-1 min-h-0 flex flex-col ${isFullScreenRoute ? 'overflow-hidden p-0' : 'overflow-y-auto p-4 md:p-6'}`}
        >
          {children}
        </main>
      </div>
      <ChatWidget />
    </div>
  )
}

export default Layout
