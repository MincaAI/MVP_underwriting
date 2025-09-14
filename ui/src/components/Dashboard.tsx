'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api'
import FileUpload from './FileUpload'
import ManualIntakeForm from './ManualIntakeForm'
import BrokerProfileManager from './BrokerProfileManager'
import ProcessingStatus from './ProcessingStatus'
import ResultsTable from './ResultsTable'
import DashboardTable from './DashboardTable'
import VehicleSearch from './VehicleSearch'


interface ProcessEmailData {
  from: string
  subject: string
  receivedDate: string
  content: string
  attachments: File[]
}

interface ProcessedVehicle {
  id: string
  vin?: string
  description?: string
  brand?: string
  model?: string
  model_year?: number
  license_plate?: string
  coverage_type?: string
  insured_value?: number
  premium?: number
  deductible?: number
  color?: string
  fuel_type?: string
  transmission?: string
  body_type?: string
  use_type?: string
  cvegs_code?: string
  confidence_score?: number
  confidence_level?: 'high' | 'medium' | 'low'
  processing_status?: 'pending' | 'processing' | 'completed' | 'error'
  processed_at?: string
}

interface ProcessingRun {
  id: string
  caseId: string
  status: 'extracting' | 'transforming' | 'ready_for_matching' | 'matching' | 'completed' | 'error'
  fileName: string
  profile: string
  progress: number
  type: 'file_upload' | 'email_intake'
  emailData?: ProcessEmailData
  results?: ProcessedVehicle[]
  metrics?: {
    rows_extracted?: number
    rows_processed?: number
    ready_for_matching?: boolean
    successful_matches?: number
    failed_matches?: number
    processed?: number
    codified?: number
    confidence_avg?: number
  }
  export_url?: string
}


interface ProcessDocumentResponse {
  run_id: string
  case_id: string
  status?: string
}

interface ProcessingStatusResponse {
  status: 'extracting' | 'transforming' | 'ready_for_matching' | 'matching' | 'completed' | 'error'
  progress?: number
}

export default function Dashboard() {
  const [activeRuns, setActiveRuns] = useState<ProcessingRun[]>([])
  const [completedRuns, setCompletedRuns] = useState<ProcessingRun[]>([])
  const [activeTab, setActiveTab] = useState<'file_upload' | 'email_intake' | 'profiles' | 'dashboard'>('file_upload')

  const pollProcessingStatus = async (runId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await apiClient.getProcessingStatus(runId) as ProcessingStatusResponse
        
        setActiveRuns(prev => prev.map(run => 
          run.id === runId 
            ? { ...run, status: status.status, progress: status.progress || 0 }
            : run
        ))
        
        // If completed, move to completed runs
        if (status.status === 'completed') {
          clearInterval(pollInterval)
          setTimeout(() => {
            setActiveRuns(prev => {
              const completedRun = prev.find(run => run.id === runId)
              if (completedRun) {
                setCompletedRuns(prevCompleted => [...prevCompleted, {
                  ...completedRun,
                  status: 'completed',
                  results: mockResults, // Would get real results from API
                  metrics: { rows_extracted: 150, rows_processed: 150, successful_matches: 142, failed_matches: 8, ready_for_matching: true },
                  export_url: 'http://localhost:9000/exports/sample-export.xlsx' // Mock export URL
                }])
                return prev.filter(run => run.id !== runId)
              }
              return prev
            })
          }, 1000)
        }
        
        // If error, clear interval
        if (status.status === 'error') {
          clearInterval(pollInterval)
        }
        
      } catch (error) {
        console.error('Error polling status:', error)
        clearInterval(pollInterval)
      }
    }, 2000) // Poll every 2 seconds
  }

  const handleFileUpload = async (file: File, profile: string) => {
    const caseId = `CASE_${Date.now()}`
    
    try {
      // Call the document processor API
      const response = await apiClient.processDocument(file, caseId, profile, 'gcotiza_v1.yaml') as ProcessDocumentResponse
      
      const newRun: ProcessingRun = {
        id: response.run_id,
        caseId: response.case_id,
        status: 'extracting',
        fileName: file.name,
        profile,
        progress: 0,
        type: 'file_upload'
      }
      
      setActiveRuns(prev => [...prev, newRun])
      
      // Start polling for status
      pollProcessingStatus(response.run_id)
      
    } catch (error) {
      console.error('Error uploading file:', error)
      // Could show error toast here
    }
  }

  const handleDownloadExport = async (exportUrl: string) => {
    try {
      const blob = await apiClient.downloadExport(exportUrl)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `export_${Date.now()}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error downloading export:', error)
      // Could show error toast here
    }
  }

  const handleTriggerMatching = async (runId: string) => {
    try {
      const response = await apiClient.triggerMatching(runId)
      console.log('Matching triggered:', response)
      
      // Update the run status to matching
      setActiveRuns(prev => prev.map(run => 
        run.id === runId 
          ? { ...run, status: 'matching' as const }
          : run
      ))
      
      // Start polling for matching results
      pollProcessingStatus(runId)
      
    } catch (error) {
      console.error('Error triggering matching:', error)
      // Could show error toast here
    }
  }

  const handleEmailProcess = async (emailData: ProcessEmailData) => {
    const caseId = `EMAIL_${Date.now()}`
    
    try {
      // Process the email upload (no broker profile selection needed)
      const response = await apiClient.processEmailData({
        from: emailData.from,
        subject: emailData.subject,
        receivedDate: emailData.receivedDate,
        content: emailData.content,
        attachments: emailData.attachments
      })
      
      const newRun: ProcessingRun = {
        id: response.run_id || `run_${Date.now()}`,
        caseId: response.case_id || caseId,
        status: 'extracting',
        fileName: `Email from ${emailData.from}`,
        profile: 'generic.yaml', // Default profile, applied during processing
        progress: 0,
        type: 'email_intake',
        emailData
      }
      
      setActiveRuns(prev => [...prev, newRun])
      
      // Start polling for status
      pollProcessingStatus(newRun.id)
      
      console.log('Email processing started:', {
        run_id: response.run_id,
        case_id: response.case_id,
        profile: 'generic.yaml',
        attachments: emailData.attachments.length,
        response
      })
      
    } catch (error) {
      console.error('Error processing email:', error)
      
      // Fallback to local processing if API fails
      const emailDomain = emailData.from.split('@')[1]
      let profile = 'generic.yaml'
      
      // Simple broker detection fallback
      if (emailDomain.includes('luckygas')) profile = 'lucky_gas.yaml'
      else if (emailDomain.includes('axa')) profile = 'axa_seguros.yaml'
      
      const mockRunId = `run_${Date.now()}`
      const newRun: ProcessingRun = {
        id: mockRunId,
        caseId,
        status: 'extracting',
        fileName: `Email from ${emailData.from} (Local)`,
        profile,
        progress: 0,
        type: 'email_intake',
        emailData
      }
      
      setActiveRuns(prev => [...prev, newRun])
      pollProcessingStatus(mockRunId)
      
      console.log('Fallback to local processing:', {
        broker_domain: emailDomain,
        detected_profile: profile,
        error: error instanceof Error ? error.message : String(error)
      })
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                🚗 Minca AI Underwriting
              </h1>
              <span className="ml-4 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                MVP v0.1.0
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">API Status:</span>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
                <span className="text-sm text-green-600">Connected</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Processing Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tab Navigation */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <nav className="flex space-x-8">
                  <button
                    onClick={() => setActiveTab('file_upload')}
                    className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'file_upload'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    📤 File Upload
                  </button>
                  <button
                    onClick={() => setActiveTab('email_intake')}
                    className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'email_intake'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    📧 Manual Email Entry
                  </button>
                  <button
                    onClick={() => setActiveTab('profiles')}
                    className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'profiles'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    🏢 Broker Profiles
                  </button>
                  <button
                    onClick={() => setActiveTab('dashboard')}
                    className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'dashboard'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    📊 Dashboard
                  </button>
                </nav>
              </div>

              <div className="p-6">
                {/* File Upload Tab */}
                {activeTab === 'file_upload' && (
                  <div>
                    <div className="mb-4">
                      <h2 className="text-lg font-medium text-gray-900">
                        Upload Broker Files
                      </h2>
                      <p className="text-sm text-gray-500 mt-1">
                        Upload Excel/CSV files for transformation and vehicle codification
                      </p>
                    </div>
                    <FileUpload onUpload={handleFileUpload} />
                  </div>
                )}

                {/* Email Intake Tab */}
                {activeTab === 'email_intake' && (
                  <ManualIntakeForm onProcess={handleEmailProcess} />
                )}

                {/* Broker Profiles Tab */}
                {activeTab === 'profiles' && (
                  <BrokerProfileManager 
                    onProfileSelect={(profile) => console.log('Selected profile:', profile)}
                    onCreateNew={() => console.log('Create new profile')}
                  />
                )}

                {/* Dashboard Tab */}
                {activeTab === 'dashboard' && (
                  <div>
                    <div className="mb-4">
                      <h2 className="text-lg font-medium text-gray-900">
                        Processing Dashboard
                      </h2>
                      <p className="text-sm text-gray-500 mt-1">
                        View all processing runs and their results
                      </p>
                    </div>
                    <DashboardTable
                      runs={[...activeRuns, ...completedRuns]}
                      onDownloadExport={handleDownloadExport}
                      onViewDetails={(runId) => console.log('View details for:', runId)}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Active Processing */}
            {activeRuns.length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">
                    ⚡ Processing Status
                  </h2>
                </div>
                <div className="p-6 space-y-4">
                  {activeRuns.map((run) => (
                    <ProcessingStatus key={run.id} run={run} onTriggerMatching={handleTriggerMatching} />
                  ))}
                </div>
              </div>
            )}

            {/* Completed Runs */}
            {completedRuns.length > 0 && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">
                      ✅ Completed Processing Runs
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {completedRuns.length} completed run{completedRuns.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                
                {completedRuns.map((run) => (
                  <ResultsTable
                    key={run.id}
                    run={run}
                    onDownloadExport={handleDownloadExport}
                    onViewDetails={(runId) => console.log('View details for:', runId)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Vehicle Search */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">
                  🔍 Vehicle Search
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Search AMIS vehicle database
                </p>
              </div>
              <div className="p-6">
                <VehicleSearch />
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">📈 Quick Stats</h2>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Total Runs:</span>
                    <span className="font-medium">{completedRuns.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Records Processed:</span>
                    <span className="font-medium">
                      {completedRuns.reduce((sum, run) => sum + (run.metrics?.processed || 0), 0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Active Jobs:</span>
                    <span className="font-medium">{activeRuns.length}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* API Endpoints */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">🔗 API Endpoints</h2>
              </div>
              <div className="p-6">
                <div className="space-y-2 text-xs font-mono">
                  <div className="text-green-600">POST /transform</div>
                  <div className="text-blue-600">POST /codify/batch</div>
                  <div className="text-purple-600">POST /export</div>
                  <div className="text-gray-600">GET /health</div>
                </div>
                <div className="mt-4">
                  <a 
                    href="http://localhost:8000/docs" 
                    target="_blank" 
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    📖 View API Docs
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const mockResults: ProcessedVehicle[] = [
  { 
    id: "1", 
    description: "Toyota Corolla 2020", 
    brand: "TOYOTA", 
    model: "COROLLA",
    model_year: 2020,
    confidence_score: 0.95,
    confidence_level: "high",
    processing_status: "completed",
    processed_at: new Date().toISOString()
  },
  { 
    id: "2", 
    description: "Honda Civic EX", 
    brand: "HONDA", 
    model: "CIVIC",
    model_year: 2020,
    confidence_score: 0.89,
    confidence_level: "high",
    processing_status: "completed",
    processed_at: new Date().toISOString()
  },
  { 
    id: "3", 
    description: "Ford F-150 XLT", 
    brand: "FORD", 
    model: "F-150",
    model_year: 2020,
    confidence_score: 0.92,
    confidence_level: "high",
    processing_status: "completed",
    processed_at: new Date().toISOString()
  }
]