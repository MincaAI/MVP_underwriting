const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const DOCUMENT_PROCESSOR_URL = process.env.NEXT_PUBLIC_DOCUMENT_PROCESSOR_URL || 'http://localhost:8001'
const SMART_INTAKE_URL = process.env.NEXT_PUBLIC_SMART_INTAKE_URL || 'http://localhost:8002'

interface BrokerProfileData {
  domain: string
  name: string
  profile_id: string
  confidence: number
  field_mappings: Record<string, string>
  auto_generated: boolean
}

class APIClient {
  private baseURL: string
  private documentProcessorURL: string
  private smartIntakeURL: string

  constructor(baseURL: string = API_BASE_URL, documentProcessorURL: string = DOCUMENT_PROCESSOR_URL, smartIntakeURL: string = SMART_INTAKE_URL) {
    this.baseURL = baseURL
    this.documentProcessorURL = documentProcessorURL
    this.smartIntakeURL = smartIntakeURL
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, baseUrl?: string): Promise<T> {
    const url = `${baseUrl || this.baseURL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  private async uploadFile<T>(endpoint: string, file: File, additionalData: Record<string, unknown> = {}, baseUrl?: string): Promise<T> {
    const url = `${baseUrl || this.baseURL}${endpoint}`
    
    const formData = new FormData()
    formData.append('file', file)
    
    // Add additional form data
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, String(value))
    })
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  // Health check
  async healthCheck() {
    return this.request('/health')
  }

  // Document processing endpoints (using document-processor service)
  async processDocument(file: File, caseId: string, profile: string = 'generic.yaml', exportTemplate: string = 'gcotiza_v1.yaml') {
    return this.uploadFile('/process', file, { 
      case_id: caseId, 
      profile, 
      export_template: exportTemplate 
    }, this.documentProcessorURL)
  }

  // Get processed results from document processor
  async getProcessedResults(runId: string) {
    return this.request(`/results/${runId}`, {}, this.documentProcessorURL)
  }

  // Download export file
  async downloadExport(exportUrl: string) {
    const response = await fetch(exportUrl)
    if (!response.ok) {
      throw new Error(`Download Error: ${response.status} ${response.statusText}`)
    }
    return response.blob()
  }

  async extractDocument(file: File, caseId: string, profile: string = 'generic.yaml') {
    return this.uploadFile('/extract', file, { 
      case_id: caseId, 
      profile 
    }, this.documentProcessorURL)
  }

  async transformDocument(runId: string, profile: string = 'generic.yaml') {
    return this.request(`/transform/${runId}?profile=${profile}`, {
      method: 'POST',
    }, this.documentProcessorURL)
  }

  async exportDocument(runId: string, template: string = 'gcotiza_v1.yaml') {
    return this.request(`/export/${runId}?template=${template}`, {
      method: 'POST',
    }, this.documentProcessorURL)
  }


  // Legacy transform endpoint (for backward compatibility)
  async transform(caseId: string, s3Uri: string, profile: string) {
    return this.request('/transform', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, s3_uri: s3Uri, profile }),
    })
  }

  // Get transform preview
  async getTransformPreview(runId: string, limit: number = 10) {
    return this.request(`/transform/preview?run_id=${runId}&limit=${limit}`)
  }

  // Codify batch
  async codifyBatch(runId?: string, caseId?: string) {
    const params = new URLSearchParams()
    if (runId) params.append('run_id', runId)
    if (caseId) params.append('case_id', caseId)
    
    return this.request(`/codify/batch?${params}`, {
      method: 'POST',
    })
  }

  // Export
  async export(runId: string, template: string = 'gcotiza_v1.yaml') {
    return this.request(`/export?run_id=${runId}&template=${template}`, {
      method: 'POST',
    })
  }

  // Get download link
  async getDownloadLink(runId: string) {
    return this.request(`/export/download?run_id=${runId}`)
  }

  // Email processing endpoints (using main API)
  async processEmailData(emailData: {
    from: string
    subject: string
    receivedDate: string
    content: string
    attachments: File[]
  }) {
    const formData = new FormData()
    
    // Add email metadata
    formData.append('from_email', emailData.from)
    formData.append('subject', emailData.subject)
    formData.append('received_date', emailData.receivedDate)
    formData.append('content', emailData.content)
    
    // Add attachments
    emailData.attachments.forEach((file) => {
      formData.append('attachments', file)
    })
    
    const response = await fetch(`${this.baseURL}/process-manual-email`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Email Processing Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async getEmailDetails(emailId: number) {
    return this.request(`/email/${emailId}`)
  }

  // Smart intake email endpoints
  async listEmails(limit: number = 50, offset: number = 0, statusFilter?: string) {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    if (statusFilter) {
      params.append('status_filter', statusFilter)
    }
    
    return this.request(`/emails?${params}`)
  }

  async processEmail(emailId: number) {
    return this.request(`/email/${emailId}/process`, {
      method: 'POST',
    })
  }

  async updatePreAnalysisStatus(caseId: string, data: {
    pre_analysis_status: string
    missing_requirements?: object
    pre_analysis_notes?: string
  }) {
    const formData = new FormData()
    formData.append('pre_analysis_status', data.pre_analysis_status)
    
    if (data.missing_requirements) {
      formData.append('missing_requirements', JSON.stringify(data.missing_requirements))
    }
    
    if (data.pre_analysis_notes) {
      formData.append('pre_analysis_notes', data.pre_analysis_notes)
    }
    
    const response = await fetch(`${this.baseURL}/case/${caseId}/pre-analysis`, {
      method: 'PUT',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  // Processing status and data endpoints
  async getProcessingStatus(runId: string) {
    return this.request(`/processing/status/${runId}`)
  }

  async getPreprocessedData(runId: string, limit: number = 100, offset: number = 0) {
    return this.request(`/processing/data/${runId}?limit=${limit}&offset=${offset}`)
  }

  async getCaseRuns(caseId: string) {
    return this.request(`/processing/runs/${caseId}`)
  }

  async triggerMatching(runId: string) {
    return this.request(`/processing/trigger-matching/${runId}`, {
      method: 'POST',
    })
  }

  async getBrokerProfiles() {
    return this.request('/broker-profiles', {}, this.smartIntakeURL)
  }

  async createBrokerProfile(profileData: BrokerProfileData) {
    return this.request('/broker-profiles', {
      method: 'POST',
      body: JSON.stringify(profileData)
    }, this.smartIntakeURL)
  }

  async updateBrokerProfile(profileId: string, profileData: BrokerProfileData) {
    return this.request(`/broker-profiles/${profileId}`, {
      method: 'PUT',
      body: JSON.stringify(profileData)
    }, this.smartIntakeURL)
  }

  async detectBrokerFromEmail(emailAddress: string) {
    return this.request(`/broker-profiles/detect?email=${encodeURIComponent(emailAddress)}`, {}, this.smartIntakeURL)
  }

  // Search vehicles (mock endpoint for now)
  async searchVehicles(query: string) {
    // This would call the actual search API when implemented
    // For now, return mock data filtered by query
    console.log('Searching for:', query) // Use the query parameter
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
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
          }
        ])
      }, 500)
    })
  }
}

export const apiClient = new APIClient()
export default APIClient
