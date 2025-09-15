# Frontend Application Documentation

The Next.js frontend provides a comprehensive user interface for the Minca AI Insurance Platform, enabling underwriters to manage cases, review vehicle matching results, and export reports.

## Application Overview

### **Purpose**
- Provide intuitive case management interface for insurance underwriters
- **Manual email intake system for testing smart workflows**
- **Intelligent broker profile management with AI-assisted generation**
- Display vehicle matching results with confidence indicators
- Enable manual review and editing of CVEGS codes
- Generate Excel reports and export functionality
- Monitor system performance and processing statistics

### **Technology Stack**
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript for type safety
- **Styling**: Tailwind CSS with custom insurance themes
- **State Management**: TanStack Query for server state
- **UI Components**: shadcn/ui with Radix UI primitives
- **Charts**: Recharts for data visualization
- **Icons**: Lucide React icon library

### **Port**: 3000 (configurable)

## Architecture

### **Application Structure**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend Application                 │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Dashboard     │  │ Manual Intake   │  │ Broker Profiles │ │
│  │                 │  │                 │  │                 │ │
│  │ • Stats Cards   │  │ • Email Entry   │  │ • Profile Mgmt  │ │
│  │ • Charts        │  │ • File Upload   │  │ • Auto-Generate │ │
│  │ • Recent Cases  │  │ • Attachments   │  │ • AI Wizard     │ │
│  │ • System Health │  │ • Real-time     │  │ • Confidence    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                 │                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Case Management │  │ Vehicle Review  │  │ Export & Report │ │
│  │                 │  │                 │  │                 │ │
│  │ • Case List     │  │ • CVEGS Grid    │  │ • Excel Export  │ │
│  │ • Search/Filter │  │ • Confidence    │  │ • PDF Reports   │ │
│  │ • Status Track  │  │ • Manual Edit   │  │ • Templates     │ │
│  │ • COT Numbers   │  │ • Batch Actions │  │ • Bulk Export   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Integration Layer                        │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Smart Intake    │  │ Vehicle Matcher │  │ Database        │ │
│  │ API Client      │  │ API Client      │  │ API Client      │ │
│  │                 │  │                 │  │                 │ │
│  │ • Email Status  │  │ • Match Results │  │ • Case Data     │ │
│  │ • Task Monitor  │  │ • Batch Process │  │ • Vehicle Info  │ │
│  │ • Reprocessing  │  │ • Statistics    │  │ • Search/Filter │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
frontend/smart-intake-ui/
├── package.json                  # Dependencies and scripts
├── next.config.js               # Next.js configuration with API proxies
├── tsconfig.json                # TypeScript configuration
├── tailwind.config.js           # Tailwind CSS with custom themes
└── src/
    ├── app/                     # Next.js App Router
    │   ├── layout.tsx           # Root layout with sidebar/header
    │   ├── page.tsx             # Home page (redirects to dashboard)
    │   ├── providers.tsx        # React Query and theme providers
    │   ├── globals.css          # Global styles and custom classes
    │   ├── dashboard/
    │   │   └── page.tsx         # Dashboard with statistics
    │   ├── cases/
    │   │   ├── page.tsx         # Case list view
    │   │   └── [cot]/
    │   │       └── page.tsx     # Case detail view
    │   ├── vehicles/
    │   │   └── page.tsx         # Vehicle management
    │   ├── reports/
    │   │   └── page.tsx         # Export and reporting
    │   └── settings/
    │       └── page.tsx         # System settings
    ├── components/
    │   ├── ui/                  # shadcn/ui base components
    │   ├── layout/              # Layout components (sidebar, header)
    │   ├── dashboard/           # Dashboard-specific components
    │   ├── ManualIntakeForm.tsx # Manual email entry form
    │   ├── BrokerProfileManager.tsx # Broker profile management
    │   ├── ProfileGenerationWizard.tsx # AI-assisted profile creation
    │   ├── cases/               # Case management components
    │   ├── vehicles/            # Vehicle grid components
    │   ├── documents/           # Document viewer components
    │   └── charts/              # Data visualization components
    └── lib/
        ├── api/                 # API integration layer
        │   ├── client.ts        # HTTP client configuration
        │   └── services.ts      # Service-specific API methods
        ├── types/               # TypeScript type definitions
        │   └── index.ts         # Complete type system
        ├── hooks/               # Custom React hooks
        ├── utils/               # Utility functions
        └── constants/           # Application constants
```

## Key Features

### **🔄 Claveteador Workflow System**

The Claveteador workflow provides a complete end-to-end process for insurance case processing, from smart intake through vehicle matching to final export.

#### **Workflow Overview**
```
Smart Intake → Claveteador → Vehicle Matching → Excel Export
     ↓              ↓              ↓              ↓
Email Processing  Data Review   AMIS Matching   Final Export
Attachment Parse  Form Validation  Code Assignment  Excel Generation
Broker Detection  Coverage Setup   Manual Editing   Agent Discount
```

#### **Smart Intake Results Dashboard**
```typescript
// Main dashboard showing processed smart intake results
export default function SmartIntakeResults({ results, onProcess, onAskInfo }: SmartIntakeResultsProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="bg-green-100 text-green-800">✓ Completo</span>
      case 'processing':
        return <span className="bg-blue-100 text-blue-800">⏳ Processing</span>
      case 'pending':
        return <span className="bg-yellow-100 text-yellow-800">⏸ Pending</span>
      case 'error':
        return <span className="bg-red-100 text-red-800">⚠ Error</span>
    }
  }

  const getPreAnalysisBadge = (preAnalysis: string) => {
    return preAnalysis === 'Completo' 
      ? <span className="bg-green-100 text-green-800">✓ Completo</span>
      : <span className="bg-orange-100 text-orange-800">⚠ Incompleto</span>
  }

  return (
    <div className="bg-white shadow-sm rounded-lg">
      {/* Filters and search */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex items-center space-x-4">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="Tous">Tous</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results table */}
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th>Description</th>
            <th>COT</th>
            <th>Pre Analysis</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.id}>
              <td>{result.description}</td>
              <td>{result.cotNumber}</td>
              <td>{getPreAnalysisBadge(result.preAnalysis)}</td>
              <td>{getStatusBadge(result.status)}</td>
              <td>
                {result.preAnalysis === 'Incompleto' ? (
                  <button onClick={() => onAskInfo(result.id)}>Ask info</button>
                ) : (
                  <button onClick={() => onProcess(result.id)}>Process</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

#### **Claveteador Component**
```typescript
// Data preprocessing and validation interface
export default function Claveteador({ caseData, onProceedToMatching, onBack }: ClaveteadorProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation header */}
      <header className="bg-white border-b border-gray-200">
        <nav className="flex items-center space-x-8">
          <div className="flex items-center">
            <div className="w-6 h-6 bg-green-500 text-white rounded-full">✓</div>
            <span className="text-green-600">Smart Intake</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full">2</div>
            <span className="text-blue-600">Claveteador</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-gray-300 text-gray-600 rounded-full">3</div>
            <span className="text-gray-500">Export</span>
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Smart Intake Email Display */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">📧 Smart Intake - Email</h2>
          <div className="space-y-2">
            <div><strong>Subject:</strong> {caseData.subject}</div>
            <div><strong>From:</strong> {caseData.from}</div>
            <div><strong>Date:</strong> {caseData.date}</div>
            <div><strong>Content:</strong></div>
            <div className="bg-gray-50 p-4 rounded">{caseData.content}</div>
          </div>
        </div>

        {/* Email Processing Details */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-medium mb-4">📋 Email Processing Details</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium">Broker Name</label>
              <input value={caseData.brokerName} readOnly className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium">Request Type</label>
              <select value={caseData.requestType} className="w-full border rounded px-3 py-2">
                <option>Fleet Quotation</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Fleet Size</label>
              <input value="40" readOnly className="w-full border rounded px-3 py-2" />
            </div>
          </div>
        </div>

        {/* Attachments */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-medium mb-4">📎 Attachments</h3>
          <div className="flex items-center justify-between p-4 border rounded">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-green-100 rounded mr-3">📄</div>
              <div>
                <div className="font-medium">fleet_vehicles_40.xlsx</div>
                <div className="text-sm text-gray-500">Excel attachment • 40 vehicles detected • Type: excel</div>
              </div>
            </div>
            <button className="bg-green-100 text-green-800 px-3 py-1 rounded">Download Excel</button>
          </div>
        </div>

        {/* Company Information Form */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-medium mb-4">🏢 Company Information</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium">Nombre *</label>
              <input value="TRANSPORTES BOLIVAR SA DE CV" className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium">RFC *</label>
              <input value="TBO850312A27" className="w-full border rounded px-3 py-2" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium">Domicilio *</label>
              <input value="AV. INSURGENTES SUR 1234, COL. DEL VALLE" className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium">Actividad</label>
              <input value="TRANSPORTE DE CARGA" className="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium">Uso *</label>
              <select value="COMERCIAL" className="w-full border rounded px-3 py-2">
                <option>COMERCIAL</option>
              </select>
            </div>
          </div>
        </div>

        {/* Coverage Requirements */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-medium mb-4">🛡️ Requested Coverage</h3>
          
          {/* Auto Coverage */}
          <div className="mb-6">
            <h4 className="bg-blue-600 text-white px-4 py-2 rounded-t">Auto</h4>
            <table className="w-full border">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left">COBERTURAS AMPARADAS</th>
                  <th className="px-4 py-2 text-left">SUMA ASEGURADA</th>
                  <th className="px-4 py-2 text-left">DEDUCIBLE</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> DAÑOS MATERIALES
                  </td>
                  <td className="px-4 py-2">$250,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> ROBO TOTAL
                  </td>
                  <td className="px-4 py-2">$500,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> RESPONSABILIDAD CIVIL BIENES
                  </td>
                  <td className="px-4 py-2">40%</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Remolques Coverage */}
          <div className="mb-6">
            <h4 className="bg-blue-600 text-white px-4 py-2 rounded-t">Remolques</h4>
            <table className="w-full border">
              <tbody>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> DAÑOS MATERIALES
                  </td>
                  <td className="px-4 py-2">$250,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS
                  </td>
                  <td className="px-4 py-2">$750,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Moto Coverage */}
          <div className="mb-6">
            <h4 className="bg-blue-600 text-white px-4 py-2 rounded-t">Moto</h4>
            <table className="w-full border">
              <tbody>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> DAÑOS MATERIALES
                  </td>
                  <td className="px-4 py-2">$250,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked /> ROBO TOTAL
                  </td>
                  <td className="px-4 py-2">$500,000</td>
                  <td className="px-4 py-2">A) 3.00 %</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Claims History */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <h3 className="text-lg font-medium mb-4">📋 Claims History</h3>
          <div className="flex items-center justify-between p-4 border rounded">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-red-100 rounded mr-3">📄</div>
              <div>
                <div className="font-medium">claims_history_report.pdf</div>
                <div className="text-sm text-gray-500">Claims report • Last 3 years • 8 total claims • $104,500 total</div>
              </div>
            </div>
            <button className="bg-green-100 text-green-800 px-3 py-1 rounded">Download</button>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-center">
          <button
            onClick={onProceedToMatching}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-blue-700 flex items-center"
          >
            🔍 Claveteador
          </button>
        </div>
      </main>
    </div>
  )
}
```

#### **Vehicle Matching Component**
```typescript
// AMIS vehicle matching and validation interface
export default function VehicleMatching({ caseData, onValidate, onGoToExport, onBack }: VehicleMatchingProps) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [editingCell, setEditingCell] = useState<{ vehicleId: string; field: string } | null>(null)

  // Calculate summary statistics
  const totalVehicles = 40
  const amisFound = vehicles.filter(v => v.amisStatus === 'ok').length
  const uncertain = vehicles.filter(v => v.status === 'uncertain').length
  const failed = vehicles.filter(v => v.amisStatus === 'fail').length

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <span className="text-green-600">✓ Complete</span>
      case 'missing':
        return <span className="text-yellow-600">⚠ Missing VIN, Suma</span>
      case 'uncertain':
        return <span className="text-orange-600">? Uncertain</span>
      case 'failed':
        return <span className="text-red-600">✗ Failed</span>
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with navigation */}
      <header className="bg-white border-b border-gray-200">
        <nav className="flex items-center space-x-8">
          <div className="flex items-center">
            <div className="w-6 h-6 bg-green-500 text-white rounded-full">✓</div>
            <span className="text-green-600">Smart Intake</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full">2</div>
            <span className="text-blue-600">Claveteador</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-gray-300 text-gray-600 rounded-full">3</div>
            <span className="text-gray-500">Export</span>
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Claveteador AMIS</h2>
          <div className="flex items-center space-x-6 mt-2 text-sm text-gray-600">
            <div><span className="font-medium">Cliente:</span> {caseData.cliente}</div>
            <div><span className="font-medium">COT:</span> {caseData.cot}</div>
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
              <select className="border border-gray-300 rounded-md px-3 py-1 text-sm">
                <option value="All AMIS">All AMIS</option>
                <option value="Found">AMIS Found</option>
                <option value="Missing">AMIS Missing</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paquete</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Marca</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descripción</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Serie (VIN)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Año</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cobertura</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Suma Asegurada</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">AMIS</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {vehicles.map((vehicle) => (
                  <tr key={vehicle.id} className="hover:bg-gray-50">
                    <td className="px-3 py-4 text-sm">{getStatusIcon(vehicle.status)}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.paquete}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.marca}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">
                      {editingCell?.vehicleId === vehicle.id && editingCell?.field === 'descripcion' ? (
                        <input
                          type="text"
                          value={vehicle.descripcion}
                          onChange={(e) => handleCellEdit(vehicle.id, 'descripcion', e.target.value)}
                          onBlur={() => setEditingCell(null)}
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
                      <span className={vehicle.serie === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'}>
                        {vehicle.serie}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.año}</td>
                    <td className="px-3 py-4 text-sm text-gray-900">{vehicle.cobertura}</td>
                    <td className="px-3 py-4 text-sm">
                      <span className={vehicle.sumaAsegurada === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'}>
                        {vehicle.sumaAsegurada}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-sm">
                      <div className="flex items-center space-x-2">
                        <span className={vehicle.amis === 'Missing' ? 'text-red-600 italic' : 'text-gray-900'}>
                          {vehicle.amis}
                        </span>
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
                <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm">1</button>
              </div>
            </div>
          </div>
        </div>

        {/* Validate Button */}
        <div className="flex justify-center mt-8">
          <button
            onClick={onValidate}
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
```

#### **Excel Export Component**
```typescript
// Final export interface with agent discount and Excel generation
export default function ExcelExport({ caseData, onBack }: ExcelExportProps) {
  const [discountPercentage, setDiscountPercentage] = useState(15)
  const [finalVehicles] = useState<FinalVehicle[]>([
    // Vehicle data with final insurance columns
  ])

  const handleDownloadExcel = () => {
    console.log(`Downloading Excel with ${discountPercentage}% discount...`)
    // Generate and download Excel file
    alert(`Excel Cotizador downloaded with ${discountPercentage}% agent discount!`)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with completed workflow navigation */}
      <header className="bg-white border-b border-gray-200">
        <nav className="flex items-center space-x-8">
          <div className="flex items-center">
            <div className="w-6 h-6 bg-green-500 text-white rounded-full">✓</div>
            <span className="text-green-600">Smart Intake</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-green-500 text-white rounded-full">✓</div>
            <span className="text-green-600">Claveteador</span>
          </div>
          <div className="flex items-center">
            <div className="w-6 h-6 bg-blue-600 text-white rounded-full">3</div>
            <span className="text-blue-600">Export</span>
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Excel Export</h2>
              <div className="flex items-center space-x-6 mt-2 text-sm text-gray-600">
                <div><span className="font-medium">Cliente:</span> {caseData.cliente}</div>
                <div><span className="font-medium">COT:</span> {caseData.cot}</div>
              </div>
            </div>
            <div className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
              Ready for Export
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
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Marca</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Serie (VIN)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Año</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paquete</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo Servicio</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo de Uso</th>
                  <th className="px-3 py

#### **Manual Email Intake**
```typescript
// Manual email entry for testing smart intake workflows
export default function ManualIntakeForm({ onProcess }: ManualIntakeFormProps) {
  const [emailData, setEmailData] = useState<EmailData>({
    from: '',
    subject: '',
    receivedDate: new Date().toISOString().split('T')[0],
    content: '',
    attachments: []
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (emailData.from && emailData.subject && emailData.attachments.length > 0) {
      onProcess(emailData) // Triggers smart processing pipeline
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* Email metadata fields */}
      {/* Content textarea */}
      {/* File drag & drop */}
      {/* Processing pipeline visualization */}
    </form>
  )
}
```

#### **AI-Assisted Profile Generation**
```typescript
// 3-step wizard for creating broker profiles with LLM assistance
export default function ProfileGenerationWizard({ onComplete }: ProfileWizardProps) {
  const [step, setStep] = useState<'review' | 'mapping' | 'validation'>('review')
  const [mappings, setMappings] = useState<FieldMapping[]>([])

  // Step 1: Review AI detection results
  // Step 2: Edit field mappings manually  
  // Step 3: Validate and save profile

  const handleComplete = () => {
    const finalProfile = {
      name: profileName,
      domain: profileData.broker_domain,
      field_mappings: Object.fromEntries(mappings.map(m => [m.source_field, m.target_field])),
      auto_generated: true,
      confidence: profileData.confidence_score
    }
    onComplete(finalProfile)
  }

  return (
    <div className="wizard-steps">
      {step === 'review' && <ReviewDetection />}
      {step === 'mapping' && <EditMappings />} 
      {step === 'validation' && <ValidateProfile />}
    </div>
  )
}
```

#### **Profile Management Interface**
```typescript
// Centralized broker profile management with statistics
export default function BrokerProfileManager() {
  const [profiles, setProfiles] = useState<BrokerProfile[]>([])
  const [showWizard, setShowWizard] = useState(false)

  const handleApproveProfile = (profileId: string) => {
    setProfiles(prev => prev.map(p => 
      p.id === profileId ? { ...p, status: 'active' } : p
    ))
  }

  return (
    <div>
      {/* Search and filter profiles */}
      {/* Profile list with usage stats */}
      {/* Auto-generation wizard */}
      {/* Detailed profile viewer */}
      
      {showWizard && (
        <ProfileGenerationWizard
          onComplete={handleCreateProfile}
          onCancel={() => setShowWizard(false)}
        />
      )}
    </div>
  )
}
```

### **📧 Smart Intake Integration**
```typescript
// Email processing with broker detection and profile application
const handleEmailProcess = async (emailData: EmailData) => {
  try {
    // 1. Detect broker from email domain
    const brokerDetection = await apiClient.detectBrokerFromEmail(emailData.from)
    let profile = brokerDetection?.profile_id || 'generic.yaml'
    
    // 2. Process email with attachments
    const attachments = emailData.attachments.map(att => att.file)
    const response = await apiClient.processEmailData({
      from: emailData.from,
      subject: emailData.subject,
      content: emailData.content,
      attachments
    })
    
    // 3. Track processing status in real-time
    const newRun: ProcessingRun = {
      id: response.run_id,
      caseId: response.case_id,
      status: 'uploading',
      fileName: `Email from ${emailData.from}`,
      profile,
      type: 'email_intake',
      emailData
    }
    
    setActiveRuns(prev => [...prev, newRun])
    pollProcessingStatus(newRun.id)
    
  } catch (error) {
    // Fallback to local processing if API fails
    console.error('Smart intake error:', error)
  }
}
```

### **Dashboard Interface**
```typescript
// Dashboard with real-time statistics
export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiService.database.getDashboardStats(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });

  return (
    <div className="space-y-6">
      <StatsCards stats={stats} />
      <ChartsGrid stats={stats} />
      <RecentActivity />
      <SystemHealth />
    </div>
  );
}
```

### **Case Management**
```typescript
// Case list with filtering and search
export default function CaseListPage() {
  const [filters, setFilters] = useState<CaseFilters>({
    status: 'all',
    dateRange: 'last_7_days',
    confidence: 'all'
  });

  const { data: cases, isLoading } = useQuery({
    queryKey: ['cases', filters],
    queryFn: () => apiService.database.getCases(filters)
  });

  return (
    <div className="space-y-4">
      <CaseFilters filters={filters} onFiltersChange={setFilters} />
      <CaseTable 
        cases={cases?.data || []} 
        loading={isLoading}
        onCaseSelect={(cot) => router.push(`/cases/${cot}`)}
      />
    </div>
  );
}
```

### **Vehicle Management Grid**
```typescript
// Editable vehicle grid with CVEGS management
export default function VehicleGrid({ caseId }: { caseId: string }) {
  const { data: vehicles, mutate } = useQuery({
    queryKey: ['vehicles', caseId],
    queryFn: () => apiService.database.getVehiclesByCase(caseId)
  });

  const updateCVEGS = useMutation({
    mutationFn: ({ vehicleId, cvegsCode }: { vehicleId: string; cvegsCode: string }) =>
      apiService.database.updateVehicleCvegs(vehicleId, { cvegs_code: cvegsCode }),
    onSuccess: () => mutate() // Refresh data
  });

  return (
    <DataTable
      data={vehicles || []}
      columns={[
        { key: 'brand', label: 'Brand', sortable: true },
        { key: 'model', label: 'Model', sortable: true },
        { key: 'year', label: 'Year', sortable: true },
        { 
          key: 'cvegs_code', 
          label: 'CVEGS Code', 
          editable: true,
          render: (value, row) => (
            <CVEGSCodeEditor 
              value={value} 
              confidence={row.cvegs_confidence}
              onSave={(newCode) => updateCVEGS.mutate({ 
                vehicleId: row.id, 
                cvegsCode: newCode 
              })}
            />
          )
        },
        {
          key: 'cvegs_confidence',
          label: 'Confidence',
          render: (value) => <ConfidenceBadge confidence={value} />
        }
      ]}
    />
  );
}
```

## API Integration

### **Service Clients**
```typescript
// API client configuration with error handling
const API_CONFIG = {
  smartIntake: {
    baseURL: process.env.NEXT_PUBLIC_SMART_INTAKE_URL || 'http://localhost:8002',
    timeout: 30000,
  },
  vehicleMatcher: {
    baseURL: process.env.NEXT_PUBLIC_VEHICLE_MATCHER_URL || 'http://localhost:8000',
    timeout: 30000,
  },
  database: {
    baseURL: process.env.NEXT_PUBLIC_DATABASE_URL || 'http://localhost:8001',
    timeout: 30000,
  },
};

// Service-specific API methods
export const apiService = {
  database: {
    async getCases(filters?: CaseFilters): Promise<Case[]> {
      return databaseClient.get('/cases', { params: filters });
    },
    
    async updateVehicleCvegs(vehicleId: string, data: any): Promise<Vehicle> {
      return databaseClient.patch(`/vehicles/${vehicleId}/cvegs`, data);
    }
  },
  
  vehicleMatcher: {
    async matchBatchVehicles(vehicles: any[]): Promise<BatchMatchResponse> {
      return vehicleMatcherClient.post('/match/batch', { vehicles });
    }
  },
  
  smartIntake: {
    async processEmailData(emailData: {
      from: string
      subject: string
      content: string
      attachments: File[]
    }): Promise<ProcessEmailResponse> {
      const formData = new FormData()
      formData.append('from_email', emailData.from)
      formData.append('subject', emailData.subject)
      formData.append('content', emailData.content)
      
      emailData.attachments.forEach((file, index) => {
        formData.append(`attachment_${index}`, file)
      })
      
      return smartIntakeClient.post('/process-email', formData)
    },
    
    async detectBrokerFromEmail(emailAddress: string): Promise<BrokerDetection> {
      return smartIntakeClient.get(`/broker-profiles/detect?email=${encodeURIComponent(emailAddress)}`)
    },
    
    async getBrokerProfiles(): Promise<BrokerProfile[]> {
      return smartIntakeClient.get('/broker-profiles')
    },
    
    async createBrokerProfile(profileData: any): Promise<BrokerProfile> {
      return smartIntakeClient.post('/broker-profiles', profileData)
    }
  }
};
```

### **React Query Integration**
```typescript
// Custom hooks for data fetching
export function useCases(filters?: CaseFilters) {
  return useQuery({
    queryKey: ['cases', filters],
    queryFn: () => apiService.database.getCases(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useVehicles(caseId: string) {
  return useQuery({
    queryKey: ['vehicles', caseId],
    queryFn: () => apiService.database.getVehiclesByCase(caseId),
    enabled: !!caseId,
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiService.database.getDashboardStats(),
    refetchInterval: 30000, // Auto-refresh
  });
}
```

## UI Components

### **Custom Insurance Components**
```typescript
// Confidence indicator component
export function ConfidenceBadge({ confidence }: { confidence?: number }) {
  if (!confidence) return <Badge variant="secondary">Unknown</Badge>;
  
  const level = confidence >= 0.9 ? 'high' : 
                confidence >= 0.7 ? 'medium' : 
                confidence >= 0.5 ? 'low' : 'very-low';
  
  return (
    <Badge className={`confidence-${level}`}>
      {(confidence * 100).toFixed(0)}%
    </Badge>
  );
}

// Status badge component
export function StatusBadge({ status }: { status: MessageStatus }) {
  return (
    <Badge className={`status-${status.toLowerCase().replace('_', '-')}`}>
      {status.replace('_', ' ').toLowerCase()}
    </Badge>
  );
}

// COT number display
export function COTDisplay({ cotNumber }: { cotNumber: string }) {
  return (
    <span className="cot-number font-mono text-sm font-medium">
      {cotNumber}
    </span>
  );
}
```

### **Data Visualization**
```typescript
// Dashboard charts
export function ConfidenceDistributionChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

// Processing trends chart
export function ProcessingTrendsChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="cases_processed" fill="#3b82f6" />
        <Bar dataKey="vehicles_matched" fill="#10b981" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

## Styling System

### **Custom CSS Classes**
```css
/* Confidence level indicators */
.confidence-high {
  @apply bg-green-100 text-green-800 border-green-200;
}

.confidence-medium {
  @apply bg-yellow-100 text-yellow-800 border-yellow-200;
}

.confidence-low {
  @apply bg-orange-100 text-orange-800 border-orange-200;
}

.confidence-very-low {
  @apply bg-red-100 text-red-800 border-red-200;
}

/* Status indicators */
.status-processed {
  @apply bg-green-100 text-green-800 border-green-200;
}

.status-needs-review {
  @apply bg-orange-100 text-orange-800 border-orange-200;
}

.status-error {
  @apply bg-red-100 text-red-800 border-red-200;
}

/* Insurance-specific utilities */
.cot-number {
  @apply font-mono text-sm font-medium;
}

.vehicle-description {
  @apply text-sm text-muted-foreground;
}

.confidence-score {
  @apply font-medium tabular-nums;
}
```

### **Theme Configuration**
```javascript
// Tailwind config with custom insurance colors
module.exports = {
  theme: {
    extend: {
      colors: {
        confidence: {
          high: "hsl(142, 76%, 36%)",
          medium: "hsl(32, 95%, 44%)",
          low: "hsl(0, 84%, 60%)",
          "very-low": "hsl(0, 84%, 40%)",
        }
      }
    }
  }
}
```

## Type Safety

### **Complete Type System**
```typescript
// Core data types
export interface Case {
  id: string;
  cot_number: string;
  client_name?: string;
  broker_email?: string;
  vehicle_count: number;
  created_at: string;
  // ... complete type definition
}

export interface Vehicle {
  id: string;
  case_id: string;
  brand?: string;
  model?: string;
  cvegs_code?: string;
  cvegs_confidence?: number;
  // ... complete type definition
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

// Filter and pagination types
export interface CaseFilters {
  status?: MessageStatus | 'all';
  dateRange?: 'today' | 'last_7_days' | 'last_30_days';
  confidence?: 'high' | 'medium' | 'low' | 'all';
  search?: string;
}
```

## Development

### **Setup Instructions**
```bash
# Navigate to frontend directory
cd frontend/smart-intake-ui

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Edit with your API URLs

# Start development server
npm run dev

# The application will be available at http://localhost:3000
```

### **Environment Configuration**
```bash
# .env.local
NEXT_PUBLIC_SMART_INTAKE_URL=http://localhost:8002
NEXT_PUBLIC_VEHICLE_MATCHER_URL=http://localhost:8000
NEXT_PUBLIC_DATABASE_URL=http://localhost:8001
NEXT_PUBLIC_API_KEY=your_api_key_if_needed
```

### **Development Scripts**
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch"
  }
}
```

## Features Implementation

### **Dashboard Features**
- **Real-time Statistics**: Auto-refreshing stats cards and charts
- **System Health**: Service status indicators with health checks
- **Recent Activity**: Live feed of processed cases and vehicles
- **Performance Metrics**: Processing times, success rates, confidence distribution

### **Case Management Features**
- **Advanced Filtering**: Filter by status, date range, confidence level
- **Search Functionality**: Search across case details, COT numbers, client names
- **Bulk Operations**: Batch actions for multiple cases
- **Status Tracking**: Visual indicators for processing status

### **Vehicle Management Features**
- **Editable Grid**: In-line editing of vehicle information and CVEGS codes
- **Confidence Indicators**: Visual confidence level indicators
- **Batch Re-matching**: Re-process vehicles with updated matching
- **Manual Override**: Allow manual CVEGS code corrections

### **Export Features**
- **Excel Reports**: Generate comprehensive Excel reports with templates
- **PDF Summaries**: Create PDF case summaries for documentation
- **Bulk Export**: Export multiple cases or filtered results
- **Custom Templates**: Configurable report templates

## Performance Optimization

### **Code Splitting**
```typescript
// Lazy loading for large components
const VehicleGrid = lazy(() => import('@/components/vehicles/vehicle-grid'));
const DocumentViewer = lazy(() => import('@/components/documents/document-viewer'));

// Route-based code splitting with Next.js App Router
// Automatic code splitting per page
```

### **Data Fetching Optimization**
```typescript
// Optimized queries with React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
  },
});

// Prefetching for better UX
export function usePrefetchCaseDetails(cotNumber: string) {
  const queryClient = useQueryClient();
  
  return useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['case', cotNumber],
      queryFn: () => apiService.database.getCaseByCot(cotNumber),
    });
  }, [cotNumber, queryClient]);
}
```

### **Image and Asset Optimization**
```javascript
// Next.js image optimization
import Image from 'next/image';

// Automatic image optimization and lazy loading
<Image
  src="/logo.png"
  alt="Minca AI Insurance"
  width={200}
  height={50}
  priority
/>
```

## Testing

### **Component Testing**
```typescript
// React Testing Library examples
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from '@/app/dashboard/page';

test('renders dashboard with statistics', async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  );

  expect(screen.getByText('Dashboard')).toBeInTheDocument();
  expect(screen.getByText('Total Cases')).toBeInTheDocument();
});
```

### **API Testing**
```typescript
// Mock API responses for testing
jest.mock('@/lib/api/services', () => ({
  apiService: {
    database: {
      getDashboardStats: jest.fn().mockResolvedValue({
        cases: { total_cases: 100, cases_today: 5 },
        vehicles: { total_vehicles: 300, match_rate: 95.5 }
      })
    }
  }
}));
```

## Deployment

### **Build Configuration**
```bash
# Production build
npm run build

# Start production server
npm start

# Docker deployment
docker build -t smart-intake-ui .
docker run -p 3000:3000 smart-intake-ui
```

### **Environment Variables**
```bash
# Production environment
NEXT_PUBLIC_SMART_INTAKE_URL=https://api.yourdomain.com/smart-intake
NEXT_PUBLIC_VEHICLE_MATCHER_URL=https://api.yourdomain.com/vehicle-matcher
NEXT_PUBLIC_DATABASE_URL=https://api.yourdomain.com/database
```

This frontend application provides a comprehensive user interface for the insurance underwriting platform, with modern React patterns, type safety, and optimized performance.
