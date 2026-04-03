import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserIcon, LockClosedIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'
import SignupModal from '../components/SignupModal'

function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('password')
  const [isSignupModalOpen, setIsSignupModalOpen] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    // Hardcoded credentials check
    if (username === 'admin' && password === 'password') {
      // Store admin login state
      localStorage.setItem('isAdmin', 'true')
      // Dispatch custom event to notify NotificationContext
      window.dispatchEvent(new Event('adminLogin'))
      // Navigate to dashboard or home page
      navigate('/dashboard')
    } else {
      alert('Invalid credentials. Use admin/password')
    }
  }

  return (
    <div 
      className="min-h-screen relative bg-cover bg-center bg-no-repeat"
      style={{
        backgroundImage: 'url(/LOGIN.jpg)'
      }}
    >
      {/* Top Left - Branding */}
      <div className="absolute top-6 left-6 text-white z-10">
        <h1 
          className="font-bold"
          style={{ 
            fontFamily: "'Oriya MN', sans-serif",
            fontSize: '38px', // Increased by 2 points from ~36px (text-3xl)
            textShadow: `
              2px 2px 0px rgba(0, 0, 0, 0.8),
              4px 4px 0px rgba(0, 0, 0, 0.6),
              6px 6px 0px rgba(0, 0, 0, 0.4),
              8px 8px 0px rgba(0, 0, 0, 0.2),
              10px 10px 20px rgba(0, 0, 0, 0.5),
              0 0 10px rgba(255, 255, 255, 0.3)
            `,
            transform: 'perspective(500px) rotateX(5deg)',
            transformStyle: 'preserve-3d'
          }}
        >
          ZenK
        </h1>
        <p 
          className="text-white mt-1"
          style={{ 
            fontFamily: "'Oriya MN', sans-serif",
            fontSize: '18px', // Increased by 2 points from 16px (text-base)
            textShadow: `
              1px 1px 0px rgba(0, 0, 0, 0.8),
              2px 2px 0px rgba(0, 0, 0, 0.6),
              3px 3px 0px rgba(0, 0, 0, 0.4),
              4px 4px 0px rgba(0, 0, 0, 0.2),
              5px 5px 15px rgba(0, 0, 0, 0.5),
              0 0 8px rgba(255, 255, 255, 0.2)
            `,
            transform: 'perspective(500px) rotateX(5deg)',
            transformStyle: 'preserve-3d'
          }}
        >
          Digital Sponsorship Ecosystem
        </p>
      </div>

      {/* Top Right - Glassmorphism Login Card */}
      <div className="absolute top-6 right-6 z-20">
        <div className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 shadow-2xl p-3">
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            {/* Username/Email Field */}
            <div className="flex flex-col">
              <label htmlFor="username" className="text-white font-bold text-xs mb-1">
                Username / Email
              </label>
              <div className="relative">
                <div className="absolute left-2 top-1/2 transform -translate-y-1/2 z-10 pointer-events-none">
                  <UserIcon className="w-4 h-4 text-white" />
                </div>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-gray-200/90 backdrop-blur-sm border border-gray-300/50 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent w-44 text-sm"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="flex flex-col">
              <label htmlFor="password" className="text-white font-bold text-xs mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute left-2 top-1/2 transform -translate-y-1/2 z-10 pointer-events-none">
                  <LockClosedIcon className="w-4 h-4 text-white" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-gray-200/90 backdrop-blur-sm border border-gray-300/50 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent w-44 text-sm"
                />
              </div>
            </div>

            {/* Login Button */}
            <div className="flex flex-col">
              <label className="text-white font-bold text-xs mb-1 opacity-0 pointer-events-none">
                Login
              </label>
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center w-10 h-9"
                aria-label="Login"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
              </button>
            </div>
          </form>

          {/* Forgot Password & Sign Up Links */}
          <div className="mt-2 text-center space-y-1">
            <a href="#" className="text-blue-300 hover:text-white text-xs underline block">
              Forgot password?
            </a>
            <button
              onClick={() => setIsSignupModalOpen(true)}
              className="text-blue-300 hover:text-white text-xs underline"
            >
              Don't have an account? Sign Up
            </button>
          </div>
        </div>
      </div>

      {/* Signup Modal */}
      <SignupModal 
        isOpen={isSignupModalOpen} 
        onClose={() => setIsSignupModalOpen(false)} 
      />
    </div>
  )
}

export default Login

