'use client'

import { useState } from 'react'
import ProfileGenerationWizard from './ProfileGenerationWizard'

interface BrokerProfile {
  id: string
  name: string
  broker_email_domain: string
  status: 'active' | 'draft' | 'archived'
  confidence_score: number
  created_at: string
  last_used: string
  usage_count: number
  field_mappings: Record<string, string>
  auto_generated: boolean
}

interface ProfileCreationData {
  name: string
  domain: string
  profile_id: string
  confidence: number
  field_mappings: Record<string, string>
  auto_generated: boolean
  created_at: string
  validation_rules: {
    required: string[]
  }
}

interface BrokerProfileManagerProps {
  onProfileSelect?: (profile: BrokerProfile) => void
  onCreateNew?: () => void
}

const mockProfiles: BrokerProfile[] = [
  {
    id: 'lucky_gas',
    name: 'Lucky Gas Fleet Profile',
    broker_email_domain: 'luckygas.com.mx',
    status: 'active',
    confidence_score: 0.95,
    created_at: '2024-09-01',
    last_used: '2024-09-15',
    usage_count: 47,
    field_mappings: {
      'marca': 'brand',
      'submarca': 'model', 
      'año': 'year',
      'descripción': 'description',
      'uso': 'use'
    },
    auto_generated: false
  },
  {
    id: 'axa_seguros',
    name: 'AXA Seguros Profile',
    broker_email_domain: 'axa.com.mx',
    status: 'active',
    confidence_score: 0.89,
    created_at: '2024-09-10',
    last_used: '2024-09-14',
    usage_count: 12,
    field_mappings: {
      'Brand': 'brand',
      'Model': 'model',
      'Year': 'year',
      'Description': 'description',
      'Coverage': 'coverage_type'
    },
    auto_generated: true
  },
  {
    id: 'generic_draft',
    name: 'Auto-detected Profile (Needs Review)',
    broker_email_domain: 'newbroker.com',
    status: 'draft',
    confidence_score: 0.72,
    created_at: '2024-09-15',
    last_used: '2024-09-15',
    usage_count: 1,
    field_mappings: {
      'Vehicle Make': 'brand',
      'Vehicle Model': 'model',
      'Model Year': 'year'
    },
    auto_generated: true
  }
]

export default function BrokerProfileManager({ onProfileSelect, onCreateNew }: BrokerProfileManagerProps) {
  const [profiles, setProfiles] = useState<BrokerProfile[]>(mockProfiles)
  const [selectedProfile, setSelectedProfile] = useState<BrokerProfile | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'draft' | 'archived'>('all')
  const [showDetails, setShowDetails] = useState(false)
  const [showWizard, setShowWizard] = useState(false)

  const filteredProfiles = profiles.filter(profile => {
    const matchesSearch = profile.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         profile.broker_email_domain.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || profile.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const getStatusBadge = (status: BrokerProfile['status']) => {
    const styles = {
      active: 'bg-green-100 text-green-800 border-green-200',
      draft: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      archived: 'bg-gray-100 text-gray-800 border-gray-200'
    }
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getConfidenceBadge = (score: number) => {
    const level = score >= 0.9 ? 'high' : score >= 0.7 ? 'medium' : 'low'
    const styles = {
      high: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800', 
      low: 'bg-red-100 text-red-800'
    }
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${styles[level]}`}>
        {(score * 100).toFixed(0)}%
      </span>
    )
  }

  const handleProfileClick = (profile: BrokerProfile) => {
    setSelectedProfile(profile)
    setShowDetails(true)
    if (onProfileSelect) {
      onProfileSelect(profile)
    }
  }

  const handleApproveProfile = (profileId: string) => {
    setProfiles(prev => prev.map(p => 
      p.id === profileId ? { ...p, status: 'active' as const } : p
    ))
  }

  const handleCreateProfile = (profileData: ProfileCreationData) => {
    const newProfile: BrokerProfile = {
      id: profileData.profile_id,
      name: profileData.name,
      broker_email_domain: profileData.domain,
      status: 'draft',
      confidence_score: profileData.confidence,
      created_at: profileData.created_at,
      last_used: profileData.created_at,
      usage_count: 0,
      field_mappings: profileData.field_mappings,
      auto_generated: profileData.auto_generated
    }

    setProfiles(prev => [...prev, newProfile])
    setShowWizard(false)
    console.log('Created new profile:', newProfile)
  }

  const handleCreateNewClick = () => {
    if (onCreateNew) {
      onCreateNew()
    } else {
      setShowWizard(true)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-medium text-gray-900">
              🏢 Broker Profiles
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Manage broker-specific data transformation rules
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleCreateNewClick}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
            >
              + Create New
            </button>
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700"
            >
              🤖 Auto-Generate
            </button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Search profiles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="draft">Needs Review</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      <div className="p-6">
        {/* Profile List */}
        <div className="space-y-4">
          {filteredProfiles.map((profile) => (
            <div
              key={profile.id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => handleProfileClick(profile)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-medium text-gray-900">{profile.name}</h3>
                    {profile.auto_generated && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        🤖 Auto-generated
                      </span>
                    )}
                    {getStatusBadge(profile.status)}
                  </div>
                  
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>📧 Domain: <span className="font-mono">{profile.broker_email_domain}</span></p>
                    <p>📊 Fields: {Object.keys(profile.field_mappings).length} mappings</p>
                    <p>📈 Used: {profile.usage_count} times • Last: {profile.last_used}</p>
                  </div>
                </div>

                <div className="text-right space-y-2">
                  {getConfidenceBadge(profile.confidence_score)}
                  {profile.status === 'draft' && (
                    <div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleApproveProfile(profile.id)
                        }}
                        className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700"
                      >
                        ✓ Approve
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredProfiles.length === 0 && (
          <div className="text-center py-8">
            <div className="text-4xl mb-4">📭</div>
            <p className="text-gray-500">No profiles found matching your criteria</p>
          </div>
        )}

        {/* Profile Details Modal */}
        {showDetails && selectedProfile && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-medium">{selectedProfile.name}</h3>
                  <button
                    onClick={() => setShowDetails(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Profile Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Broker Domain</label>
                    <p className="text-sm text-gray-900 font-mono">{selectedProfile.broker_email_domain}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Status</label>
                    <div className="mt-1">{getStatusBadge(selectedProfile.status)}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Confidence Score</label>
                    <div className="mt-1">{getConfidenceBadge(selectedProfile.confidence_score)}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Usage Count</label>
                    <p className="text-sm text-gray-900">{selectedProfile.usage_count} times</p>
                  </div>
                </div>

                {/* Field Mappings */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Field Mappings</h4>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="space-y-2">
                      {Object.entries(selectedProfile.field_mappings).map(([source, target]) => (
                        <div key={source} className="flex items-center justify-between text-sm">
                          <span className="font-mono text-blue-600">&quot;{source}&quot;</span>
                          <span className="text-gray-400">→</span>
                          <span className="font-mono text-green-600">{target}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                  {selectedProfile.status === 'draft' && (
                    <button
                      onClick={() => handleApproveProfile(selectedProfile.id)}
                      className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700"
                    >
                      ✓ Approve Profile
                    </button>
                  )}
                  <button
                    onClick={() => setShowDetails(false)}
                    className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-md hover:bg-gray-700"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {profiles.filter(p => p.status === 'active').length}
              </div>
              <div className="text-xs text-gray-500">Active</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-600">
                {profiles.filter(p => p.status === 'draft').length}
              </div>
              <div className="text-xs text-gray-500">Need Review</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {profiles.filter(p => p.auto_generated).length}
              </div>
              <div className="text-xs text-gray-500">Auto-generated</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">
                {profiles.reduce((sum, p) => sum + p.usage_count, 0)}
              </div>
              <div className="text-xs text-gray-500">Total Uses</div>
            </div>
          </div>
        </div>

        {/* Profile Generation Wizard */}
        {showWizard && (
          <ProfileGenerationWizard
            onComplete={handleCreateProfile}
            onCancel={() => setShowWizard(false)}
          />
        )}
      </div>
    </div>
  )
}