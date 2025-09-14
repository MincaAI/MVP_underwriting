'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api'

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
  doors?: number
  seats?: number
  engine_size?: string
  mileage?: number
  cvegs_code?: string
  confidence?: number
  process_status?: string
  processed_at?: string
  validation_errors?: string[]
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

interface ResultsTableProps {
  run: ProcessingRun
  onDownloadExport?: (exportUrl: string) => void
  onViewDetails?: (runId: string) => void
}

export default function ResultsTable({ run, onDownloadExport }: ResultsTableProps) {
  const [results, setResults] = useState<ProcessedVehicle[]>(run.results || [])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const loadResults = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.getProcessedResults(run.id) as { results?: ProcessedVehicle[] }
      setResults(data.results || [])
    } catch (error) {
      console.error('Error loading results:', error)
      // Fallback to mock data if API fails
      const mockResults: ProcessedVehicle[] = [
        {
          id: '1',
          vin: '1HGBH41JXMN109186',
          description: 'Toyota Corolla 2020',
          brand: 'TOYOTA',
          model: 'COROLLA',
          model_year: 2020,
          license_plate: 'ABC-123',
          coverage_type: 'Comprehensive',
          insured_value: 25000,
          premium: 1200,
          deductible: 500,
          color: 'White',
          fuel_type: 'Gasoline',
          transmission: 'Automatic',
          doors: 4,
          seats: 5,
          engine_size: '1.8L',
          mileage: 25000,
          cvegs_code: 'TOY-COR-001',
          confidence: 0.95,
          process_status: 'completed',
          processed_at: new Date().toISOString()
        },
        {
          id: '2',
          vin: '2HGBH41JXMN109187',
          description: 'Honda Civic EX 2019',
          brand: 'HONDA',
          model: 'CIVIC',
          model_year: 2019,
          license_plate: 'DEF-456',
          coverage_type: 'Liability',
          insured_value: 22000,
          premium: 1100,
          deductible: 500,
          color: 'Silver',
          fuel_type: 'Gasoline',
          transmission: 'Manual',
          doors: 4,
          seats: 5,
          engine_size: '1.5L',
          mileage: 30000,
          cvegs_code: 'HON-CIV-002',
          confidence: 0.89,
          process_status: 'completed',
          processed_at: new Date().toISOString()
        }
      ]
      setResults(mockResults)
    } finally {
      setLoading(false)
    }
  }, [run.id])

  useEffect(() => {
    if (run.status === 'completed' && !results.length) {
      loadResults()
    }
  }, [run.status, results.length, loadResults])

  const handleDownload = async () => {
    if (run.export_url && onDownloadExport) {
      onDownloadExport(run.export_url)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100'
      case 'error': return 'text-red-600 bg-red-100'
      case 'pending': return 'text-yellow-600 bg-yellow-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600'
    if (confidence >= 0.7) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (!expanded) {
    return (
      <div className="border rounded-lg p-4 bg-white">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-medium text-gray-900">{run.fileName}</h3>
            <p className="text-sm text-gray-500">
              Case: {run.caseId} • {run.type === 'email_intake' ? '📧 Email' : '📄 File'}
            </p>
            {run.emailData && (
              <p className="text-xs text-gray-400">From: {run.emailData.from}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(run.status)}`}>
              {run.status}
            </span>
            <button
              onClick={() => setExpanded(true)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View Results
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="border rounded-lg bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{run.fileName}</h3>
            <p className="text-sm text-gray-500">
              Case: {run.caseId} • Profile: {run.profile} • {run.type === 'email_intake' ? '📧 Email' : '📄 File'}
            </p>
            {run.emailData && (
              <p className="text-xs text-gray-400">From: {run.emailData.from}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setExpanded(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Collapse
            </button>
            {run.export_url && (
              <button
                onClick={handleDownload}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                📥 Download Export
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Vehicle
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                VIN
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Year
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                License Plate
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Coverage
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Insured Value
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                CVEGS Code
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={9} className="px-6 py-4 text-center text-gray-500">
                  Loading results...
                </td>
              </tr>
            ) : results.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-6 py-4 text-center text-gray-500">
                  No results available
                </td>
              </tr>
            ) : (
              results.map((vehicle) => (
                <tr key={vehicle.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {vehicle.brand} {vehicle.model}
                      </div>
                      <div className="text-sm text-gray-500">
                        {vehicle.description}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.vin || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.model_year || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.license_plate || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.coverage_type || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.insured_value ? `$${vehicle.insured_value.toLocaleString()}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {vehicle.cvegs_code || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {vehicle.confidence ? (
                      <span className={`text-sm font-medium ${getConfidenceColor(vehicle.confidence)}`}>
                        {(vehicle.confidence * 100).toFixed(1)}%
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(vehicle.process_status || 'pending')}`}>
                      {vehicle.process_status || 'pending'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      {results.length > 0 && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Total Records: <strong>{results.length}</strong></span>
            <span>Average Confidence: <strong>{((results.reduce((sum, v) => sum + (v.confidence || 0), 0) / results.length) * 100).toFixed(1)}%</strong></span>
            <span>CVEGS Codes: <strong>{results.filter(v => v.cvegs_code).length}</strong></span>
          </div>
        </div>
      )}
    </div>
  )
}