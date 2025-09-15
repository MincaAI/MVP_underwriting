'use client'

import { useState } from 'react'

interface Vehicle {
  id: string
  status: 'complete' | 'missing' | 'uncertain' | 'failed'
  paquete: string
  marca: string
  descripcion: string
  serie: string
  año: number
  cobertura: string
  sumaAsegurada: string
  amis: string
  amisStatus: 'ok' | 'fail' | 'missing'
}

interface VehicleMatchingProps {
  caseData: {
    cliente: string
    cot: string
  }
  onValidate: () => void
  onGoToExport: () => void
  onBack: () => void
}

export default function VehicleMatching({ caseData, onValidate, onGoToExport, onBack }: VehicleMatchingProps) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([
    {
      id: '1',
      status: 'complete',
      paquete: 'AMPL-001',
      marca: 'NISSAN',
      descripcion: 'NISSAN (2016)',
      serie: '1G1BC5SM5J7123789',
      año: 2016,
      cobertura: 'Limitada',
      sumaAsegurada: '$433,076',
      amis: 'Missing',
      amisStatus: 'fail'
    },
    {
      id: '2',
      status: 'complete',
      paquete: 'AMPL-002',
      marca: 'CHEVROLET',
      descripcion: 'CHEVROLET (2017)',
      serie: 'JTDBE40E399456123',
      año: 2017,
      cobertura: 'RC',
      sumaAsegurada: '$283,748',
      amis: 'CORO4',
      amisStatus: 'ok'
    },
    {
      id: '3',
      status: 'complete',
      paquete: 'AMPL-034',
      marca: 'FORD',
      descripcion: 'FORD (2017)',
      serie: 'WAULV44E77N456789',
      año: 2017,
      cobertura: 'Limitada',
      sumaAsegurada: '$279,607',
      amis: 'RANG4',
      amisStatus: 'ok'
    },
    {
      id: '4',
      status: 'complete',
      paquete: 'AMPL-035',
      marca: 'HONDA',
      descripcion: 'HONDA (2018)',
      serie: 'KMHL14JA3EA123456',
      año: 2018,
      cobertura: 'RC',
      sumaAsegurada: '$395,140',
      amis: 'CRUZ4',
      amisStatus: 'ok'
    },
    {
      id: '5',
      status: 'complete',
      paquete: 'AMPL-036',
      marca: 'VOLKSWAGEN',
      descripcion: 'VOLKSWAGEN (2019)',
      serie: '3N1AB7AP1KL123456',
      año: 2019,
      cobertura: 'Amplia',
      sumaAsegurada: '$308,600',
      amis: 'SENT4',
      amisStatus: 'ok'
    },
    {
      id: '6',
      status: 'complete',
      paquete: 'AMPL-037',
      marca: 'NISSAN',
      descripcion: 'NISSAN (2020)',
      serie: '1G1BC5SM5J7123789',
      año: 2020,
      cobertura: 'Limitada',
      sumaAsegurada: '$280,368',
      amis: 'FIES4',
      amisStatus: 'ok'
    },
    {
      id: '7',
      status: 'complete',
      paquete: 'AMPL-038',
      marca: 'CHEVROLET',
      descripcion: 'CHEVROLET (2021)',
      serie: 'JTDBE40E399456123',
      año: 2021,
      cobertura: 'RC',
      sumaAsegurada: '$413,262',
      amis: 'SPAR4',
      amisStatus: 'ok'
    },
    {
      id: '8',
      status: 'complete',
      paquete: 'AMPL-039',
      marca: 'TOYOTA',
      descripcion: 'TOYOTA (2022)',
      serie: '1HGBH41JXMN789456',
      año: 2022,
      cobertura: 'Amplia',
      sumaAsegurada: '$441,047',
      amis: 'Missing',
      amisStatus: 'fail'
    },
    {
      id: '9',
      status: 'missing',
      paquete: 'AMPL-040',
      marca: 'FORD',
      descripcion: 'FORD (2015)',
      serie: 'Missing',
      año: 2015,
      cobertura: 'Limitada',
      sumaAsegurada: 'Missing',
      amis: 'Missing',
      amisStatus: 'fail'
    }
  ])

  const [filter, setFilter] = useState('All AMIS')
  const [editingCell, setEditingCell] = useState<{ vehicleId: string; field: string } | null>(null)

  // Calculate summary statistics
  const totalVehicles = 40
  const amisFound = vehicles.filter(v => v.amisStatus === 'ok').length
  const uncertain = vehicles.filter(v => v.status === 'uncertain').length
  const failed = vehicles.filter(v => v.amisStatus === 'fail').length

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <span className="text-green-600 font-medium">✓ Complete</span>
      case 'missing':
        return <span className="text-yellow-600 font-medium">⚠ Missing VIN, Suma</span>
      case 'uncertain':
        return <span className="text-orange-600 font-medium">? Uncertain</span>
      case 'failed':
        return <span className="text-red-600 font-medium">✗ Failed</span>
      default:
        return status
    }
  }

  const getAmisStatus = (amisStatus: string, amis: string) => {
    if (amis === 'Missing' || amisStatus === 'fail') {
      return <span className="text-red-600 font-medium">FAIL</span>
    } else if (amisStatus === 'ok') {
      return <span className="text-green-600 font-medium">OK</span>
    }
    return <span className="text-gray-600">-</span>
  }

  const handleCellEdit = (vehicleId: string, field: string, value: string) => {
    setVehicles(prev => 
      prev.map(vehicle => 
        vehicle.id === vehicleId 
          ? { ...vehicle, [field]: value }
          : vehicle
      )
    )
    setEditingCell(null)
  }

  const handleValidate = () => {
    console.log('Validating AMIS codes...')
    onValidate()
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
              <button
                onClick={onGoToExport}
                className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
              >
                Go to Export
              </button>
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
        {/* Page Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Claveteador AMIS</h2>
              <div className="flex items-center space-x-6 mt-2 text-sm text-gray-600">
                <div>
                  <span className="font-medium">Cliente:</span> {caseData.cliente}
                </div>
                <div>
                  <span className="font-medium">COT:</span> {caseData.cot}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Codification Results Summary */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Codification Results</h3>
          <div className="grid grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-500">Total Vehicles:</div>
              <div className="text-2xl font-bold text-gray-900">{totalVehicles}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">AMIS Found:</div>
              <div className="text-2xl font-bold text-green-600">{amisFound}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Uncertain:</div>
              <div className="text-2xl font-bold text-yellow-600">{uncertain}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Failed:</div>
              <div className="text-2xl font-bold text-red-600">{failed}</div>
            </div>
          </div>
        </div>

        {/* Vehicles Data Table */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Vehicles Data</h3>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="All AMIS">All AMIS</option>
                <option value="Found">AMIS Found</option>
                <option value="Missing">AMIS Missing</option>
                <option value="Failed">Failed</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Paquete</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Marca</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Descripción</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serie (VIN)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Año</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cobertura</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Suma Asegurada</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AMIS</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {vehicles.map((vehicle) => (
                  <tr key={vehicle.id} className="hover:bg-gray-50">
                    <td className="px-3 py-4 text-sm">
                      {getStatusIcon(vehicle.status)}
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.paquete}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.marca}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">
                      {editingCell?.vehicleId === vehicle.id && editingCell?.field === 'descripcion' ? (
                        <input
                          type="text"
                          value={vehicle.descripcion}
                          onChange={(e) => handleCellEdit(vehicle.id, 'descripcion', e.target.value)}
                          onBlur={() => setEditingCell(null)}
                          onKeyPress={(e) => e.key === 'Enter' && setEditingCell(null)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          autoFocus
                        />
                      ) : (
                        <span
                          onClick={() => setEditingCell({ vehicleId: vehicle.id, field: 'descripcion' })}
                          className="cursor-pointer hover:bg-gray-100 px-1 rounded"
                        >
                          {vehicle.descripcion}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-4 text-sm">
                      {editingCell?.vehicleId === vehicle.id && editingCell?.field === 'serie' ? (
                        <input
                          type="text"
                          value={vehicle.serie}
                          onChange={(e) => handleCellEdit(vehicle.id, 'serie', e.target.value)}
                          onBlur={() => setEditingCell(null)}
                          onKeyPress={(e) => e.key === 'Enter' && setEditingCell(null)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          autoFocus
                        />
                      ) : (
                        <span
                          onClick={() => setEditingCell({ vehicleId: vehicle.id, field: 'serie' })}
                          className={`cursor-pointer hover:bg-gray-100 px-1 rounded ${
                            vehicle.serie === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'
                          }`}
                        >
                          {vehicle.serie}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.año}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.cobertura}</td>
                    <td className="px-3 py-4 text-sm">
                      {editingCell?.vehicleId === vehicle.id && editingCell?.field === 'sumaAsegurada' ? (
                        <input
                          type="text"
                          value={vehicle.sumaAsegurada}
                          onChange={(e) => handleCellEdit(vehicle.id, 'sumaAsegurada', e.target.value)}
                          onBlur={() => setEditingCell(null)}
                          onKeyPress={(e) => e.key === 'Enter' && setEditingCell(null)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          autoFocus
                        />
                      ) : (
                        <span
                          onClick={() => setEditingCell({ vehicleId: vehicle.id, field: 'sumaAsegurada' })}
                          className={`cursor-pointer hover:bg-gray-100 px-1 rounded ${
                            vehicle.sumaAsegurada === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'
                          }`}
                        >
                          {vehicle.sumaAsegurada}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-4 text-sm">
                      <div className="flex items-center space-x-2">
                        {editingCell?.vehicleId === vehicle.id && editingCell?.field === 'amis' ? (
                          <input
                            type="text"
                            value={vehicle.amis}
                            onChange={(e) => handleCellEdit(vehicle.id, 'amis', e.target.value)}
                            onBlur={() => setEditingCell(null)}
                            onKeyPress={(e) => e.key === 'Enter' && setEditingCell(null)}
                            className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                            autoFocus
                          />
                        ) : (
                          <span
                            onClick={() => setEditingCell({ vehicleId: vehicle.id, field: 'amis' })}
                            className={`cursor-pointer hover:bg-gray-100 px-1 rounded ${
                              vehicle.amis === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'
                            }`}
                          >
                            {vehicle.amis}
                          </span>
                        )}
                        {getAmisStatus(vehicle.amisStatus, vehicle.amis)}
                      </div>
                    </td>
                    <td className="px-3 py-4 text-sm">
                      <button className="text-blue-600 hover:text-blue-800">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-6 py-4 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Showing 1 to {vehicles.length} of {totalVehicles} vehicles
              </div>
              <div className="flex items-center space-x-2">
                <button className="px-3 py-1 border border-gray-300 rounded text-sm text-gray-500 cursor-not-allowed">
                  ‹
                </button>
                <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm">
                  1
                </button>
                <button className="px-3 py-1 border border-gray-300 rounded text-sm text-gray-500 cursor-not-allowed">
                  ›
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Validate Button */}
        <div className="flex justify-center mt-8">
          <button
            onClick={handleValidate}
            className="bg-green-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-green-700 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            VALIDATE CLAVE AMIS
          </button>
        </div>
      </main>
    </div>
  )
}
