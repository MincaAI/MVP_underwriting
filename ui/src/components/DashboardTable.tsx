'use client'

import { useState } from 'react'
import ResultsTable from './ResultsTable'

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
  emailData?: {
    from: string
    subject: string
    receivedDate: string
    content: string
    attachments: File[]
  }
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

interface DashboardTableProps {
  runs: ProcessingRun[]
  onDownloadExport?: (exportUrl: string) => void
  onViewDetails?: (runId: string) => void
}

export default function DashboardTable({ runs, onDownloadExport, onViewDetails }: DashboardTableProps) {
  const [selectedRun, setSelectedRun] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('recent')

  const filteredRuns = runs.filter(run => {
    if (statusFilter === 'all') return true
    return run.status === statusFilter
  })

  const sortedRuns = [...filteredRuns].sort((a, b) => {
    switch (sortBy) {
      case 'recent':
        return new Date(b.caseId).getTime() - new Date(a.caseId).getTime()
      case 'oldest':
        return new Date(a.caseId).getTime() - new Date(b.caseId).getTime()
      case 'name':
        return a.fileName.localeCompare(b.fileName)
      default:
        return 0
    }
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'error': return 'bg-red-100 text-red-800'
      case 'extracting': return 'bg-blue-100 text-blue-800'
      case 'transforming': return 'bg-yellow-100 text-yellow-800'
      case 'ready_for_matching': return 'bg-green-100 text-green-800'
      case 'matching': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPreAnalysisStatus = (run: ProcessingRun) => {
    if (run.status === 'completed') {
      return { status: 'complete', message: 'Completo' }
    } else if (run.status === 'error') {
      return { status: 'incomplete', message: 'Error en procesamiento' }
    } else {
      return { status: 'incomplete', message: 'Procesando...' }
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">Tous</option>
              <option value="completed">Completed</option>
              <option value="extracting">Extracting</option>
              <option value="transforming">Transforming</option>
              <option value="ready_for_matching">Ready for Matching</option>
              <option value="matching">Matching</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Trier par date</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="recent">Plus récent d&apos;abord</option>
              <option value="oldest">Plus ancien d&apos;abord</option>
              <option value="name">Par nom</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  COT Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pre Analysis
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedRuns.map((run) => {
                const preAnalysis = getPreAnalysisStatus(run)
                const contactEmail = run.emailData?.from || 'system@minca.ai'
                const date = new Date(parseInt(run.caseId.split('_')[1]) || Date.now()).toLocaleString('en-GB', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                }).replace(',', '')
                
                return (
                  <tr key={run.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {run.fileName}
                        </div>
                        <div className="text-sm text-gray-500">
                          {run.type === 'email_intake' ? 'Email Processing' : 'File Upload'}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {contactEmail}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {run.caseId}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {preAnalysis.status === 'complete' ? (
                          <>
                            <span className="text-green-500 mr-2">✓</span>
                            <span className="text-sm text-green-600">{preAnalysis.message}</span>
                          </>
                        ) : (
                          <>
                            <span className="text-orange-500 mr-2">⚠</span>
                            <span className="text-sm text-orange-600">{preAnalysis.message}</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {run.status === 'completed' ? (
                        <button
                          onClick={() => setSelectedRun(selectedRun === run.id ? null : run.id)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          {selectedRun === run.id ? 'Hide Results' : 'View Results'}
                        </button>
                      ) : (
                        <button
                          disabled
                          className="text-gray-400 cursor-not-allowed"
                        >
                          Processing...
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Expanded Results */}
      {selectedRun && (
        <div className="mt-6">
          {(() => {
            const run = runs.find(r => r.id === selectedRun)
            return run ? (
              <ResultsTable
                run={run}
                onDownloadExport={onDownloadExport}
                onViewDetails={onViewDetails}
              />
            ) : null
          })()}
        </div>
      )}
    </div>
  )
}
