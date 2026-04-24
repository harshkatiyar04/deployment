import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { PersonaProvider } from './contexts/PersonaContext'
import { NotificationProvider } from './contexts/NotificationContext'
import { CartProvider } from './contexts/CartContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Home from './pages/Home'
import SponsorCircleDashboard from './microservices/sponsor-circle/index'
import SponsorLeaderDashboard from './microservices/sponsor-leader/index'
import VendorPortal from './microservices/vendor/index'

// Student Pages
import Resources from './pages/Resources'
import Sessions from './pages/Sessions'
import Progress from './pages/Progress'

// Chat Demo
import ChatDemo from './pages/ChatDemo'

// Sponsor Pages
import Circles from './pages/Circles'
import ImpactLeague from './pages/ImpactLeague'
import Contributions from './pages/Contributions'
import Mentoring from './pages/Mentoring'

// Shared Pages
import Marketplace from './pages/Marketplace'
import VendorDashboardPage from './pages/VendorDashboardPage'
import Analytics from './pages/Analytics'

// Supplier Pages
import Catalog from './pages/Catalog'
import Orders from './pages/Orders'

// Admin Pages
import Users from './pages/Users'
import Suppliers from './pages/Suppliers'
import Safety from './pages/Safety'
import Financial from './pages/Financial'
import ChatBans from './pages/admin/ChatBans'
import SOSQueue from './pages/admin/SOSQueue'

function App() {
  return (
    <PersonaProvider>
      <NotificationProvider>
        <CartProvider>
          <Router>
            <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/login" element={<Login />} />

            {/* Home Page - For Personas and Admins */}
            <Route path="/dashboard/home" element={<Home />} />

            {/* Dashboard */}
            <Route path="/dashboard" element={<Dashboard />} />

            {/* Student Routes */}
            <Route path="/dashboard/resources" element={<Resources />} />
            <Route path="/dashboard/sessions" element={<Sessions />} />
            <Route path="/dashboard/progress" element={<Progress />} />

            {/* Sponsor Routes */}
            <Route path="/dashboard/circles" element={<Circles />} />
            <Route path="/dashboard/impact-league" element={<ImpactLeague />} />
            <Route path="/dashboard/contributions" element={<Contributions />} />
            <Route path="/dashboard/mentoring" element={<Mentoring />} />

            {/* Supplier Routes */}
            <Route path="/dashboard/catalog" element={<Catalog />} />
            <Route path="/dashboard/orders" element={<Orders />} />

            {/* Admin Routes */}
            <Route path="/dashboard/users" element={<Users />} />
            <Route path="/dashboard/suppliers" element={<Suppliers />} />
            <Route path="/dashboard/safety" element={<Safety />} />
            <Route path="/dashboard/financial" element={<Financial />} />
            <Route path="/dashboard/chat-bans" element={<ChatBans />} />
            <Route path="/dashboard/report-queue" element={<SOSQueue />} />

            {/* Shared Routes */}
            <Route path="/dashboard/marketplace" element={<Marketplace />} />
            <Route path="/dashboard/vendor-dashboard" element={<VendorDashboardPage />} />
            <Route path="/dashboard/vendor-portal" element={<VendorPortal />} />
            <Route path="/dashboard/analytics" element={<Analytics />} />

            {/* Chat Testing Route */}
            <Route path="/chat-demo" element={<ChatDemo />} />

            {/* Sponsor Circle Dashboard Microservice */}
            <Route path="/sponsor-circle" element={<SponsorCircleDashboard />} />

            {/* Sponsor Leader Dashboard */}
            <Route path="/sponsor-leader" element={<SponsorLeaderDashboard />} />
            </Routes>
          </Router>
        </CartProvider>
      </NotificationProvider>
    </PersonaProvider>
  )
}

export default App

