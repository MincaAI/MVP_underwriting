interface ProcessingRun {
  id: string
  caseId: string
  status: 'extracting' | 'transforming' | 'ready_for_matching' | 'matching' | 'completed' | 'error'
  fileName: string
  profile: string
  progress: number
  metrics?: {
    rows_extracted?: number
    rows_processed?: number
    ready_for_matching?: boolean
    successful_matches?: number
    failed_matches?: number
  }
}

interface ProcessingStatusProps {
  run: ProcessingRun
  onTriggerMatching?: (runId: string) => void
}

const statusConfig = {
  extracting: { icon: '📄', label: 'Extracting Data', color: 'blue', description: 'Parsing Excel/CSV files and extracting vehicle data...' },
  transforming: { icon: '🔄', label: 'Normalizing Data', color: 'yellow', description: 'Cleaning and standardizing data for matching...' },
  ready_for_matching: { icon: '✅', label: 'Ready for Matching', color: 'green', description: 'Data preprocessed and ready for vehicle matching!' },
  matching: { icon: '🤖', label: 'Matching Vehicles', color: 'purple', description: 'Matching vehicles against AMIS catalog...' },
  completed: { icon: '🎉', label: 'Completed', color: 'green', description: 'All processing completed successfully!' },
  error: { icon: '❌', label: 'Error', color: 'red', description: 'An error occurred during processing.' }
}

export default function ProcessingStatus({ run, onTriggerMatching }: ProcessingStatusProps) {
  const config = statusConfig[run.status]
  
  const getProgressPercentage = () => {
    switch (run.status) {
      case 'extracting': return 25
      case 'transforming': return 50
      case 'ready_for_matching': return 75
      case 'matching': return 90
      case 'completed': return 100
      case 'error': return 0
      default: return 0
    }
  }
  
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="text-2xl">{config.icon}</div>
          <div>
            <h3 className="font-medium text-gray-900">{run.fileName}</h3>
            <p className="text-sm text-gray-500">
              Case: {run.caseId} • Profile: {run.profile}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className={`
            text-sm font-medium
            ${config.color === 'blue' ? 'text-blue-600' : ''}
            ${config.color === 'yellow' ? 'text-yellow-600' : ''}
            ${config.color === 'purple' ? 'text-purple-600' : ''}
            ${config.color === 'green' ? 'text-green-600' : ''}
            ${config.color === 'red' ? 'text-red-600' : ''}
          `}>
            {config.label}
          </div>
          <div className="text-xs text-gray-500">
            {getProgressPercentage().toFixed(0)}% complete
          </div>
        </div>
      </div>
      
      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className={`
            h-2 rounded-full transition-all duration-500
            ${config.color === 'blue' ? 'bg-blue-600' : ''}
            ${config.color === 'yellow' ? 'bg-yellow-400' : ''}
            ${config.color === 'purple' ? 'bg-purple-600' : ''}
            ${config.color === 'green' ? 'bg-green-600' : ''}
            ${config.color === 'red' ? 'bg-red-600' : ''}
          `}
          style={{ width: `${getProgressPercentage()}%` }}
        />
      </div>
      
      {/* Current Stage Description */}
      <div className="mt-2 text-sm text-gray-600">
        {config.description}
      </div>
      
      {/* Metrics */}
      {run.metrics && (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
          {run.metrics.rows_extracted && (
            <div>Rows extracted: {run.metrics.rows_extracted}</div>
          )}
          {run.metrics.rows_processed && (
            <div>Rows processed: {run.metrics.rows_processed}</div>
          )}
          {run.metrics.successful_matches !== undefined && (
            <div>Matches found: {run.metrics.successful_matches}</div>
          )}
          {run.metrics.failed_matches !== undefined && (
            <div>No matches: {run.metrics.failed_matches}</div>
          )}
        </div>
      )}
      
      {/* Action Button for Ready for Matching */}
      {run.status === 'ready_for_matching' && onTriggerMatching && (
        <div className="mt-3">
          <button
            onClick={() => onTriggerMatching(run.id)}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
          >
            🚀 Start Vehicle Matching
          </button>
        </div>
      )}
      
      {/* Pipeline Steps Visualization */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className={`flex items-center space-x-1 ${run.status === 'extracting' ? 'text-blue-600' : run.status === 'transforming' || run.status === 'ready_for_matching' || run.status === 'matching' || run.status === 'completed' ? 'text-green-600' : ''}`}>
            <span>1</span>
            <span>Extract</span>
          </div>
          <div className={`flex items-center space-x-1 ${run.status === 'transforming' ? 'text-yellow-600' : run.status === 'ready_for_matching' || run.status === 'matching' || run.status === 'completed' ? 'text-green-600' : ''}`}>
            <span>2</span>
            <span>Transform</span>
          </div>
          <div className={`flex items-center space-x-1 ${run.status === 'matching' ? 'text-purple-600' : run.status === 'completed' ? 'text-green-600' : ''}`}>
            <span>3</span>
            <span>Match</span>
          </div>
          <div className={`flex items-center space-x-1 ${run.status === 'completed' ? 'text-green-600' : ''}`}>
            <span>4</span>
            <span>Complete</span>
          </div>
        </div>
      </div>
    </div>
  )
}