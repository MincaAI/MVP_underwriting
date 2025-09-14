'use client'

import { useState, useRef } from 'react'

interface EmailAttachment {
  id: string
  name: string
  file: File
}

interface EmailData {
  from: string
  subject: string
  receivedDate: string
  content: string
  attachments: EmailAttachment[]
}

interface ProcessEmailData {
  from: string
  subject: string
  receivedDate: string
  content: string
  attachments: File[]
}

interface ManualIntakeFormProps {
  onProcess: (emailData: ProcessEmailData) => void
}

export default function ManualIntakeForm({ onProcess }: ManualIntakeFormProps) {
  const [emailData, setEmailData] = useState<EmailData>({
    from: '',
    subject: '',
    receivedDate: new Date().toISOString().split('T')[0], // Today's date
    content: '',
    attachments: []
  })
  
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleInputChange = (field: keyof EmailData, value: string) => {
    setEmailData(prev => ({ ...prev, [field]: value }))
  }

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
    
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files))
    }
  }

  const addFiles = (files: File[]) => {
    const validFiles = files.filter(file => 
      file.type.includes('spreadsheet') || 
      file.type === 'text/csv' ||
      file.name.endsWith('.xlsx') || 
      file.name.endsWith('.xls') || 
      file.name.endsWith('.csv') ||
      file.type === 'application/pdf'
    )

    const newAttachments: EmailAttachment[] = validFiles.map((file, index) => ({
      id: `${Date.now()}-${index}`,
      name: file.name,
      file
    }))

    setEmailData(prev => ({
      ...prev,
      attachments: [...prev.attachments, ...newAttachments]
    }))
  }

  const removeAttachment = (id: string) => {
    setEmailData(prev => ({
      ...prev,
      attachments: prev.attachments.filter(att => att.id !== id)
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (emailData.from && emailData.subject && emailData.attachments.length > 0) {
      // Convert EmailAttachment[] to the format expected by API
      const processData = {
        from: emailData.from,
        subject: emailData.subject,
        receivedDate: emailData.receivedDate,
        content: emailData.content,
        attachments: emailData.attachments.map(att => att.file)
      }
      onProcess(processData)
      // Reset form
      setEmailData({
        from: '',
        subject: '',
        receivedDate: new Date().toISOString().split('T')[0],
        content: '',
        attachments: []
      })
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) return '📊'
    if (fileName.endsWith('.csv')) return '📋'
    if (fileName.endsWith('.pdf')) return '📄'
    return '📁'
  }

  const isValidFile = (fileName: string) => {
    return fileName.endsWith('.xlsx') || fileName.endsWith('.xls') || 
           fileName.endsWith('.csv') || fileName.endsWith('.pdf')
  }

  const canSubmit = emailData.from && emailData.subject && emailData.attachments.length > 0

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-900">
          📧 Manual Email Entry
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Simulate smart intake by manually entering email data (temporary before full email integration)
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Email Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              From Email Address
            </label>
            <input
              type="email"
              value={emailData.from}
              onChange={(e) => handleInputChange('from', e.target.value)}
              placeholder="broker@example.com"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Email address for record keeping and tracking
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Received Date
            </label>
            <input
              type="date"
              value={emailData.receivedDate}
              onChange={(e) => handleInputChange('receivedDate', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Subject
          </label>
          <input
            type="text"
            value={emailData.subject}
            onChange={(e) => handleInputChange('subject', e.target.value)}
            placeholder="Fleet Insurance Request - Client Name"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        {/* Email Content */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Email Content
          </label>
          <textarea
            value={emailData.content}
            onChange={(e) => handleInputChange('content', e.target.value)}
            placeholder="Paste email content here... (client info, vehicle descriptions, etc.)"
            rows={8}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            AI will extract client info, broker details, and vehicle descriptions from this content
          </p>
        </div>

        {/* File Attachments */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Attachments
          </label>
          
          {/* File Drop Area */}
          <div
            className={`
              relative border-2 border-dashed rounded-lg p-6 text-center transition-colors mb-4
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
              multiple
              accept=".xlsx,.xls,.csv,.pdf"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            
            <div className="space-y-2">
              <div className="text-3xl">📎</div>
              <div>
                <p className="text-base font-medium text-gray-900">
                  {dragActive ? 'Drop files here' : 'Drop attachments here or click to browse'}
                </p>
                <p className="text-sm text-gray-500">
                  Excel (.xlsx, .xls), CSV, and PDF files supported
                </p>
              </div>
            </div>
          </div>

          {/* Attachment List */}
          {emailData.attachments.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">
                Attached Files ({emailData.attachments.length})
              </h4>
              {emailData.attachments.map((attachment) => (
                <div key={attachment.id} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{getFileIcon(attachment.name)}</span>
                    <div>
                      <p className="font-medium text-gray-900">{attachment.name}</p>
                      <p className="text-sm text-gray-500">
                        {(attachment.file.size / 1024 / 1024).toFixed(2)} MB
                        {!isValidFile(attachment.name) && (
                          <span className="ml-2 text-red-500">⚠️ Unsupported format</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAttachment(attachment.id)}
                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Processing Info */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h4 className="font-medium text-amber-900 mb-2">🔄 Processing Pipeline:</h4>
          <ol className="text-sm text-amber-800 space-y-1">
            <li>1. 📤 <strong>Upload:</strong> Store email and attachments to S3</li>
            <li>2. 📄 <strong>Content Extraction:</strong> Parse email content and attachments</li>
            <li>3. 🤖 <strong>AI Processing:</strong> Extract vehicle data using LLM</li>
            <li>4. ✅ <strong>Data Processing:</strong> Apply validation and transformation rules</li>
            <li>5. 📊 <strong>Export:</strong> Generate standardized output format</li>
          </ol>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!canSubmit}
            className={`
              px-6 py-3 text-base font-medium rounded-md transition-colors
              ${canSubmit
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            🚀 Process Email Data
          </button>
        </div>

        {!canSubmit && (
          <div className="text-sm text-gray-500 text-center">
            Please fill in required fields and add at least one attachment
          </div>
        )}
      </form>
    </div>
  )
}