import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { XMarkIcon, DocumentArrowUpIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000'

function SignupModal({ isOpen, onClose }) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('sponsor') // 'sponsor', 'vendor', 'student'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [redirecting, setRedirecting] = useState(false)

  // Common form state
  const [commonFields, setCommonFields] = useState({
    full_name: '',
    mobile: '',
    email: '',
    password: '',
    confirm_password: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    pincode: '',
    country: 'IN'
  })

  // Sponsor-specific state
  const [sponsorFields, setSponsorFields] = useState({
    sponsor_type: 'individual', // 'individual' or 'company'
    pan_number: '',
    company_name: '',
    company_registration_number: '',
    gst_number: '',
    authorized_signatory_name: '',
    authorized_signatory_designation: ''
  })
  const [sponsorFiles, setSponsorFiles] = useState([])

  // Vendor-specific state
  const [vendorFields, setVendorFields] = useState({
    business_name: '',
    business_type: '',
    gst_number: '',
    pan_number: '',
    product_categories: '',
    website: ''
  })
  const [vendorFiles, setVendorFiles] = useState([])

  // Student-specific state
  const [studentFields, setStudentFields] = useState({
    date_of_birth: '',
    school_or_college_name: '',
    grade_or_year: '',
    guardian_name: '',
    guardian_mobile: ''
  })
  const [studentFiles, setStudentFiles] = useState([])

  // Validation errors
  const [errors, setErrors] = useState({})
  
  // Password tooltip state
  const [showPasswordTooltip, setShowPasswordTooltip] = useState(false)

  const handleCommonFieldChange = (e) => {
    const { name, value } = e.target
    setCommonFields(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleSponsorFieldChange = (e) => {
    const { name, value } = e.target
    setSponsorFields(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleVendorFieldChange = (e) => {
    const { name, value } = e.target
    setVendorFields(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleStudentFieldChange = (e) => {
    const { name, value } = e.target
    setStudentFields(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleFileChange = (e, setFiles) => {
    const files = Array.from(e.target.files)
    setFiles(files)
    if (errors.kyc_docs) {
      setErrors(prev => ({ ...prev, kyc_docs: '' }))
    }
  }

  const validateCommonFields = () => {
    const newErrors = {}
    const required = ['full_name', 'mobile', 'email', 'password', 'confirm_password', 'address_line1', 'address_line2', 'city', 'state', 'pincode', 'country']
    required.forEach(field => {
      if (!commonFields[field]?.trim()) {
        newErrors[field] = `${field.replace(/_/g, ' ')} is required`
      }
    })
    if (commonFields.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(commonFields.email)) {
      newErrors.email = 'Invalid email format'
    }
    if (commonFields.mobile && !/^\d{10}$/.test(commonFields.mobile)) {
      newErrors.mobile = 'Mobile must be 10 digits'
    }
    // Password validation
    if (commonFields.password) {
      if (commonFields.password.length < 8) {
        newErrors.password = 'Password must be at least 8 characters long'
      }
      if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(commonFields.password)) {
        newErrors.password = 'Password must contain at least one uppercase letter, one lowercase letter, and one number'
      }
    }
    // Confirm password validation
    if (commonFields.password && commonFields.confirm_password) {
      if (commonFields.password !== commonFields.confirm_password) {
        newErrors.confirm_password = 'Passwords do not match'
      }
    }
    return newErrors
  }

  const validateSponsorFields = () => {
    const newErrors = {}
    if (sponsorFields.sponsor_type === 'individual') {
      if (!sponsorFields.pan_number?.trim()) {
        newErrors.pan_number = 'PAN number is required for individual sponsors'
      }
    } else if (sponsorFields.sponsor_type === 'company') {
      const required = ['company_name', 'company_registration_number', 'gst_number', 'authorized_signatory_name', 'authorized_signatory_designation']
      required.forEach(field => {
        if (!sponsorFields[field]?.trim()) {
          newErrors[field] = `${field.replace(/_/g, ' ')} is required for company sponsors`
        }
      })
    }
    if (sponsorFiles.length === 0) {
      newErrors.kyc_docs = 'At least one KYC document is required'
    }
    return newErrors
  }

  const validateVendorFields = () => {
    const newErrors = {}
    const required = ['business_name', 'business_type', 'gst_number', 'pan_number', 'product_categories', 'website']
    required.forEach(field => {
      if (!vendorFields[field]?.trim()) {
        newErrors[field] = `${field.replace(/_/g, ' ')} is required`
      }
    })
    if (vendorFields.website && !/^https?:\/\/.+/.test(vendorFields.website)) {
      newErrors.website = 'Website must be a valid URL (http:// or https://)'
    }
    if (vendorFiles.length === 0) {
      newErrors.kyc_docs = 'At least one KYC document is required'
    }
    return newErrors
  }

  const validateStudentFields = () => {
    const newErrors = {}
    const required = ['date_of_birth', 'school_or_college_name', 'grade_or_year', 'guardian_name', 'guardian_mobile']
    required.forEach(field => {
      if (!studentFields[field]?.trim()) {
        newErrors[field] = `${field.replace(/_/g, ' ')} is required`
      }
    })
    if (studentFields.guardian_mobile && !/^\d{10}$/.test(studentFields.guardian_mobile)) {
      newErrors.guardian_mobile = 'Guardian mobile must be 10 digits'
    }
    if (studentFields.date_of_birth) {
      const dob = new Date(studentFields.date_of_birth)
      const today = new Date()
      if (dob >= today) {
        newErrors.date_of_birth = 'Date of birth must be in the past'
      }
    }
    if (studentFiles.length === 0) {
      newErrors.kyc_docs = 'At least one KYC document is required'
    }
    return newErrors
  }

  const buildFormData = (persona) => {
    const formData = new FormData()

    // Add common fields (including confirm_password as API requires it)
    Object.keys(commonFields).forEach(key => {
      formData.append(key, commonFields[key])
    })

    if (persona === 'sponsor') {
      Object.keys(sponsorFields).forEach(key => {
        if (sponsorFields[key]) {
          formData.append(key, sponsorFields[key])
        }
      })
      // Add files
      sponsorFiles.forEach((file, index) => {
        formData.append('kyc_docs', file)
      })
    } else if (persona === 'vendor') {
      Object.keys(vendorFields).forEach(key => {
        formData.append(key, vendorFields[key])
      })
      // Add files
      vendorFiles.forEach((file, index) => {
        formData.append('kyc_docs', file)
      })
    } else if (persona === 'student') {
      Object.keys(studentFields).forEach(key => {
        formData.append(key, studentFields[key])
      })
      // Add files
      studentFiles.forEach((file, index) => {
        formData.append('kyc_docs', file)
      })
    }

    return formData
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setRedirecting(false)

    console.log('Form submission started for persona:', activeTab)
    console.log('Common fields:', commonFields)
    console.log('Student fields:', studentFields)
    console.log('Student files:', studentFiles)

    // Validate common fields
    const commonErrors = validateCommonFields()
    console.log('Common validation errors:', commonErrors)
    
    // Validate persona-specific fields
    let personaErrors = {}
    if (activeTab === 'sponsor') {
      personaErrors = validateSponsorFields()
    } else if (activeTab === 'vendor') {
      personaErrors = validateVendorFields()
    } else if (activeTab === 'student') {
      personaErrors = validateStudentFields()
      console.log('Student validation errors:', personaErrors)
    }

    const allErrors = { ...commonErrors, ...personaErrors }
    console.log('All validation errors:', allErrors)
    
    if (Object.keys(allErrors).length > 0) {
      console.log('Validation failed, not calling API')
      setErrors(allErrors)
      return
    }

    console.log('Validation passed, calling API...')
    setLoading(true)
    try {
      const formData = buildFormData(activeTab)
      const endpoint = `${API_BASE_URL}/signup/${activeTab}`
      
      console.log('Submitting signup to:', endpoint)
      console.log('FormData contents:')
      for (let pair of formData.entries()) {
        console.log(pair[0] + ': ' + (pair[1] instanceof File ? pair[1].name : pair[1]))
      }
      
      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      console.log('Signup response:', response.data)

      setSuccess('Sign Up completed successfully!')
      setRedirecting(true)
      
      // Keep modal open to show banner for 3 seconds, then redirect
      setTimeout(() => {
        try {
          navigate('/login')
        } catch (navError) {
          console.error('Navigation error:', navError)
        }
        // Close modal and reset after navigation starts
        setTimeout(() => {
          resetForms()
          onClose()
        }, 100)
      }, 3000) // Show banner for 3 seconds before redirecting
    } catch (err) {
      console.error('Signup API error:', err)
      console.error('Error response:', err.response)
      console.error('Error message:', err.message)
      console.error('Error stack:', err.stack)
      
      let errorMessage = 'An error occurred. Please try again.'
      
      if (!err.response) {
        // Network error or no response
        errorMessage = `Network error: ${err.message}. Please check if the API server is running at ${API_BASE_URL}`
        console.error('No response from server - possible network error or server not running')
      } else if (err.response?.status === 409) {
        errorMessage = 'This email is already registered. Please use a different email or contact support.'
      } else if (err.response?.status === 400 || err.response?.status === 422) {
        // Handle validation errors - could be string or array of error objects
        const detail = err.response.data?.detail
        if (Array.isArray(detail)) {
          // Format validation errors from array
          errorMessage = detail.map(err => {
            if (typeof err === 'string') return err
            if (typeof err === 'object' && err.msg) {
              const field = Array.isArray(err.loc) && err.loc.length > 1 ? err.loc[err.loc.length - 1] : 'field'
              return `${field}: ${err.msg}`
            }
            return JSON.stringify(err)
          }).join(', ')
        } else if (typeof detail === 'string') {
          errorMessage = detail
        } else if (typeof detail === 'object' && detail !== null) {
          // If it's an object, try to extract a message
          errorMessage = detail.msg || detail.message || 'Validation error. Please check all fields.'
        } else {
          errorMessage = 'Validation error. Please check all fields.'
        }
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail
        if (typeof detail === 'string') {
          errorMessage = detail
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(err => {
            if (typeof err === 'string') return err
            if (typeof err === 'object' && err.msg) return err.msg
            return JSON.stringify(err)
          }).join(', ')
        } else {
          errorMessage = 'An error occurred. Please try again.'
        }
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const resetForms = () => {
    setCommonFields({
      full_name: '',
      mobile: '',
      email: '',
      password: '',
      confirm_password: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      pincode: '',
      country: 'IN'
    })
    setShowPasswordTooltip(false)
    setSponsorFields({
      sponsor_type: 'individual',
      pan_number: '',
      company_name: '',
      company_registration_number: '',
      gst_number: '',
      authorized_signatory_name: '',
      authorized_signatory_designation: ''
    })
    setVendorFields({
      business_name: '',
      business_type: '',
      gst_number: '',
      pan_number: '',
      product_categories: '',
      website: ''
    })
    setStudentFields({
      date_of_birth: '',
      school_or_college_name: '',
      grade_or_year: '',
      guardian_name: '',
      guardian_mobile: ''
    })
    setSponsorFiles([])
    setVendorFiles([])
    setStudentFiles([])
    setErrors({})
    setError('')
    setSuccess('')
    setRedirecting(false)
  }

  const handleClose = () => {
    resetForms()
    onClose()
  }

  if (!isOpen) return null

  const renderCommonFields = () => {
    // Password validation checks
    const passwordChecks = {
      minLength: commonFields.password.length >= 8,
      hasUpperCase: /[A-Z]/.test(commonFields.password),
      hasLowerCase: /[a-z]/.test(commonFields.password),
      hasNumber: /\d/.test(commonFields.password)
    }

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">Personal Information</h3>
        
        {/* Full Name - Single Row */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Full Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="full_name"
            value={commonFields.full_name}
            onChange={handleCommonFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.full_name ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Lenin Stark"
          />
          {errors.full_name && <p className="mt-1 text-xs text-red-600">{typeof errors.full_name === 'string' ? errors.full_name : String(errors.full_name)}</p>}
        </div>

        {/* Password and Confirm Password - Together */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              name="password"
              value={commonFields.password}
              onChange={handleCommonFieldChange}
              onFocus={() => setShowPasswordTooltip(true)}
              onBlur={() => setShowPasswordTooltip(false)}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.password ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Enter password"
            />
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password}</p>}
            
            {/* Password Tooltip */}
            {showPasswordTooltip && commonFields.password && (
              <div className="absolute z-10 mt-2 w-64 p-3 bg-white border border-gray-200 rounded-lg shadow-lg">
                <p className="text-sm font-semibold text-gray-900 mb-2">Password Requirements:</p>
                <ul className="space-y-1 text-xs">
                  <li className={`flex items-center gap-2 ${passwordChecks.minLength ? 'text-green-600' : 'text-gray-600'}`}>
                    <span className={passwordChecks.minLength ? 'text-green-600' : 'text-gray-400'}>
                      {passwordChecks.minLength ? '✓' : '○'}
                    </span>
                    At least 8 characters
                  </li>
                  <li className={`flex items-center gap-2 ${passwordChecks.hasUpperCase ? 'text-green-600' : 'text-gray-600'}`}>
                    <span className={passwordChecks.hasUpperCase ? 'text-green-600' : 'text-gray-400'}>
                      {passwordChecks.hasUpperCase ? '✓' : '○'}
                    </span>
                    One uppercase letter
                  </li>
                  <li className={`flex items-center gap-2 ${passwordChecks.hasLowerCase ? 'text-green-600' : 'text-gray-600'}`}>
                    <span className={passwordChecks.hasLowerCase ? 'text-green-600' : 'text-gray-400'}>
                      {passwordChecks.hasLowerCase ? '✓' : '○'}
                    </span>
                    One lowercase letter
                  </li>
                  <li className={`flex items-center gap-2 ${passwordChecks.hasNumber ? 'text-green-600' : 'text-gray-600'}`}>
                    <span className={passwordChecks.hasNumber ? 'text-green-600' : 'text-gray-400'}>
                      {passwordChecks.hasNumber ? '✓' : '○'}
                    </span>
                    One number
                  </li>
                </ul>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              name="confirm_password"
              value={commonFields.confirm_password}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.confirm_password ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Confirm password"
            />
            {errors.confirm_password && <p className="mt-1 text-xs text-red-600">{errors.confirm_password}</p>}
          </div>
        </div>

        {/* Email and Mobile - Together */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              name="email"
              value={commonFields.email}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.email ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="leninstark@gmail.com"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mobile <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="mobile"
              value={commonFields.mobile}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.mobile ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="9003151716"
              maxLength="10"
            />
            {errors.mobile && <p className="mt-1 text-xs text-red-600">{errors.mobile}</p>}
          </div>
        </div>

        {/* Address Line 1 and Address Line 2 - Together */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address Line 1 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="address_line1"
              value={commonFields.address_line1}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.address_line1 ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="123 Main Street"
            />
            {errors.address_line1 && <p className="mt-1 text-xs text-red-600">{errors.address_line1}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address Line 2 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="address_line2"
              value={commonFields.address_line2}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.address_line2 ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Apartment 4B"
            />
            {errors.address_line2 && <p className="mt-1 text-xs text-red-600">{errors.address_line2}</p>}
          </div>
        </div>

        {/* City and Pincode - Together */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              City <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="city"
              value={commonFields.city}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.city ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Chennai"
            />
            {errors.city && <p className="mt-1 text-xs text-red-600">{errors.city}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pincode <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="pincode"
              value={commonFields.pincode}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.pincode ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="600001"
            />
            {errors.pincode && <p className="mt-1 text-xs text-red-600">{errors.pincode}</p>}
          </div>
        </div>

        {/* State and Country - Together */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              State <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="state"
              value={commonFields.state}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.state ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Tamil Nadu"
            />
            {errors.state && <p className="mt-1 text-xs text-red-600">{errors.state}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Country <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="country"
              value={commonFields.country}
              onChange={handleCommonFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.country ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="IN"
            />
            {errors.country && <p className="mt-1 text-xs text-red-600">{errors.country}</p>}
          </div>
        </div>
      </div>
    )
  }

  const renderSponsorFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">Sponsor Information</h3>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Sponsor Type <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-4">
          <label className="flex items-center">
            <input
              type="radio"
              name="sponsor_type"
              value="individual"
              checked={sponsorFields.sponsor_type === 'individual'}
              onChange={handleSponsorFieldChange}
              className="mr-2"
            />
            Individual
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="sponsor_type"
              value="company"
              checked={sponsorFields.sponsor_type === 'company'}
              onChange={handleSponsorFieldChange}
              className="mr-2"
            />
            Company
          </label>
        </div>
      </div>

      {sponsorFields.sponsor_type === 'individual' ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PAN Number <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="pan_number"
            value={sponsorFields.pan_number}
            onChange={handleSponsorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.pan_number ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="ABCDE1234F"
            maxLength="10"
          />
          {errors.pan_number && <p className="mt-1 text-xs text-red-600">{errors.pan_number}</p>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="company_name"
              value={sponsorFields.company_name}
              onChange={handleSponsorFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.company_name ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="ABC Corp Ltd"
            />
            {errors.company_name && <p className="mt-1 text-xs text-red-600">{errors.company_name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company Registration Number <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="company_registration_number"
              value={sponsorFields.company_registration_number}
              onChange={handleSponsorFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.company_registration_number ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="U12345TN2020PTC123456"
            />
            {errors.company_registration_number && <p className="mt-1 text-xs text-red-600">{errors.company_registration_number}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              GST Number <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="gst_number"
              value={sponsorFields.gst_number}
              onChange={handleSponsorFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.gst_number ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="27ABCDE1234F1Z5"
            />
            {errors.gst_number && <p className="mt-1 text-xs text-red-600">{errors.gst_number}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Authorized Signatory Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="authorized_signatory_name"
              value={sponsorFields.authorized_signatory_name}
              onChange={handleSponsorFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.authorized_signatory_name ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="John Doe"
            />
            {errors.authorized_signatory_name && <p className="mt-1 text-xs text-red-600">{errors.authorized_signatory_name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Authorized Signatory Designation <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="authorized_signatory_designation"
              value={sponsorFields.authorized_signatory_designation}
              onChange={handleSponsorFieldChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.authorized_signatory_designation ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Director"
            />
            {errors.authorized_signatory_designation && <p className="mt-1 text-xs text-red-600">{errors.authorized_signatory_designation}</p>}
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          KYC Documents <span className="text-red-500">*</span>
        </label>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
          <input
            type="file"
            multiple
            onChange={(e) => handleFileChange(e, setSponsorFiles)}
            className="hidden"
            id="sponsor-kyc-files"
            accept=".pdf,.jpg,.jpeg,.png"
          />
          <label
            htmlFor="sponsor-kyc-files"
            className="cursor-pointer flex flex-col items-center justify-center"
          >
            <DocumentArrowUpIcon className="w-8 h-8 text-gray-400 mb-2" />
            <span className="text-sm text-gray-600">Click to upload KYC documents</span>
            <span className="text-xs text-gray-500 mt-1">PDF, JPG, PNG (Multiple files allowed)</span>
          </label>
        </div>
        {sponsorFiles.length > 0 && (
          <div className="mt-2">
            <p className="text-sm text-gray-600">Selected files:</p>
            <ul className="list-disc list-inside text-xs text-gray-500 mt-1">
              {sponsorFiles.map((file, idx) => (
                <li key={idx}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
        {errors.kyc_docs && <p className="mt-1 text-xs text-red-600">{errors.kyc_docs}</p>}
      </div>
    </div>
  )

  const renderVendorFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">Vendor Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="business_name"
            value={vendorFields.business_name}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.business_name ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="ABC Trading Co."
          />
          {errors.business_name && <p className="mt-1 text-xs text-red-600">{errors.business_name}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Type <span className="text-red-500">*</span>
          </label>
          <select
            name="business_type"
            value={vendorFields.business_type}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.business_type ? 'border-red-300' : 'border-gray-300'
            }`}
          >
            <option value="">Select business type</option>
            <option value="Retail">Retail</option>
            <option value="Wholesale">Wholesale</option>
            <option value="Manufacturing">Manufacturing</option>
            <option value="Service Provider">Service Provider</option>
            <option value="E-commerce">E-commerce</option>
          </select>
          {errors.business_type && <p className="mt-1 text-xs text-red-600">{errors.business_type}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            GST Number <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="gst_number"
            value={vendorFields.gst_number}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.gst_number ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="27ABCDE1234F1Z5"
          />
          {errors.gst_number && <p className="mt-1 text-xs text-red-600">{errors.gst_number}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PAN Number <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="pan_number"
            value={vendorFields.pan_number}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.pan_number ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="ABCDE1234F"
            maxLength="10"
          />
          {errors.pan_number && <p className="mt-1 text-xs text-red-600">{errors.pan_number}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Product Categories <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="product_categories"
            value={vendorFields.product_categories}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.product_categories ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Electronics, Clothing, Home Appliances"
          />
          {errors.product_categories && <p className="mt-1 text-xs text-red-600">{errors.product_categories}</p>}
          <p className="mt-1 text-xs text-gray-500">Comma-separated list</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Website <span className="text-red-500">*</span>
          </label>
          <input
            type="url"
            name="website"
            value={vendorFields.website}
            onChange={handleVendorFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.website ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="https://abctrading.com"
          />
          {errors.website && <p className="mt-1 text-xs text-red-600">{errors.website}</p>}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          KYC Documents <span className="text-red-500">*</span>
        </label>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
          <input
            type="file"
            multiple
            onChange={(e) => handleFileChange(e, setVendorFiles)}
            className="hidden"
            id="vendor-kyc-files"
            accept=".pdf,.jpg,.jpeg,.png"
          />
          <label
            htmlFor="vendor-kyc-files"
            className="cursor-pointer flex flex-col items-center justify-center"
          >
            <DocumentArrowUpIcon className="w-8 h-8 text-gray-400 mb-2" />
            <span className="text-sm text-gray-600">Click to upload KYC documents</span>
            <span className="text-xs text-gray-500 mt-1">PDF, JPG, PNG (Multiple files allowed)</span>
          </label>
        </div>
        {vendorFiles.length > 0 && (
          <div className="mt-2">
            <p className="text-sm text-gray-600">Selected files:</p>
            <ul className="list-disc list-inside text-xs text-gray-500 mt-1">
              {vendorFiles.map((file, idx) => (
                <li key={idx}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
        {errors.kyc_docs && <p className="mt-1 text-xs text-red-600">{errors.kyc_docs}</p>}
      </div>
    </div>
  )

  const renderStudentFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">Student Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date of Birth <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            name="date_of_birth"
            value={studentFields.date_of_birth}
            onChange={handleStudentFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.date_of_birth ? 'border-red-300' : 'border-gray-300'
            }`}
          />
          {errors.date_of_birth && <p className="mt-1 text-xs text-red-600">{errors.date_of_birth}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            School/College Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="school_or_college_name"
            value={studentFields.school_or_college_name}
            onChange={handleStudentFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.school_or_college_name ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="ABC High School"
          />
          {errors.school_or_college_name && <p className="mt-1 text-xs text-red-600">{errors.school_or_college_name}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Grade/Year <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="grade_or_year"
            value={studentFields.grade_or_year}
            onChange={handleStudentFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.grade_or_year ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="10th Grade or Year 2"
          />
          {errors.grade_or_year && <p className="mt-1 text-xs text-red-600">{errors.grade_or_year}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Guardian Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="guardian_name"
            value={studentFields.guardian_name}
            onChange={handleStudentFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.guardian_name ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Rajesh Kumar"
          />
          {errors.guardian_name && <p className="mt-1 text-xs text-red-600">{errors.guardian_name}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Guardian Mobile <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="guardian_mobile"
            value={studentFields.guardian_mobile}
            onChange={handleStudentFieldChange}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.guardian_mobile ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="9876543212"
            maxLength="10"
          />
          {errors.guardian_mobile && <p className="mt-1 text-xs text-red-600">{errors.guardian_mobile}</p>}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          KYC Documents <span className="text-red-500">*</span>
        </label>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
          <input
            type="file"
            multiple
            onChange={(e) => handleFileChange(e, setStudentFiles)}
            className="hidden"
            id="student-kyc-files"
            accept=".pdf,.jpg,.jpeg,.png"
          />
          <label
            htmlFor="student-kyc-files"
            className="cursor-pointer flex flex-col items-center justify-center"
          >
            <DocumentArrowUpIcon className="w-8 h-8 text-gray-400 mb-2" />
            <span className="text-sm text-gray-600">Click to upload KYC documents</span>
            <span className="text-xs text-gray-500 mt-1">PDF, JPG, PNG (Multiple files allowed)</span>
          </label>
        </div>
        {studentFiles.length > 0 && (
          <div className="mt-2">
            <p className="text-sm text-gray-600">Selected files:</p>
            <ul className="list-disc list-inside text-xs text-gray-500 mt-1">
              {studentFiles.map((file, idx) => (
                <li key={idx}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
        {errors.kyc_docs && <p className="mt-1 text-xs text-red-600">{errors.kyc_docs}</p>}
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      ></div>
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div 
          className="relative w-full max-w-4xl rounded-xl bg-white shadow-lg border border-gray-200 max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Sign Up</h2>
              <p className="text-sm text-gray-500 mt-1">Create your account to get started</p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-500 p-2 hover:bg-gray-100 rounded-lg"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 px-6">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab('sponsor')}
                className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'sponsor'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Sponsor
              </button>
              <button
                onClick={() => setActiveTab('vendor')}
                className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'vendor'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Vendor/Supplier
              </button>
              <button
                onClick={() => setActiveTab('student')}
                className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'student'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Student
              </button>
            </div>
          </div>

          {/* Modal Body */}
          <form onSubmit={handleSubmit} className="p-6">
            {/* Error/Success Messages */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
            {success && (
              <div className="mb-4 p-4 bg-green-50 border-2 border-green-500 rounded-xl shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    <CheckCircleIcon className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-base font-semibold text-green-800">{success}</p>
                    {redirecting && (
                      <p className="text-sm text-green-700 mt-1">Redirecting to Login...</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Common Fields */}
            {renderCommonFields()}

            {/* Persona-Specific Fields */}
            <div className="mt-6">
              {activeTab === 'sponsor' && renderSponsorFields()}
              {activeTab === 'vendor' && renderVendorFields()}
              {activeTab === 'student' && renderStudentFields()}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 mt-8 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loading}
              >
                {loading ? 'Submitting...' : 'Submit Signup'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default SignupModal

