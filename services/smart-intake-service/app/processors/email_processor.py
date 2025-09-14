import re
from typing import Dict, List, Any, Optional
import structlog
from bs4 import BeautifulSoup
import html2text
from datetime import datetime
import json

from ..config.settings import get_settings

logger = structlog.get_logger()


class EmailProcessor:
    """Processes email content and extracts insurance-related information."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # HTML to text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.body_width = 0  # No line wrapping
        
        # Vehicle description patterns
        self.vehicle_patterns = [
            r'\b(?:MARCA|BRAND):\s*([A-Z\s]+)',
            r'\b(?:MODELO|MODEL):\s*([A-Z0-9\s\-]+)',
            r'\b(?:AÑO|YEAR|MODELO):\s*(\d{4})',
            r'\b([A-Z]+\s+[A-Z0-9\s\-]+\s+\d{4})',  # Generic vehicle description
        ]
        
        # Client information patterns
        self.client_patterns = {
            'client_name': [
                r'(?:CLIENTE|CLIENT|ASEGURADO):\s*([A-Z\s\.]+)',
                r'(?:NOMBRE|NAME):\s*([A-Z\s\.]+)',
                r'(?:RAZÓN SOCIAL|COMPANY):\s*([A-Z\s\.]+)'
            ],
            'client_rfc': [
                r'(?:RFC):\s*([A-Z0-9]{10,13})',
                r'\b([A-Z]{3,4}\d{6}[A-Z0-9]{3})\b'  # RFC pattern
            ],
            'broker_name': [
                r'(?:BROKER|AGENTE|INTERMEDIARIO):\s*([A-Z\s\.]+)',
                r'(?:CORREDOR):\s*([A-Z\s\.]+)'
            ],
            'broker_email': [
                r'(?:EMAIL|CORREO):\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            ]
        }
        
        # Coverage patterns
        self.coverage_patterns = [
            r'(?:COBERTURA|COVERAGE):\s*([A-Z\s]+)',
            r'(?:LÍMITE|LIMIT):\s*([0-9,\$\s]+)',
            r'(?:DEDUCIBLE|DEDUCTIBLE):\s*([0-9,\$\s]+)'
        ]
    
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email and extract structured information.
        
        Args:
            email_data: Raw email data from Microsoft Graph
            
        Returns:
            Processed email with extracted information
        """
        try:
            # Extract basic metadata
            metadata = self._extract_email_metadata(email_data)
            
            # Process email body
            body_content = self._process_email_body(email_data)
            
            # Extract structured information
            extracted_info = self._extract_structured_info(body_content)
            
            processed_email = {
                "metadata": metadata,
                "body_content": body_content,
                "extracted_info": extracted_info,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Email processed successfully", 
                       message_id=email_data.get("id"),
                       subject=metadata.get("subject", "")[:100],
                       extracted_fields=list(extracted_info.keys()))
            
            return processed_email
            
        except Exception as e:
            logger.error("Failed to process email", 
                        message_id=email_data.get("id"),
                        error=str(e))
            raise
    
    def _extract_email_metadata(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic email metadata."""
        sender = email_data.get("sender", {}).get("emailAddress", {})
        
        return {
            "message_id": email_data.get("id"),
            "subject": email_data.get("subject"),
            "from_name": sender.get("name"),
            "from_email": sender.get("address"),
            "received_datetime": email_data.get("receivedDateTime"),
            "has_attachments": email_data.get("hasAttachments", False),
            "importance": email_data.get("importance"),
            "folder": email_data.get("parentFolderId")
        }
    
    def _process_email_body(self, email_data: Dict[str, Any]) -> Dict[str, str]:
        """Process email body content."""
        body = email_data.get("body", {})
        content_type = body.get("contentType", "text")
        content = body.get("content", "")
        
        if content_type.lower() == "html":
            # Convert HTML to text
            text_content = self.html_converter.handle(content)
            
            # Also extract tables from HTML
            soup = BeautifulSoup(content, 'html.parser')
            tables = self._extract_html_tables(soup)
            
            return {
                "original_html": content,
                "text_content": text_content,
                "tables": tables,
                "content_type": "html"
            }
        else:
            return {
                "text_content": content,
                "content_type": "text"
            }
    
    def _extract_html_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables from HTML content."""
        tables = []
        
        for table in soup.find_all('table'):
            try:
                rows = []
                for tr in table.find_all('tr'):
                    cells = []
                    for td in tr.find_all(['td', 'th']):
                        cells.append(td.get_text(strip=True))
                    if cells:  # Only add non-empty rows
                        rows.append(cells)
                
                if rows:
                    tables.append({
                        "rows": rows,
                        "row_count": len(rows),
                        "column_count": len(rows[0]) if rows else 0
                    })
                    
            except Exception as e:
                logger.warning("Failed to extract table", error=str(e))
        
        return tables
    
    def _extract_structured_info(self, body_content: Dict[str, str]) -> Dict[str, Any]:
        """Extract structured information using regex patterns."""
        text_content = body_content.get("text_content", "")
        
        extracted = {}
        
        # Extract client information
        for field, patterns in self.client_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
                if match:
                    extracted[field] = match.group(1).strip()
                    break
        
        # Extract vehicle descriptions
        vehicle_descriptions = self._extract_vehicle_descriptions_from_text(text_content)
        if vehicle_descriptions:
            extracted["vehicle_descriptions"] = vehicle_descriptions
        
        # Extract coverage information
        coverage_info = self._extract_coverage_info(text_content)
        if coverage_info:
            extracted["coverage_info"] = coverage_info
        
        # Extract tables if present
        if body_content.get("tables"):
            extracted["tables"] = body_content["tables"]
        
        return extracted
    
    def _extract_vehicle_descriptions_from_text(self, text: str) -> List[str]:
        """Extract vehicle descriptions from email text."""
        descriptions = []
        
        # Look for vehicle description patterns
        for pattern in self.vehicle_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)
                
                # Clean and validate description
                cleaned = self._clean_vehicle_description(match)
                if cleaned and len(cleaned) > 10:  # Minimum length check
                    descriptions.append(cleaned)
        
        # Look for vehicle lists or tables in text
        vehicle_list = self._extract_vehicle_list_from_text(text)
        descriptions.extend(vehicle_list)
        
        # Remove duplicates while preserving order
        unique_descriptions = []
        seen = set()
        for desc in descriptions:
            if desc.upper() not in seen:
                unique_descriptions.append(desc)
                seen.add(desc.upper())
        
        return unique_descriptions
    
    def _extract_vehicle_list_from_text(self, text: str) -> List[str]:
        """Extract vehicle list from structured text."""
        vehicles = []
        
        # Look for lines that look like vehicle descriptions
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or headers
            if not line or len(line) < 10:
                continue
            
            # Look for lines with vehicle characteristics
            if self._looks_like_vehicle_description(line):
                cleaned = self._clean_vehicle_description(line)
                if cleaned:
                    vehicles.append(cleaned)
        
        return vehicles
    
    def _looks_like_vehicle_description(self, line: str) -> bool:
        """Check if a line looks like a vehicle description."""
        line_upper = line.upper()
        
        # Check for vehicle-related keywords
        vehicle_keywords = [
            'TOYOTA', 'HONDA', 'NISSAN', 'MITSUBISHI', 'FORD', 'CHEVROLET',
            'VOLKSWAGEN', 'GENERAL MOTORS', 'GM', 'HYUNDAI', 'KIA',
            'TRACTO', 'REMOLQUE', 'CAMION', 'AUTO', 'PICKUP'
        ]
        
        # Check for year pattern
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', line))
        
        # Check for brand
        has_brand = any(keyword in line_upper for keyword in vehicle_keywords)
        
        # Check for vehicle characteristics
        has_characteristics = any(keyword in line_upper for keyword in [
            'DIESEL', 'GASOLINA', '4X4', '4X2', 'AUTOMATICO', 'MANUAL'
        ])
        
        return (has_brand and has_year) or (has_brand and has_characteristics)
    
    def _clean_vehicle_description(self, description: str) -> str:
        """Clean and normalize vehicle description."""
        if not description:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            r'^(?:VEHÍCULO|VEHICLE|UNIDAD):\s*',
            r'^\d+[\.\)]\s*',  # Remove numbering
            r'^[-\*]\s*'       # Remove bullet points
        ]
        
        for prefix in prefixes_to_remove:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE)
        
        # Convert to uppercase for consistency
        cleaned = cleaned.upper().strip()
        
        return cleaned if len(cleaned) > 5 else ""
    
    def _extract_coverage_info(self, text: str) -> List[Dict[str, str]]:
        """Extract coverage information from text."""
        coverages = []
        
        # Look for coverage patterns
        coverage_matches = re.findall(
            r'(?:COBERTURA|COVERAGE):\s*([A-Z\s]+)(?:\s+LÍMITE|LIMIT):\s*([0-9,\$\s]+)',
            text,
            re.IGNORECASE | re.MULTILINE
        )
        
        for coverage_match in coverage_matches:
            coverages.append({
                "coverage": coverage_match[0].strip(),
                "limit": coverage_match[1].strip()
            })
        
        return coverages
    
    async def extract_vehicle_descriptions(self, 
                                         processed_email: Dict[str, Any],
                                         attachments_data: List[Dict[str, Any]]) -> List[str]:
        """
        Extract vehicle descriptions from email and attachments.
        
        Args:
            processed_email: Processed email data
            attachments_data: Processed attachment data
            
        Returns:
            List of vehicle descriptions
        """
        all_descriptions = []
        
        # Extract from email text
        email_descriptions = processed_email.get("extracted_info", {}).get("vehicle_descriptions", [])
        all_descriptions.extend(email_descriptions)
        
        # Extract from email tables
        tables = processed_email.get("extracted_info", {}).get("tables", [])
        for table in tables:
            table_descriptions = self._extract_vehicles_from_table(table)
            all_descriptions.extend(table_descriptions)
        
        # Extract from attachments
        for attachment_data in attachments_data:
            if attachment_data.get("vehicle_data_found") == "yes":
                attachment_descriptions = attachment_data.get("extracted_vehicles", [])
                all_descriptions.extend(attachment_descriptions)
        
        # Remove duplicates and clean
        unique_descriptions = []
        seen = set()
        
        for desc in all_descriptions:
            cleaned = self._clean_vehicle_description(desc)
            if cleaned and cleaned.upper() not in seen and len(cleaned) > 10:
                unique_descriptions.append(cleaned)
                seen.add(cleaned.upper())
        
        logger.info("Vehicle descriptions extracted", 
                   total_found=len(all_descriptions),
                   unique_descriptions=len(unique_descriptions))
        
        return unique_descriptions
    
    def _extract_vehicles_from_table(self, table: Dict[str, Any]) -> List[str]:
        """Extract vehicle descriptions from table data."""
        descriptions = []
        rows = table.get("rows", [])
        
        if not rows:
            return descriptions
        
        # Try to identify vehicle-related columns
        header_row = rows[0] if rows else []
        vehicle_column_indices = []
        
        for i, header in enumerate(header_row):
            if any(keyword in header.upper() for keyword in [
                'VEHÍCULO', 'VEHICLE', 'DESCRIPCIÓN', 'DESCRIPTION', 'UNIDAD'
            ]):
                vehicle_column_indices.append(i)
        
        # If no specific vehicle columns found, look for descriptions in all columns
        if not vehicle_column_indices:
            vehicle_column_indices = list(range(len(header_row)))
        
        # Extract descriptions from identified columns
        for row in rows[1:]:  # Skip header row
            for col_index in vehicle_column_indices:
                if col_index < len(row):
                    cell_content = row[col_index]
                    if self._looks_like_vehicle_description(cell_content):
                        cleaned = self._clean_vehicle_description(cell_content)
                        if cleaned:
                            descriptions.append(cleaned)
        
        return descriptions
    
    async def extract_case_information(self, 
                                     processed_email: Dict[str, Any],
                                     attachments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract case information from email and attachments.
        
        Args:
            processed_email: Processed email data
            attachments_data: Processed attachment data
            
        Returns:
            Extracted case information
        """
        extracted_info = processed_email.get("extracted_info", {})
        metadata = processed_email.get("metadata", {})
        
        # Start with extracted information from email
        case_data = {
            "client_name": extracted_info.get("client_name"),
            "client_rfc": extracted_info.get("client_rfc"),
            "broker_name": extracted_info.get("broker_name"),
            "broker_email": extracted_info.get("broker_email"),
            "loss_history": self._extract_loss_history(processed_email),
            "policy_type": "FLEET_AUTO",  # Default for this folder
            "notes": f"Processed from email: {metadata.get('subject', '')}"
        }
        
        # If broker email not found in content, use sender email
        if not case_data["broker_email"]:
            case_data["broker_email"] = metadata.get("from_email")
        
        # If broker name not found, use sender name
        if not case_data["broker_name"]:
            case_data["broker_name"] = metadata.get("from_name")
        
        # Extract additional information from attachments
        for attachment_data in attachments_data:
            attachment_info = attachment_data.get("extracted_info", {})
            
            # Merge attachment information (prefer email content)
            for key, value in attachment_info.items():
                if value and not case_data.get(key):
                    case_data[key] = value
        
        # Clean and validate case data
        case_data = self._clean_case_data(case_data)
        
        logger.info("Case information extracted", 
                   client_name=case_data.get("client_name"),
                   broker_email=case_data.get("broker_email"),
                   has_client_rfc=bool(case_data.get("client_rfc")))
        
        return case_data
    
    def _extract_loss_history(self, processed_email: Dict[str, Any]) -> Optional[str]:
        """Extract loss history information from email."""
        text_content = processed_email.get("body_content", {}).get("text_content", "")
        
        # Look for loss history patterns
        loss_patterns = [
            r'(?:HISTORIAL DE SINIESTROS|LOSS HISTORY):\s*([A-Z\s]+)',
            r'(?:SINIESTROS|CLAIMS):\s*(SÍ|NO|YES|NO)',
            r'(?:SIN SINIESTROS|NO CLAIMS)',
            r'(?:CON SINIESTROS|WITH CLAIMS)'
        ]
        
        for pattern in loss_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
        
        return None
    
    def _clean_case_data(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate case data."""
        cleaned = {}
        
        for key, value in case_data.items():
            if value is None:
                cleaned[key] = None
                continue
            
            if isinstance(value, str):
                # Clean string values
                cleaned_value = value.strip()
                
                # Specific cleaning for different fields
                if key == "client_rfc":
                    # Validate and clean RFC
                    cleaned_value = re.sub(r'[^A-Z0-9]', '', cleaned_value.upper())
                    if len(cleaned_value) < 10 or len(cleaned_value) > 13:
                        cleaned_value = None
                elif key in ["client_name", "broker_name"]:
                    # Clean names
                    cleaned_value = re.sub(r'\s+', ' ', cleaned_value.title())
                elif key == "broker_email":
                    # Validate email format
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, cleaned_value):
                        cleaned_value = None
                
                cleaned[key] = cleaned_value if cleaned_value else None
            else:
                cleaned[key] = value
        
        return cleaned
    
    async def detect_email_type(self, processed_email: Dict[str, Any]) -> str:
        """
        Detect the type of insurance email.
        
        Args:
            processed_email: Processed email data
            
        Returns:
            Email type (fleet_quote, claim_report, policy_renewal, etc.)
        """
        subject = processed_email.get("metadata", {}).get("subject", "").upper()
        text_content = processed_email.get("body_content", {}).get("text_content", "").upper()
        
        # Check for fleet insurance keywords
        if any(keyword in subject or keyword in text_content for keyword in [
            "FLEET", "FLOTA", "COTIZACIÓN", "QUOTE", "VEHÍCULOS"
        ]):
            return "fleet_quote"
        
        # Check for claim keywords
        if any(keyword in subject or keyword in text_content for keyword in [
            "SINIESTRO", "CLAIM", "ACCIDENTE", "DAMAGE"
        ]):
            return "claim_report"
        
        # Check for renewal keywords
        if any(keyword in subject or keyword in text_content for keyword in [
            "RENOVACIÓN", "RENEWAL", "PÓLIZA", "POLICY"
        ]):
            return "policy_renewal"
        
        # Default to general inquiry
        return "general_inquiry"
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get email processing statistics."""
        return {
            "supported_patterns": {
                "vehicle_patterns": len(self.vehicle_patterns),
                "client_patterns": sum(len(patterns) for patterns in self.client_patterns.values()),
                "coverage_patterns": len(self.coverage_patterns)
            },
            "supported_content_types": ["text/html", "text/plain"],
            "supported_languages": ["spanish", "english"],
            "last_updated": datetime.utcnow().isoformat()
        }
