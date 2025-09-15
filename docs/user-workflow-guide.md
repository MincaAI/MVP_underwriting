# Claveteador Workflow User Guide

## Overview

The Claveteador workflow provides a complete end-to-end process for insurance case processing, from smart intake through vehicle matching to final export. This guide walks you through each step of the process.

## Workflow Steps

```
Smart Intake → Claveteador → Vehicle Matching → Excel Export
     ↓              ↓              ↓              ↓
Email Processing  Data Review   AMIS Matching   Final Export
Attachment Parse  Form Validation  Code Assignment  Excel Generation
Broker Detection  Coverage Setup   Manual Editing   Agent Discount
```

## Step 1: Smart Intake Dashboard

### Purpose
The Smart Intake Dashboard displays processed email results and allows you to initiate case processing.

### Features
- **Results Table**: Shows all processed smart intake cases
- **Status Indicators**: Visual indicators for case status and pre-analysis
- **Filtering**: Filter cases by status, date, and other criteria
- **Action Buttons**: Process complete cases or request additional information

### How to Use

1. **View Cases**: The dashboard displays all smart intake results in a table format
2. **Check Status**: Look for status badges:
   - ✅ **Completo**: Case has all required information
   - ⚠️ **Incompleto**: Case is missing required information
   - 🟡 **Pending**: Case is waiting for processing
   - 🔵 **Processing**: Case is currently being processed

3. **Filter Results**: Use the dropdown filters to narrow down cases:
   - **Status Filter**: Filter by completion status
   - **Date Filter**: Sort by most recent or oldest first

4. **Take Action**:
   - **Process Button**: Click to proceed with complete cases
   - **Ask Info Button**: Click to request missing information for incomplete cases

### Example
```
Case: Fleet Insurance Quote Request
Company: Logistics Express S.A. de C.V.
COT: TK-2024-001
Status: ✅ Completo
Action: [Process] button available
```

## Step 2: Claveteador (Data Preprocessing)

### Purpose
The Claveteador step allows you to review and validate all case information before proceeding to vehicle matching.

### Sections

#### 2.1 Smart Intake Email Display
- **Email Details**: Subject, sender, date, and content
- **Verification**: Confirm email information is correct
- **Content Review**: Review the original email content

#### 2.2 Email Processing Details
- **Broker Information**: 
  - Broker Name (auto-extracted from email)
  - Broker Email address
- **Request Details**:
  - Request Type (e.g., Fleet Quotation)
  - Coverage Type (e.g., Comprehensive/Amplia)
  - Fleet Size (auto-detected from attachments)

#### 2.3 Attachments Management
- **File Display**: Shows attached Excel files
- **Vehicle Detection**: Displays detected vehicle count
- **Download Option**: Download original attachments for review
- **File Validation**: Confirms file type and content

#### 2.4 Company Information Form
**Required Fields** (marked with *):
- **Nombre***: Company legal name
- **RFC***: Tax identification number
- **Domicilio***: Company address
- **Actividad**: Business activity description
- **Uso***: Vehicle usage type (Commercial, Personal, etc.)
- **Vigencia Desde***: Policy start date
- **Vigencia Hasta***: Policy end date

**Missing Field Indicators**:
- Fields highlighted in yellow indicate missing information
- Red "Missing field" labels show what needs to be completed

#### 2.5 Coverage Requirements Configuration

**Auto Coverage**:
- ✅ DAÑOS MATERIALES: $250,000 (A) 3.00%
- ✅ ROBO TOTAL: $500,000 (A) 3.00%
- ✅ RESPONSABILIDAD CIVIL BIENES: 40% (A) 3.00%
- ☐ RESPONSABILIDAD CIVIL PERSONAS: NO APLICA
- ☐ GASTOS MÉDICOS OCUPANTES: NO APLICA

**Remolques Coverage**:
- ✅ DAÑOS MATERIALES: $250,000 (A) 3.00%
- ✅ ROBO TOTAL: $500,000 (A) 3.00%
- ✅ RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS: $750,000 (A) 3.00%

**Camiones Pesado Coverage**:
- ✅ RESPONSABILIDAD CIVIL POR DAÑOS A TERCEROS: $750,000 (A) 3.00%
- ✅ Opera Sub-límite sobre la RESPONSABILIDAD CIVIL TERCEROS: 50% (A) 3.00%

**Moto Coverage**:
- ✅ DAÑOS MATERIALES: $250,000 (A) 3.00%
- ✅ ROBO TOTAL: $500,000 (A) 3.00%

#### 2.6 Claims History
- **PDF Report**: Claims history document
- **Statistics**: Summary of claims (e.g., "Last 3 years • 8 total claims • $104,500 total")
- **Download**: Access to full claims report

### How to Use

1. **Review Email Information**: Verify all email details are correct
2. **Check Processing Details**: Confirm broker information and request type
3. **Validate Company Information**: 
   - Fill in any missing required fields
   - Correct any inaccurate information
   - Pay attention to highlighted missing fields
4. **Configure Coverage**: 
   - Review coverage requirements for each vehicle type
   - Enable/disable coverage options as needed
   - Verify coverage amounts and deductibles
5. **Review Claims History**: Check historical claims data
6. **Proceed**: Click the "🔍 Claveteador" button to continue to vehicle matching

## Step 3: Vehicle Matching (AMIS Codification)

### Purpose
The Vehicle Matching step performs AMIS codification and allows you to review and edit vehicle matching results.

### Features

#### 3.1 Codification Results Summary
- **Total Vehicles**: Total number of vehicles in the fleet
- **AMIS Found**: Number of successfully matched vehicles (green)
- **Uncertain**: Number of uncertain matches (yellow)
- **Failed**: Number of failed matches (red)

#### 3.2 Vehicle Data Table
**Columns**:
- **Status**: Visual indicator of matching status
  - ✅ Complete: All information available
  - ⚠️ Missing VIN, Suma: Missing critical information
  - ❓ Uncertain: Uncertain match
  - ❌ Failed: Matching failed

- **Paquete**: Package identifier (e.g., AMPL-001)
- **Marca**: Vehicle brand (e.g., NISSAN, CHEVROLET)
- **Descripción**: Vehicle description (editable)
- **Serie (VIN)**: Vehicle identification number (editable)
- **Año**: Vehicle year
- **Cobertura**: Coverage type (e.g., Limitada, RC, Amplia)
- **Suma Asegurada**: Insured amount (editable)
- **AMIS**: AMIS code with status indicator
  - 🟢 OK: Successfully matched
  - 🔴 FAIL: Matching failed or missing
- **Action**: Edit button for manual corrections

#### 3.3 Interactive Features
- **Inline Editing**: Click on editable fields to modify values
- **Filtering**: Filter vehicles by AMIS status (All AMIS, Found, Missing, Failed)
- **Pagination**: Navigate through multiple pages of vehicles
- **Search**: Search for specific vehicles (if implemented)

### How to Use

1. **Review Summary**: Check the codification results summary
   - High success rate (AMIS Found) indicates good matching
   - Review uncertain and failed matches for manual correction

2. **Examine Vehicle Data**:
   - Scroll through the vehicle table
   - Look for red "FAIL" indicators in the AMIS column
   - Check for missing information (highlighted in red/italic)

3. **Make Corrections**:
   - Click on editable fields to modify values
   - Focus on vehicles with missing VIN or Suma Asegurada
   - Correct vehicle descriptions for better matching
   - Manually assign AMIS codes if needed

4. **Use Filters**: Filter by status to focus on problematic vehicles
   - "AMIS Missing" to see unmatched vehicles
   - "Failed" to see vehicles that need attention

5. **Validate**: Click "✅ VALIDATE CLAVE AMIS" when satisfied with the results

### Best Practices
- **Prioritize Failed Matches**: Focus on vehicles with "FAIL" status first
- **Complete Missing Information**: Ensure VIN and Suma Asegurada are filled
- **Verify Descriptions**: Accurate descriptions improve AMIS matching
- **Check Consistency**: Ensure similar vehicles have consistent AMIS codes

## Step 4: Excel Export

### Purpose
The Excel Export step generates the final quotation document with all processed vehicle data and insurance details.

### Features

#### 4.1 Export Header
- **Status Indicator**: "Ready for Export" (green badge)
- **Case Information**: Client name and COT number
- **Navigation**: Shows completed workflow steps

#### 4.2 Final Vehicles Data Table
**Complete Mexican Insurance Columns**:
- **Marca**: Vehicle brand
- **Serie (VIN)**: Vehicle identification number
- **Año**: Vehicle year
- **Paquete**: Package identifier
- **Tipo Servicio**: Service type (e.g., particular)
- **Tipo de Uso**: Usage type (e.g., normal)
- **Valor Vehiculo**: Vehicle value
- **DED DM PP**: Deductible percentage for material damage
- **DED DM PT**: Deductible percentage for partial theft
- **DED RT**: Deductible percentage for total theft
- **SA RC LUC**: Civil liability coverage amount
- **A. JURIDICA**: Legal assistance coverage

#### 4.3 Agent Discount Configuration
- **Discount Percentage**: Editable field (default: 15%)
- **Real-time Calculation**: Discount applied to final pricing
- **Flexible Adjustment**: Can be modified before export

#### 4.4 Export Functionality
- **Excel Generation**: Creates professional Excel Cotizador
- **Download Button**: "📄 Download Excel Cotizador (X% discount)"
- **Professional Formatting**: Properly formatted for insurance use

### How to Use

1. **Review Final Data**: 
   - Verify all vehicle information is complete and accurate
   - Check that all required Mexican insurance columns are populated
   - Ensure vehicle values and coverage amounts are correct

2. **Set Agent Discount**:
   - Adjust the discount percentage as needed
   - Default is 15% but can be modified
   - Discount is applied to the final quotation

3. **Generate Export**:
   - Click "Download Excel Cotizador" button
   - Excel file will be generated with the specified discount
   - File includes all vehicle data in the proper format

4. **Workflow Completion**:
   - Navigation shows all steps as completed
   - Case is ready for final review and client delivery

### Export File Contents
The generated Excel file includes:
- **Professional formatting** with insurance company branding
- **Complete vehicle inventory** with all required fields
- **Coverage details** for each vehicle type
- **Pricing information** with agent discount applied
- **Mexican insurance compliance** formatting

## Navigation and Workflow Control

### Step Navigation
- **Progress Indicators**: Visual step indicators show current position
- **Back Navigation**: Return to previous steps if needed
- **Step Completion**: Completed steps show green checkmarks

### Workflow States
1. **Smart Intake** (Step 1): ✅ Completed
2. **Claveteador** (Step 2): 🔵 Active or ✅ Completed
3. **Export** (Step 3): ⚪ Pending or 🔵 Active

### Error Handling
- **Missing Information**: Highlighted fields and clear indicators
- **Validation Errors**: Inline error messages and guidance
- **Failed Matches**: Clear status indicators and editing options

## Tips for Efficient Processing

### Data Quality
1. **Complete Information**: Ensure all required fields are filled
2. **Accurate Descriptions**: Better descriptions lead to better AMIS matching
3. **Consistent Formatting**: Use consistent formats for similar data

### Review Process
1. **Start with Summary**: Review codification results summary first
2. **Focus on Failures**: Address failed matches before proceeding
3. **Verify Critical Fields**: Double-check VIN numbers and vehicle values
4. **Test Export**: Generate a test export to verify formatting

### Common Issues and Solutions

#### Issue: Low AMIS Matching Rate
**Solution**: 
- Review vehicle descriptions for accuracy
- Check for typos or formatting issues
- Manually assign AMIS codes for failed matches

#### Issue: Missing Vehicle Information
**Solution**:
- Return to Claveteador step to complete company information
- Check original attachments for missing data
- Contact broker for additional information if needed

#### Issue: Incorrect Coverage Configuration
**Solution**:
- Review coverage requirements in Claveteador step
- Verify coverage amounts match client requirements
- Adjust coverage options as needed

## Workflow Completion Checklist

### Before Proceeding from Smart Intake:
- [ ] Case status shows "Completo"
- [ ] All required attachments are present
- [ ] Email information is accurate

### Before Proceeding from Claveteador:
- [ ] Company information is complete
- [ ] Coverage requirements are configured
- [ ] Claims history is reviewed
- [ ] All missing fields are addressed

### Before Proceeding from Vehicle Matching:
- [ ] AMIS matching rate is acceptable
- [ ] Failed matches are addressed
- [ ] Critical vehicle information is complete
- [ ] Manual corrections are made as needed

### Before Final Export:
- [ ] Final vehicle data is accurate
- [ ] Agent discount is set correctly
- [ ] All Mexican insurance columns are populated
- [ ] Export format meets requirements

This comprehensive workflow ensures accurate, complete insurance case processing from initial email intake through final quotation delivery.
