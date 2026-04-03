import Header from './Header'
import Sidebar from './Sidebar'
import ChatWidget from './chat/ChatWidget'

function Layout({ children }) {
  return (
    <div className="h-screen bg-slate-50 flex flex-col overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      <ChatWidget />
    </div>
  )
}

export default Layout

