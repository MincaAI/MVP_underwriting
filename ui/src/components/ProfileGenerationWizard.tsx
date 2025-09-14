'use client'

import { useState } from 'react'

interface FieldMapping {
  source_field: string
  target_field: string
  confidence: number
  auto_detected: boolean
}

interface ProfileGenerationData {
  broker_domain: string
  sample_headers: string[]
  suggested_mappings: FieldMapping[]
  confidence_score: number
}

interface ProfileCreationResult {
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

interface ProfileGenerationWizardProps {
  onComplete: (profile: ProfileCreationResult) => void
  onCancel: () => void
}

const CANONICAL_FIELDS = [
  { key: 'brand', label: 'Brand/Marca', description: 'Vehicle manufacturer' },
  { key: 'model', label: 'Model/Submarca', description: 'Vehicle model' },
  { key: 'year', label: 'Year/Año', description: 'Model year' },
  { key: 'description', label: 'Description/Descripción', description: 'Full vehicle description' },
  { key: 'use', label: 'Use/Uso', description: 'Vehicle usage (particular, commercial)' },
  { key: 'body', label: 'Body/Carrocería', description: 'Body type (sedan, suv, etc.)' },
  { key: 'license_plate', label: 'License Plate/Placa', description: 'Vehicle registration plate' },
  { key: 'vin', label: 'VIN/Serie', description: 'Vehicle identification number' },
  { key: 'insured_value', label: 'Insured Value/Valor', description: 'Insurance value' },
  { key: 'premium', label: 'Premium/Prima', description: 'Insurance premium' }
]

// Mock LLM-generated profile data
const mockProfileGeneration: ProfileGenerationData = {
  broker_domain: 'newbroker.com',
  sample_headers: [
    'Vehicle Make',
    'Vehicle Model', 
    'Model Year',
    'Full Description',
    'Usage Type',
    'Body Style',
    'License Number',
    'Coverage Amount'
  ],
  suggested_mappings: [
    { source_field: 'Vehicle Make', target_field: 'brand', confidence: 0.95, auto_detected: true },
    { source_field: 'Vehicle Model', target_field: 'model', confidence: 0.95, auto_detected: true },
    { source_field: 'Model Year', target_field: 'year', confidence: 0.93, auto_detected: true },
    { source_field: 'Full Description', target_field: 'description', confidence: 0.88, auto_detected: true },
    { source_field: 'Usage Type', target_field: 'use', confidence: 0.82, auto_detected: true },
    { source_field: 'Body Style', target_field: 'body', confidence: 0.79, auto_detected: true },
    { source_field: 'License Number', target_field: 'license_plate', confidence: 0.91, auto_detected: true },
    { source_field: 'Coverage Amount', target_field: 'insured_value', confidence: 0.76, auto_detected: true }
  ],
  confidence_score: 0.86
}

export default function ProfileGenerationWizard({ onComplete, onCancel }: ProfileGenerationWizardProps) {
  const [step, setStep] = useState<'review' | 'mapping' | 'validation'>('review')
  const [profileData, setProfileData] = useState<ProfileGenerationData>(mockProfileGeneration)
  const [mappings, setMappings] = useState<FieldMapping[]>(profileData.suggested_mappings)
  const [profileName, setProfileName] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  const handleMappingChange = (index: number, newTargetField: string) => {
    const updatedMappings = [...mappings]
    updatedMappings[index].target_field = newTargetField
    updatedMappings[index].auto_detected = false // Mark as manually edited
    setMappings(updatedMappings)
  }

  const removeMappingItem = (index: number) => {
    setMappings(mappings.filter((_, i) => i !== index))
  }

  const addMapping = () => {
    setMappings([...mappings, {
      source_field: '',
      target_field: '',
      confidence: 0.50,
      auto_detected: false
    }])
  }

  const getConfidenceBadge = (confidence: number) => {
    const level = confidence >= 0.9 ? 'high' : confidence >= 0.7 ? 'medium' : 'low'
    const styles = {
      high: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-red-100 text-red-800'
    }
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${styles[level]}`}>
        {(confidence * 100).toFixed(0)}%
      </span>
    )
  }

  const handleComplete = () => {
    const finalProfile = {
      name: profileName || `Auto-generated Profile (${profileData.broker_domain})`,
      domain: profileData.broker_domain,
      profile_id: `${profileData.broker_domain.replace('.', '_')}_auto.yaml`,
      confidence: profileData.confidence_score,
      field_mappings: Object.fromEntries(
        mappings.map(m => [m.source_field, m.target_field])
      ),
      auto_generated: true,
      created_at: new Date().toISOString(),
      validation_rules: {
        required: ['brand', 'model', 'year', 'description']
      }
    }

    onComplete(finalProfile)
  }

  const simulateGeneration = async () => {
    setIsGenerating(true)
    
    // Simulate LLM processing
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Update confidence scores to show "improvement"
    const updatedMappings = mappings.map(m => ({
      ...m,
      confidence: Math.min(m.confidence + 0.05, 0.98)
    }))
    
    setMappings(updatedMappings)
    setProfileData(prev => ({
      ...prev,
      confidence_score: Math.min(prev.confidence_score + 0.03, 0.95)
    }))
    
    setIsGenerating(false)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-medium">🤖 Auto-Generate Broker Profile</h3>
              <p className="text-sm text-gray-500 mt-1">
                AI-assisted profile generation from detected field patterns
              </p>
            </div>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          {/* Step indicators */}
          <div className="mt-4">
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 ${step === 'review' ? 'text-blue-600' : 'text-gray-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                  step === 'review' ? 'bg-blue-100' : 'bg-gray-100'
                }`}>1</div>
                <span className="text-sm">Review Detection</span>
              </div>
              <div className="flex-1 h-px bg-gray-200"></div>
              <div className={`flex items-center space-x-2 ${step === 'mapping' ? 'text-blue-600' : 'text-gray-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                  step === 'mapping' ? 'bg-blue-100' : 'bg-gray-100'
                }`}>2</div>
                <span className="text-sm">Edit Mappings</span>
              </div>
              <div className="flex-1 h-px bg-gray-200"></div>
              <div className={`flex items-center space-x-2 ${step === 'validation' ? 'text-blue-600' : 'text-gray-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                  step === 'validation' ? 'bg-blue-100' : 'bg-gray-100'
                }`}>3</div>
                <span className="text-sm">Validate & Save</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Step 1: Review AI Detection */}
          {step === 'review' && (
            <div className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-2">🔍 AI Detection Results</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-blue-700">Broker Domain:</span>
                    <span className="font-mono ml-2">{profileData.broker_domain}</span>
                  </div>
                  <div>
                    <span className="text-blue-700">Overall Confidence:</span>
                    <span className="ml-2">{getConfidenceBadge(profileData.confidence_score)}</span>
                  </div>
                  <div>
                    <span className="text-blue-700">Fields Detected:</span>
                    <span className="ml-2">{profileData.sample_headers.length}</span>
                  </div>
                  <div>
                    <span className="text-blue-700">Auto-mapped:</span>
                    <span className="ml-2">{mappings.filter(m => m.auto_detected).length}</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">Detected Headers</h4>
                <div className="grid grid-cols-2 gap-2">
                  {profileData.sample_headers.map((header, index) => (
                    <div key={index} className="bg-gray-50 rounded px-3 py-2 text-sm font-mono">
                      &quot;{header}&quot;
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">Suggested Mappings</h4>
                <div className="space-y-2">
                  {mappings.slice(0, 5).map((mapping, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-sm text-blue-600">&quot;{mapping.source_field}&quot;</span>
                        <span className="text-gray-400">→</span>
                        <span className="font-mono text-sm text-green-600">{mapping.target_field}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        {mapping.auto_detected && <span className="text-xs text-blue-500">🤖 Auto</span>}
                        {getConfidenceBadge(mapping.confidence)}
                      </div>
                    </div>
                  ))}
                  {mappings.length > 5 && (
                    <p className="text-sm text-gray-500 text-center">
                      + {mappings.length - 5} more mappings
                    </p>
                  )}
                </div>
              </div>

              <div className="flex justify-between space-x-3">
                <div className="flex space-x-2">
                  <button
                    onClick={simulateGeneration}
                    disabled={isGenerating}
                    className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:bg-gray-400"
                  >
                    {isGenerating ? '🔄 Re-analyzing...' : '🧠 Improve with AI'}
                  </button>
                </div>
                <button
                  onClick={() => setStep('mapping')}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
                >
                  Next: Edit Mappings →
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Edit Mappings */}
          {step === 'mapping' && (
            <div className="space-y-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Field Mappings</h4>
                <p className="text-sm text-gray-500 mb-4">
                  Review and edit the field mappings. You can modify any auto-detected mappings.
                </p>

                <div className="space-y-3">
                  {mappings.map((mapping, index) => (
                    <div key={index} className="flex items-center space-x-4 bg-gray-50 rounded-lg p-3">
                      <div className="flex-1">
                        <input
                          type="text"
                          value={mapping.source_field}
                          onChange={(e) => {
                            const updated = [...mappings]
                            updated[index].source_field = e.target.value
                            setMappings(updated)
                          }}
                          placeholder="Source field name"
                          className="w-full text-sm font-mono bg-white border border-gray-300 rounded px-2 py-1"
                        />
                      </div>
                      <span className="text-gray-400">→</span>
                      <div className="flex-1">
                        <select
                          value={mapping.target_field}
                          onChange={(e) => handleMappingChange(index, e.target.value)}
                          className="w-full text-sm bg-white border border-gray-300 rounded px-2 py-1"
                        >
                          <option value="">Select target field...</option>
                          {CANONICAL_FIELDS.map(field => (
                            <option key={field.key} value={field.key}>{field.label}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getConfidenceBadge(mapping.confidence)}
                        <button
                          onClick={() => removeMappingItem(index)}
                          className="text-red-500 hover:text-red-700 text-sm"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  onClick={addMapping}
                  className="mt-3 text-sm text-blue-600 hover:text-blue-800"
                >
                  + Add Mapping
                </button>
              </div>

              <div className="flex justify-between space-x-3">
                <button
                  onClick={() => setStep('review')}
                  className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-md hover:bg-gray-700"
                >
                  ← Back
                </button>
                <button
                  onClick={() => setStep('validation')}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
                >
                  Next: Validate →
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Validation */}
          {step === 'validation' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Profile Name
                </label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  placeholder="Enter a descriptive name for this profile"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-medium text-green-900 mb-2">✅ Profile Summary</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-green-700">Broker Domain:</span>
                    <span className="font-mono ml-2">{profileData.broker_domain}</span>
                  </div>
                  <div>
                    <span className="text-green-700">Field Mappings:</span>
                    <span className="ml-2">{mappings.filter(m => m.target_field).length}</span>
                  </div>
                  <div>
                    <span className="text-green-700">Required Fields:</span>
                    <span className="ml-2">
                      {['brand', 'model', 'year', 'description'].filter(field => 
                        mappings.some(m => m.target_field === field)
                      ).length}/4
                    </span>
                  </div>
                  <div>
                    <span className="text-green-700">Confidence:</span>
                    <span className="ml-2">{getConfidenceBadge(profileData.confidence_score)}</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">Final Mappings</h4>
                <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
                  {mappings.filter(m => m.target_field).map((mapping, index) => (
                    <div key={index} className="flex items-center justify-between py-1 text-sm">
                      <span className="font-mono text-blue-600">&quot;{mapping.source_field}&quot;</span>
                      <span className="text-gray-400">→</span>
                      <span className="font-mono text-green-600">{mapping.target_field}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-between space-x-3">
                <button
                  onClick={() => setStep('mapping')}
                  className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-md hover:bg-gray-700"
                >
                  ← Back
                </button>
                <button
                  onClick={handleComplete}
                  className="px-6 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700"
                >
                  ✓ Create Profile
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}