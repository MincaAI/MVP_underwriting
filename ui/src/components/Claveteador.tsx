'use client'

import { useState } from 'react'

interface CompanyInfo {
  nombre: string
  rfc: string
  domicilio: string
  actividad: string
  uso: string
  formaPago: string
  vigenciaDesde: string
  vigenciaHasta: string
  cobertura: string
  primaNeta: string
  transporta: string
}

interface CoverageItem {
  name: string
  sumaAsegurada: string
  deducible: string
  checked: boolean
}

interface CoverageSection {
  title: string
  items: CoverageItem[]
}

interface Attachment {
  name: string
  type: string
  vehicleCount?: number
  description: string
}

interface ClaveteadorProps {
  caseData: {
    cliente: string
    cot: string
    brokerName: string
    brokerEmail: string
    requestType: string
    subject: string
    from: string
    date: string
    content: string
  }
  onProceedToMatching: () => void
  onBack: () => void
}

export default function Claveteador({ caseData, onProceedToMatching, onBack }: ClaveteadorProps) {
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo>({
    nombre: 'TRANSPORTES BOLIVAR SA DE CV',
    rfc: 'TBO850312A27',
    domicilio: 'AV. INSURGENTES SUR 1234, COL. DEL VALLE',
    actividad: 'TRANSPORTE DE CARGA',
    uso: 'COMERCIAL',
    formaPago: 'ANUAL',
    vigenciaDesde: '2024-01-01',
    vigenciaHasta: '2024-12-31',
    cobertura: 'Not specified',
    primaNeta: 'Not specified',
    transporta: 'Not specified'
  })

  const [coverageSections, setCoverageSections] = useState<CoverageSection[]>([
    {
      title: 'Auto',
      items: [
        { name: 'DAÑOS MATERIALES', sumaAsegurada: '$250,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'ROBO TOTAL', sumaAsegurada: '$500,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS', sumaAsegurada: '$750,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL BIENES', sumaAsegurada: '40%', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL PERSONAS', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'GASTOS MÉDICOS OCUPANTES', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'AUTO PROTEGIDO EMME', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'SEGURO DE LLANTAS Y RINES', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false }
      ]
    },
    {
      title: 'Remolques',
      items: [
        { name: 'DAÑOS MATERIALES', sumaAsegurada: '$250,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'ROBO TOTAL', sumaAsegurada: '$500,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS', sumaAsegurada: '$750,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL BIENES', sumaAsegurada: '40%', deducible: 'A) 3.00 %', checked: true }
      ]
    },
    {
      title: 'Camiones Pesado',
      items: [
        { name: 'DAÑOS MATERIALES', sumaAsegurada: '$250,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'ROBO TOTAL', sumaAsegurada: '$500,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS', sumaAsegurada: '$750,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL BIENES', sumaAsegurada: '40%', deducible: 'A) 3.00 %', checked: true },
        { name: 'Opera Sub-límite sobre la RESPONSABILIDAD CIVIL TERCEROS', sumaAsegurada: '50%', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL PERSONAS', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'RESPONSABILIDAD CIVIL FAMILIAR', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'GASTOS MÉDICOS OCUPANTES', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'ASISTENCIA EN VIAJE CDS', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false }
      ]
    },
    {
      title: 'Moto',
      items: [
        { name: 'DAÑOS MATERIALES', sumaAsegurada: '$250,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'ROBO TOTAL', sumaAsegurada: '$500,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS', sumaAsegurada: '$750,000', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL BIENES', sumaAsegurada: '40%', deducible: 'A) 3.00 %', checked: true },
        { name: 'RESPONSABILIDAD CIVIL PERSONAS', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false },
        { name: 'GASTOS MÉDICOS OCUPANTES', sumaAsegurada: 'NO APLICA', deducible: 'NO APLICA', checked: false }
      ]
    }
  ])

  const [attachments] = useState<Attachment[]>([
    {
      name: 'fleet_vehicles_40.xlsx',
      type: 'excel',
      vehicleCount: 40,
      description: 'Excel attachment • 40 vehicles detected • Type: excel'
    }
  ])

  const [claimsHistory] = useState([
    {
      name: 'claims_history_report.pdf',
      description: 'Claims report • Last 3 years • 8 total claims • $104,500 total'
    }
  ])

  const handleCompanyInfoChange = (field: keyof CompanyInfo, value: string) => {
    setCompanyInfo(prev => ({ ...prev, [field]: value }))
  }

  const handleCoverageToggle = (sectionIndex: number, itemIndex: number) => {
    setCoverageSections(prev => 
      prev.map((section, sIdx) => 
        sIdx === sectionIndex 
          ? {
              ...section,
              items: section.items.map((item, iIdx) => 
                iIdx === itemIndex ? { ...item, checked: !item.checked } : item
              )
            }
          : section
      )
    )
  }

  const handleValidate = () => {
    console.log('Validating company information...')
    alert('Company information validated successfully!')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <button
                onClick={onBack}
                className="flex items-center text-gray-600 hover:text-gray-900 mr-4"
              >
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>
              
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
                  <span className="text-white font-bold text-sm">M</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900">MincaAI tool</h1>
              </div>
              
              {/* Navigation steps */}
              <nav className="hidden md:flex ml-8 space-x-8">
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    ✓
                  </div>
                  <span className="text-sm text-green-600">Smart Intake</span>
                </div>
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    2
                  </div>
                  <span className="text-sm font-medium text-blue-600">Claveteador</span>
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
        {/* Case Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Smart Intake</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">Cliente:</span> {caseData.cliente}
            </div>
            <div>
              <span className="font-medium text-gray-700">COT:</span> {caseData.cot}
            </div>
          </div>
        </div>

        {/* Smart Intake Email */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center mb-4">
            <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900">Smart Intake - Email</h3>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <span className="font-medium text-gray-700">Subject:</span> {caseData.subject}
              </div>
              <div>
                <span className="font-medium text-gray-700">From:</span> {caseData.from}
              </div>
              <div>
                <span className="font-medium text-gray-700">Date:</span> {caseData.date}
              </div>
              <div>
                <span className="font-medium text-gray-700">Content:</span>
                <p className="mt-1 text-gray-600 text-sm bg-gray-50 p-3 rounded">
                  {caseData.content}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <span className="font-medium text-gray-700">Broker Name:</span>
                <input
                  type="text"
                  value={caseData.brokerName}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  readOnly
                />
              </div>
              <div>
                <span className="font-medium text-gray-700">Broker Email:</span>
                <input
                  type="email"
                  value={caseData.brokerEmail}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  readOnly
                />
              </div>
              <div>
                <span className="font-medium text-gray-700">Request Type:</span>
                <select
                  value={caseData.requestType}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option>Fleet Quotation</option>
                  <option>Individual Quote</option>
                  <option>Renewal</option>
                </select>
              </div>
              <div>
                <span className="font-medium text-gray-700">Coverage Type:</span>
                <select
                  value="Comprehensive (Amplia)"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option>Comprehensive (Amplia)</option>
                  <option>Limited</option>
                  <option>Basic</option>
                </select>
              </div>
              <div>
                <span className="font-medium text-gray-700">Fleet Size:</span>
                <input
                  type="number"
                  value="40"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Attachments */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center mb-4">
            <svg className="w-5 h-5 text-orange-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900">Attachments</h3>
          </div>

          {attachments.map((attachment, index) => (
            <div key={index} className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center">
                <svg className="w-8 h-8 text-green-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                  <div className="font-medium text-gray-900">{attachment.name}</div>
                  <div className="text-sm text-gray-500">{attachment.description}</div>
                </div>
              </div>
              <button className="bg-green-100 text-green-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-green-200">
                Download Excel
              </button>
            </div>
          ))}
        </div>

        {/* Company Information */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h4M9 7h6m-6 4h6m-2 4h2M9 15h2" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900">Company Information</h3>
            </div>
            <button
              onClick={handleValidate}
              className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Validate
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre *</label>
                <input
                  type="text"
                  value={companyInfo.nombre}
                  onChange={(e) => handleCompanyInfoChange('nombre', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">RFC *</label>
                <input
                  type="text"
                  value={companyInfo.rfc}
                  onChange={(e) => handleCompanyInfoChange('rfc', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Domicilio *</label>
                <input
                  type="text"
                  value={companyInfo.domicilio}
                  onChange={(e) => handleCompanyInfoChange('domicilio', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Actividad</label>
                <input
                  type="text"
                  value={companyInfo.actividad}
                  onChange={(e) => handleCompanyInfoChange('actividad', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Uso *</label>
                <select
                  value={companyInfo.uso}
                  onChange={(e) => handleCompanyInfoChange('uso', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="COMERCIAL">COMERCIAL</option>
                  <option value="PARTICULAR">PARTICULAR</option>
                  <option value="PUBLICO">PUBLICO</option>
                </select>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Vigencia Desde *</label>
                <input
                  type="date"
                  value={companyInfo.vigenciaDesde}
                  onChange={(e) => handleCompanyInfoChange('vigenciaDesde', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Vigencia Hasta *</label>
                <input
                  type="date"
                  value={companyInfo.vigenciaHasta}
                  onChange={(e) => handleCompanyInfoChange('vigenciaHasta', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Cobertura</label>
                <input
                  type="text"
                  value={companyInfo.cobertura}
                  onChange={(e) => handleCompanyInfoChange('cobertura', e.target.value)}
                  className="mt-1 block w-full border border-yellow-300 rounded-md px-3 py-2 text-sm bg-yellow-50"
                  placeholder="Not specified"
                />
                <p className="text-xs text-orange-600 mt-1">Missing field</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Prima Neta Objetivo</label>
                <input
                  type="text"
                  value={companyInfo.primaNeta}
                  onChange={(e) => handleCompanyInfoChange('primaNeta', e.target.value)}
                  className="mt-1 block w-full border border-yellow-300 rounded-md px-3 py-2 text-sm bg-yellow-50"
                  placeholder="Not specified"
                />
                <p className="text-xs text-orange-600 mt-1">Missing field</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Transporta</label>
                <input
                  type="text"
                  value={companyInfo.transporta}
                  onChange={(e) => handleCompanyInfoChange('transporta', e.target.value)}
                  className="mt-1 block w-full border border-yellow-300 rounded-md px-3 py-2 text-sm bg-yellow-50"
                  placeholder="Not specified"
                />
                <p className="text-xs text-orange-600 mt-1">Missing field</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Forma de Pago *</label>
                <select
                  value={companyInfo.formaPago}
                  onChange={(e) => handleCompanyInfoChange('formaPago', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="ANUAL">ANUAL</option>
                  <option value="SEMESTRAL">SEMESTRAL</option>
                  <option value="TRIMESTRAL">TRIMESTRAL</option>
                  <option value="MENSUAL">MENSUAL</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Requested Coverage */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center mb-6">
            <svg className="w-5 h-5 text-purple-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900">Requested Coverage</h3>
          </div>

          <div className="space-y-6">
            {coverageSections.map((section, sectionIndex) => (
              <div key={sectionIndex}>
                <div className="bg-blue-600 text-white px-4 py-2 rounded-t-lg">
                  <h4 className="font-medium">{section.title}</h4>
                </div>
                <div className="border border-gray-200 rounded-b-lg overflow-hidden">
                  <table className="min-w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Coberturas amparadas</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Suma asegurada</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Deducible</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {section.items.map((item, itemIndex) => (
                        <tr key={itemIndex} className={item.checked ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-4 py-2">
                            <div className="flex items-center">
                              <input
                                type="checkbox"
                                checked={item.checked}
                                onChange={() => handleCoverageToggle(sectionIndex, itemIndex)}
                                className="mr-3 h-4 w-4 text-blue-600 border-gray-300 rounded"
                              />
                              <span className={`text-sm ${item.checked ? 'text-gray-900' : 'text-gray-500'}`}>
                                {item.name}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.sumaAsegurada}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.deducible}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Claims History */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center mb-4">
            <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900">Claims History</h3>
          </div>

          {claimsHistory.map((claim, index) => (
            <div key={index} className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center">
                <svg className="w-8 h-8 text-red-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                  <div className="font-medium text-gray-900">{claim.name}</div>
                  <div className="text-sm text-gray-500">{claim.description}</div>
                </div>
              </div>
              <button className="bg-green-100 text-green-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-green-200">
                Download
              </button>
            </div>
          ))}
        </div>

        {/* Action Button */}
        <div className="flex justify-center">
          <button
            onClick={onProceedToMatching}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-blue-700 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Claveteador
          </button>
        </div>
      </main>
    </div>
  )
}
