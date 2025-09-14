'use client'

import { useState } from 'react'

interface FinalVehicle {
  id: string
  marca: string
  serie: string
  año: number
  paquete: string
  tipoServicio: string
  tipoUso: string
  valorVehiculo: string
  dedDmPp: string
  dedDmPt: string
  dedRt: string
  saRcLuc: string
  aJuridica: string
}

interface ExcelExportProps {
  caseData: {
    cliente: string
    cot: string
  }
  onBack: () => void
}

export default function ExcelExport({ caseData, onBack }: ExcelExportProps) {
  const [discountPercentage, setDiscountPercentage] = useState(15)

  const [finalVehicles] = useState<FinalVehicle[]>([
    {
      id: '1',
      marca: 'NISSAN',
      serie: '1G1BC5SM5J7123789',
      año: 2016,
      paquete: 'AMPL-001',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$433,076',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '2',
      marca: 'CHEVROLET',
      serie: 'JTDBE40E399456123',
      año: 2017,
      paquete: 'AMPL-002',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$283,748',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '3',
      marca: 'TOYOTA',
      serie: '1HGBH41JXMN789456',
      año: 2018,
      paquete: 'AMPL-003',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$260,157',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '4',
      marca: 'FORD',
      serie: 'JN1CV6EK5CM123789',
      año: 2019,
      paquete: 'AMPL-004',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$335,266',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '5',
      marca: 'VOLKSWAGEN',
      serie: '3N1AB7AP1KL123456',
      año: 2019,
      paquete: 'AMPL-036',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$308,600',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '6',
      marca: 'NISSAN',
      serie: '1G1BC5SM5J7123789',
      año: 2020,
      paquete: 'AMPL-037',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$280,368',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '7',
      marca: 'CHEVROLET',
      serie: 'JTDBE40E399456123',
      año: 2021,
      paquete: 'AMPL-038',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$413,262',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '8',
      marca: 'TOYOTA',
      serie: '1HGBH41JXMN789456',
      año: 2022,
      paquete: 'AMPL-039',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$441,047',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    },
    {
      id: '9',
      marca: 'FORD',
      serie: 'N/A',
      año: 2015,
      paquete: 'AMPL-040',
      tipoServicio: 'particular',
      tipoUso: 'normal',
      valorVehiculo: '$800,000',
      dedDmPp: '3%',
      dedDmPt: '10%',
      dedRt: '10%',
      saRcLuc: '$4,000,000',
      aJuridica: 'AMPARADA'
    }
  ])

  const handleDownloadExcel = () => {
    console.log(`Downloading Excel with ${discountPercentage}% discount...`)
    // In a real implementation, this would generate and download the Excel file
    alert(`Excel Cotizador downloaded with ${discountPercentage}% agent discount!`)
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
                  <div className="w-6 h-6 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    ✓
                  </div>
                  <span className="text-sm text-green-600">Claveteador</span>
                </div>
                <div className="flex items-center">
                  <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium mr-2">
                    3
                  </div>
                  <span className="text-sm font-medium text-blue-600">Export</span>
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
        {/* Page Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Excel Export</h2>
              <div className="flex items-center space-x-6 mt-2 text-sm text-gray-600">
                <div>
                  <span className="font-medium">Cliente:</span> {caseData.cliente}
                </div>
                <div>
                  <span className="font-medium">COT:</span> {caseData.cot}
                </div>
              </div>
            </div>
            <div className="flex items-center">
              <div className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                Ready for Export
              </div>
            </div>
          </div>
        </div>

        {/* Final Vehicles Data Table */}
        <div className="bg-white rounded-lg shadow-sm mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Final Vehicles Data</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Marca</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serie (VIN)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Año</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Paquete</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo Servicio</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo de Uso</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Valor Vehiculo</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DED DM PP</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DED DM PT</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DED RT</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SA RC LUC</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">A. JURIDICA</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {finalVehicles.map((vehicle) => (
                  <tr key={vehicle.id} className="hover:bg-gray-50">
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.marca}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.serie}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.año}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.paquete}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.tipoServicio}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.tipoUso}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.valorVehiculo}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.dedDmPp}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.dedDmPt}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.dedRt}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.saRcLuc}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.aJuridica}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="px-6 py-4 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              Showing all {finalVehicles.length} vehicles with editable Mexican insurance columns.
            </div>
          </div>
        </div>

        {/* Agent Discount Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Agent Discount</h3>
          <div className="flex items-center space-x-4">
            <label htmlFor="discount" className="text-sm font-medium text-gray-700">
              Discount Percentage:
            </label>
            <div className="flex items-center">
              <input
                type="number"
                id="discount"
                value={discountPercentage}
                onChange={(e) => setDiscountPercentage(Number(e.target.value))}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm w-20 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="0"
                max="100"
              />
              <span className="ml-2 text-sm text-gray-700">%</span>
            </div>
          </div>
        </div>

        {/* Download Button */}
        <div className="flex justify-center">
          <button
            onClick={handleDownloadExcel}
            className="bg-green-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-green-700 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Excel Cotizador ({discountPercentage}% discount)
          </button>
        </div>
      </main>
    </div>
  )
}
