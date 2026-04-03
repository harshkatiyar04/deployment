import { usePersona } from '../contexts/PersonaContext'
import Layout from '../components/Layout'
import StudentDashboard from './dashboards/StudentDashboard'
import SponsorDashboard from './dashboards/SponsorDashboard'
import SupplierDashboard from './dashboards/SupplierDashboard'
import AdminDashboard from './dashboards/AdminDashboard'

function Dashboard() {
  const { isStudent, isSponsor, isSupplier, isAdmin } = usePersona()

  const renderDashboard = () => {
    if (isStudent) return <StudentDashboard />
    if (isSponsor) return <SponsorDashboard />
    if (isSupplier) return <SupplierDashboard />
    if (isAdmin) return <AdminDashboard />
    return <SponsorDashboard /> // Default
  }

  return (
    <Layout>
      {renderDashboard()}
    </Layout>
  )
}

export default Dashboard

