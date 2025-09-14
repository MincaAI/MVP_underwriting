'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import SmartIntakeResults from './SmartIntakeResults'
import QuickEmailInput from './QuickEmailInput'
import Claveteador from './Claveteador'
import VehicleMatching from './VehicleMatching'
import ExcelExport from './ExcelExport'

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

interface EmailData {
  from: string
  subject: string
  receivedDate: string
  content: string
  attachments: File[]
}

export default function NewDashboard() {
  const [smartIntakeResults, setSmartIntakeResults] = useState<SmartIntakeResult[]>([])
  const [isProcessingEmail, setIsProcessingEmail] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [currentView, setCurrentView] = useState<'dashboard' | 'claveteador' | 'vehicleMatching' | 'export'>('dashboard')
  const [selectedCase, setSelectedCase] = useState<SmartIntakeResult | null>(null)

  // Mock data for demonstration - replace with real API calls
  useEffect(() => {
    // Simulate loading smart intake results
    const loadMockData = () => {
      const mockResults: SmartIntakeResult[] = [
        {
          id: '1',
          description: 'Fleet Insurance Quote Request',
          contact: 'maria.rodriguez@broker.com',
          date: '2024-01-15 09:30',
          cotNumber: 'TK-2024-001',
          preAnalysis: 'Completo',
          status: 'pending',
          company: 'Logistics Express S.A. de C.V.'
        },
        {
          id: '2',
          description: 'Fleet Renewal Request',
          contact: 'carlos.mendez@broker.com',
          date: '2024-01-14 14:22',
          cotNumber: 'TK-2024-002',
          preAnalysis: 'Completo',
          status: 'pending',
          company: 'Metro Delivery Services'
        },
        {
          id: '3',
          description: 'Commercial Vehicle Coverage',
          contact: 'ana.torres@broker.com',
          date: '2024-01-13 16:45',
          cotNumber: 'TK-2024-003',
          preAnalysis: 'Completo',
          status: 'pending',
          company: 'Constructora Torres & Asociados'
        },
        {
          id: '4',
          description: 'Auto Insurance Premium Review',
          contact: 'roberto.jimenez@transportes.com',
          date: '2024-01-12 11:18',
          cotNumber: 'TK-2024-004',
          preAnalysis: 'Incompleto',
          status: 'pending',
          company: 'Transportes del Norte S.A.',
          details: 'Falta: Coberturas moto, RFC, Lista de vehículos'
        },
        {
          id: '5',
          description: 'Fleet Coverage Extension Request',
          contact: 'carmen.morales@distribuidora.com',
          date: '2024-01-11 08:52',
          cotNumber: 'TK-2024-005',
          preAnalysis: 'Incompleto',
          status: 'pending',
          company: 'Distribuidora Central LTDA',
          details: 'Falta: Coberturas moto, RFC, Lista de vehículos'
        }
      ]
      
      setSmartIntakeResults(mockResults)
      setIsLoading(false)
    }

    // Simulate API delay
    setTimeout(loadMockData, 1000)
  }, [])

  const handleEmailSubmit = async (emailData: EmailData) => {
    setIsProcessingEmail(true)
    
    try {
      // Call the API to process the email
      const response = await apiClient.processEmailData({
        from: emailData.from,
        subject: emailData.subject,
        receivedDate: emailData.receivedDate,
        content: emailData.content,
        attachments: emailData.attachments
      })

      // Create a new smart intake result from the email
      const newResult: SmartIntakeResult = {
        id: response.run_id || `email_${Date.now()}`,
        description: emailData.subject,
        contact: emailData.from,
        date: new Date().toISOString().slice(0, 16).replace('T', ' '),
        cotNumber: `TK-${new Date().getFullYear()}-${String(smartIntakeResults.length + 1).padStart(3, '0')}`,
        preAnalysis: 'Completo',
        status: 'processing',
        company: emailData.from.split('@')[1]
      }

      // Add to the results list
      setSmartIntakeResults(prev => [newResult, ...prev])

      console.log('Email processed successfully:', response)
    } catch (error) {
      console.error('Error processing email:', error)
      
      // Still add to results for demo purposes
      const newResult: SmartIntakeResult = {
        id: `email_${Date.now()}`,
        description: emailData.subject,
        contact: emailData.from,
        date: new Date().toISOString().slice(0, 16).replace('T', ' '),
        cotNumber: `TK-${new Date().getFullYear()}-${String(smartIntakeResults.length + 1).padStart(3, '0')}`,
        preAnalysis: 'Completo',
        status: 'pending',
        company: emailData.from.split('@')[1]
      }

      setSmartIntakeResults(prev => [newResult, ...prev])
    } finally {
      setIsProcessingEmail(false)
    }
  }

  const handleProcess = (id: string) => {
    console.log('Processing result:', id)
    // Find the selected case
    const caseToProcess = smartIntakeResults.find(result => result.id === id)
    if (caseToProcess) {
      setSelectedCase(caseToProcess)
      setCurrentView('claveteador')
    }
  }

  const handleBackToDashboard = () => {
    setCurrentView('dashboard')
    setSelectedCase(null)
  }

  const handleProceedToMatching = () => {
    console.log('Proceeding to vehicle matching...')
    setCurrentView('vehicleMatching')
  }

  const handleBackToClaveteador = () => {
    setCurrentView('claveteador')
  }

  const handleValidateAmis = () => {
    console.log('Validating AMIS codes...')
    setCurrentView('export')
  }

  const handleGoToExport = () => {
    console.log('Going to export...')
    setCurrentView('export')
  }

  const handleBackToVehicleMatching = () => {
    setCurrentView('vehicleMatching')
  }

  const handleAskInfo = (id: string) => {
    console.log('Asking for more info for result:', id)
    // In a real app, this would open a dialog or send a request for more information
    alert('Request for additional information sent to the broker.')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  // Render Claveteador view if selected
  if (currentView === 'claveteador' && selectedCase) {
    return (
      <Claveteador
        caseData={{
          cliente: selectedCase.company || 'TRANSPORTES BOLIVAR SA DE CV',
          cot: selectedCase.cotNumber,
          brokerName: selectedCase.contact.split('@')[0].replace('.', ' ').toUpperCase(),
          brokerEmail: selectedCase.contact,
          requestType: 'Fleet Quotation',
          subject: selectedCase.description,
          from: selectedCase.contact,
          date: selectedCase.date,
          content: `Estimado equipo de suscripción,

Les envío la solicitud de cotización para la flota de la empresa ${selectedCase.company || 'TRANSPORTES BOLIVAR SA DE CV'}.

Adjunto encontrarán el Excel con el detalle de 40 vehículos para cobertura amplia.

Saludos cordiales,
${selectedCase.contact.split('@')[0].replace('.', ' ')}`
        }}
        onProceedToMatching={handleProceedToMatching}
        onBack={handleBackToDashboard}
      />
    )
  }

  // Render VehicleMatching view if selected
  if (currentView === 'vehicleMatching' && selectedCase) {
    return (
      <VehicleMatching
        caseData={{
          cliente: selectedCase.company || 'TRANSPORTES BOLIVAR SA DE CV',
          cot: selectedCase.cotNumber
        }}
        onValidate={handleValidateAmis}
        onGoToExport={handleGoToExport}
        onBack={handleBackToClaveteador}
      />
    )
  }

  // Render ExcelExport view if selected
  if (currentView === 'export' && selectedCase) {
    return (
      <ExcelExport
        caseData={{
          cliente: selectedCase.company || 'TRANSPORTES BOLIVAR SA DE CV',
          cot: selectedCase.cotNumber
        }}
        onBack={handleBackToVehicleMatching}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
                  <span className="text-white font-bold text-sm">M</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900">MincaAI tool</h1>
              </div>
              
              {/* Navigation steps */}
              <nav className="hidden md:flex ml-8 space-x-8">
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    1
                  </div>
                  <span className="text-sm font-medium text-blue-600">Smart Intake</span>
                </div>
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-gray-300 text-gray-600 rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    2
                  </div>
                  <span className="text-sm text-gray-500">Claveteador</span>
                </div>
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-gray-300 text-gray-600 rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    3
                  </div>
                  <span className="text-sm text-gray-500">Export</span>
                </div>
              </nav>
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
                <span className="text-sm text-gray-600">System Online</span>
              </div>
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">A</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SmartIntakeResults
          results={smartIntakeResults}
          onProcess={handleProcess}
          onAskInfo={handleAskInfo}
        />
      </main>

      {/* Quick Email Input - Floating Action Button */}
      <QuickEmailInput
        onSubmit={handleEmailSubmit}
        isProcessing={isProcessingEmail}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center text-sm text-gray-500">
            <div>
              © 2024 MincaAI. Smart underwriting platform.
            </div>
            <div className="flex space-x-4">
              <span>API Status: Online</span>
              <span>•</span>
              <span>Version: 1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
