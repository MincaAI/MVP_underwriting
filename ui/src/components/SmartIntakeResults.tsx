'use client'

import { useState } from 'react'

interface SmartIntakeResult {
  id: string
  description: string
  contact: string
  date: string
  cotNumber: string
  preAnalysis: 'Completo' | 'Incompleto'
  status: 'pending' | 'processing' | 'completed' | 'error'
  company?: string
  details?: string
}

interface SmartIntakeResultsProps {
  results: SmartIntakeResult[]
  onProcess: (id: string) => void
  onAskInfo: (id: string) => void
}

export default function SmartIntakeResults({ results, onProcess, onAskInfo }: SmartIntakeResultsProps) {
  const [statusFilter, setStatusFilter] = useState<string>('Tous')
  const [sortBy, setSortBy] = useState<string>('Plus récent d\'abord')

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            ✓ Completo
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            ⏳ Processing
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            ⏸ Pending
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            ⚠ Error
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {status}
          </span>
        )
    }
  }

  const getPreAnalysisBadge = (preAnalysis: string) => {
    if (preAnalysis === 'Completo') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          ✓ Completo
        </span>
      )
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          ⚠ Incompleto
        </span>
      )
    }
  }

  const getActionButton = (result: SmartIntakeResult) => {
    if (result.status === 'completed') {
      return (
        <button
          onClick={() => onProcess(result.id)}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Process
        </button>
      )
    } else if (result.preAnalysis === 'Incompleto') {
      return (
        <button
          onClick={() => onAskInfo(result.id)}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Ask info
        </button>
      )
    } else {
      return (
        <button
          onClick={() => onProcess(result.id)}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Process
        </button>
      )
    }
  }

  return (
    <div className="bg-white shadow-sm rounded-lg">
      {/* Header with filters */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-500 mt-1">Smart intake results and processing status</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="status-filter" className="text-sm font-medium text-gray-700">
                Status:
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="Tous">Tous</option>
                <option value="completed">Completed</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="error">Error</option>
              </select>
            </div>
            <div className="flex items-center space-x-2">
              <label htmlFor="sort-by" className="text-sm font-medium text-gray-700">
                Trier par date:
              </label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="Plus récent d'abord">Plus récent d&apos;abord</option>
                <option value="Plus ancien d'abord">Plus ancien d&apos;abord</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                COT
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pre Analysis
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.id} className="hover:bg-gray-50">
                <td className="px-3 py-4">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{result.description}</div>
                    {result.company && (
                      <div className="text-xs text-gray-500">{result.company}</div>
                    )}
                    <div className="text-xs text-gray-400">{result.contact}</div>
                    <div className="text-xs text-gray-400">{result.date}</div>
                  </div>
                </td>
                <td className="px-3 py-4 text-sm text-gray-900">
                  {result.cotNumber}
                </td>
                <td className="px-3 py-4">
                  {getPreAnalysisBadge(result.preAnalysis)}
                  {result.preAnalysis === 'Incompleto' && result.details && (
                    <div className="text-xs text-orange-600 mt-1">
                      ⚠ {result.details}
                    </div>
                  )}
                </td>
                <td className="px-3 py-4">
                  {getStatusBadge(result.status)}
                </td>
                <td className="px-3 py-4">
                  {getActionButton(result)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg mb-2">📧</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No smart intake results yet</h3>
          <p className="text-gray-500">
            Smart intake results will appear here once emails are processed.
          </p>
        </div>
      )}
    </div>
  )
}
