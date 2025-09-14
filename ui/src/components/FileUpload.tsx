'use client'

import { useState, useRef } from 'react'

interface FileUploadProps {
  onUpload: (file: File, profile: string) => void
}

const brokerProfiles = [
  { value: 'lucky_gas.yaml', label: 'Lucky Gas', description: 'Standard Lucky Gas broker format' },
  { value: 'generic.yaml', label: 'Generic', description: 'Generic broker format template' }
]

export default function FileUpload({ onUpload }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedProfile, setSelectedProfile] = useState(brokerProfiles[0].value)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
    }
  }

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile, selectedProfile)
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const isExcelOrCSV = (file: File) => {
    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.ms-excel', // .xls
      'text/csv' // .csv
    ]
    return validTypes.includes(file.type) || file.name.endsWith('.xlsx') || file.name.endsWith('.xls') || file.name.endsWith('.csv')
  }

  return (
    <div className="space-y-4">
      {/* Profile Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Broker Profile
        </label>
        <select
          value={selectedProfile}
          onChange={(e) => setSelectedProfile(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {brokerProfiles.map((profile) => (
            <option key={profile.value} value={profile.value}>
              {profile.label} - {profile.description}
            </option>
          ))}
        </select>
      </div>

      {/* File Drop Area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
          ${dragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="space-y-2">
          <div className="text-4xl">📁</div>
          <div>
            <p className="text-lg font-medium text-gray-900">
              {dragActive ? 'Drop your file here' : 'Drop file here or click to browse'}
            </p>
            <p className="text-sm text-gray-500">
              Supports Excel (.xlsx, .xls) and CSV files
            </p>
          </div>
        </div>
      </div>

      {/* Selected File Display */}
      {selectedFile && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">
                {isExcelOrCSV(selectedFile) ? '📊' : '❌'}
              </div>
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setSelectedFile(null)}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              >
                Remove
              </button>
              <button
                onClick={handleUpload}
                disabled={!isExcelOrCSV(selectedFile)}
                className={`
                  px-4 py-2 text-sm font-medium rounded-md
                  ${isExcelOrCSV(selectedFile)
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                Upload & Process
              </button>
            </div>
          </div>
          
          {!isExcelOrCSV(selectedFile) && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              ⚠️ Please select a valid Excel or CSV file
            </div>
          )}
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">Processing Pipeline:</h4>
        <ol className="text-sm text-blue-800 space-y-1">
          <li>1. 📤 <strong>Upload:</strong> File uploaded to S3 storage</li>
          <li>2. 🔄 <strong>Transform:</strong> Apply broker profile rules</li>
          <li>3. 🤖 <strong>Codify:</strong> AI-powered vehicle classification</li>
          <li>4. 📊 <strong>Export:</strong> Generate Gcotiza-ready Excel</li>
        </ol>
      </div>
    </div>
  )
}