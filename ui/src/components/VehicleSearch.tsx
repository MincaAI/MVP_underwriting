'use client'

import { useState } from 'react'

interface VehicleResult {
  id: string
  make: string
  model: string
  year?: number
  cvegs_code: string
  confidence: number
}

export default function VehicleSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<VehicleResult[]>([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    
    setLoading(true)
    // Simulate API call
    setTimeout(() => {
      const mockResults: VehicleResult[] = [
        {
          id: '1',
          make: 'TOYOTA',
          model: 'COROLLA',
          year: 2020,
          cvegs_code: 'TOY-COR-001',
          confidence: 0.95
        },
        {
          id: '2', 
          make: 'TOYOTA',
          model: 'COROLLA',
          year: 2019,
          cvegs_code: 'TOY-COR-002',
          confidence: 0.89
        },
        {
          id: '3',
          make: 'TOYOTA',
          model: 'CORONA',
          year: 2018,
          cvegs_code: 'TOY-CRN-001',
          confidence: 0.72
        }
      ]
      
      setResults(mockResults)
      setLoading(false)
    }, 1000)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="flex space-x-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="e.g., Toyota Corolla 2020"
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '⏳' : '🔍'}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">
            Search Results ({results.length})
          </h4>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {results.map((result) => (
              <div key={result.id} className="border border-gray-200 rounded p-3 text-sm">
                <div className="flex justify-between items-start mb-1">
                  <div className="font-medium text-gray-900">
                    {result.make} {result.model}
                    {result.year && ` (${result.year})`}
                  </div>
                  <div className={`
                    px-2 py-1 rounded text-xs font-medium
                    ${result.confidence >= 0.9 ? 'bg-green-100 text-green-800' :
                      result.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }
                  `}>
                    {(result.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="text-xs text-gray-600">
                  CVEGS: {result.cvegs_code}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {results.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-2xl mb-2">🔍</div>
          <p className="text-sm">Search the AMIS vehicle database</p>
          <p className="text-xs mt-1">Try: &quot;Toyota Corolla&quot;, &quot;Honda Civic&quot;, etc.</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-2xl mb-2 animate-spin">⏳</div>
          <p className="text-sm">Searching vehicles...</p>
        </div>
      )}
    </div>
  )
}