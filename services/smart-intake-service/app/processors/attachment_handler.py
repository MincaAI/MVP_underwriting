import os
import io
import re
import structlog
from typing import Dict, Any, List, Optional

from ..auth.graph_client import GraphAPIClient

logger = structlog.get_logger()


class AttachmentHandler:
    """Basic attachment processing used by email_tasks to extract vehicle data."""

    def __init__(self) -> None:
        # Reserved for future dependency injection (storage, filetype detection, etc.)
        pass

    async def process_attachment(
        self,
        message_id: str,
        attachment_info: Dict[str, Any],
        graph_client: GraphAPIClient,
    ) -> Dict[str, Any]:
        """
        Download an attachment and attempt to extract vehicle-like descriptions.

        Args:
            message_id: Microsoft Graph message ID the attachment belongs to
            attachment_info: Attachment metadata from Graph
            graph_client: Graph client to download the attachment content

        Returns:
            A dict with:
              - info: original attachment_info
              - content_type: detected content type (best-effort)
              - size_bytes: size of downloaded content
              - vehicle_data_found: "yes" | "no"
              - extracted_vehicles: List[str]
              - extracted_info: Dict[str, Any] (placeholder for future fields)
        """
        name = attachment_info.get("name") or "attachment"
        content_type = (attachment_info.get("contentType") or "").lower()
        attachment_id = attachment_info.get("id")

        if not attachment_id:
            logger.warning("Attachment missing id; skipping", message_id=message_id, name=name)
            return {
                "info": attachment_info,
                "content_type": content_type or "unknown",
                "size_bytes": 0,
                "vehicle_data_found": "no",
                "extracted_vehicles": [],
                "extracted_info": {},
            }

        # Download bytes from Graph
        try:
            content_bytes = await graph_client.get_attachment(message_id, attachment_id)
        except Exception as e:
            logger.error("Failed to download attachment", message_id=message_id, name=name, error=str(e))
            return {
                "info": attachment_info,
                "content_type": content_type or "unknown",
                "size_bytes": 0,
                "vehicle_data_found": "no",
                "extracted_vehicles": [],
                "extracted_info": {"error": str(e)},
            }

        size_bytes = len(content_bytes or b"")
        logger.info("Attachment downloaded", message_id=message_id, name=name, size_bytes=size_bytes)

        # Best-effort type detection by extension if contentType is not helpful
        ext = os.path.splitext(name)[1].lower()
        if not content_type or content_type == "application/octet-stream":
            content_type = self._infer_content_type_from_ext(ext) or content_type or "unknown"

        extracted_vehicles: List[str] = []
        vehicle_data_found = "no"

        # Very lightweight extraction for text-like formats
        if self._is_textual(content_type, ext):
            try:
                text = self._to_text(content_bytes)
                extracted_vehicles = self._extract_vehicle_descriptions_from_text(text)
                vehicle_data_found = "yes" if extracted_vehicles else "no"
            except Exception as e:
                logger.warning("Failed basic text extraction", name=name, error=str(e))
        else:
            # For non-text formats (xlsx/pdf), keep placeholder for future implementations
            logger.debug("Non-text attachment type; skipping deep parse", name=name, content_type=content_type)

        return {
            "info": attachment_info,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "vehicle_data_found": vehicle_data_found,
            "extracted_vehicles": extracted_vehicles,
            "extracted_info": {},  # Placeholder for future enrichment
        }

    def _infer_content_type_from_ext(self, ext: str) -> Optional[str]:
        mapping = {
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".pdf": "application/pdf",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return mapping.get(ext)

    def _is_textual(self, content_type: str, ext: str) -> bool:
        if content_type.startswith("text/"):
            return True
        return ext in {".txt", ".csv", ".json"}

    def _to_text(self, data: bytes) -> str:
        # Attempt UTF-8 then latin-1 as fallback to avoid crashes on weird encodings
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode("latin-1", errors="replace")

    def _extract_vehicle_descriptions_from_text(self, text: str) -> List[str]:
        """
        Minimal heuristic extraction: pick lines that look like vehicle descriptions.
        Heuristics:
          - Contains a vehicle brand keyword OR looks like an all-caps start
          - Contains a 4-digit year (19xx/20xx) or vehicle characteristics
        """
        candidates: List[str] = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        brand_keywords = [
            "TOYOTA", "HONDA", "NISSAN", "MITSUBISHI", "FORD", "CHEVROLET", "VOLKSWAGEN", "HYUNDAI", "KIA",
            "BMW", "MERCEDES", "AUDI", "RENAULT", "PEUGEOT", "FIAT", "JEEP", "MAZDA", "DODGE", "RAM", "GMC",
        ]

        def looks_like_vehicle(line: str) -> bool:
            up = line.upper()
            has_brand = any(b in up for b in brand_keywords)
            has_year = bool(re.search(r"\b(19|20)\d{2}\b", up))
            has_characteristics = any(k in up for k in ["4X4", "4X2", "DIESEL", "GASOLINA", "AUTOMATIC", "MANUAL"])
            # Generic pattern like "BRAND MODEL 2020"
            generic = bool(re.search(r"^[A-Z][A-Z0-9\-\s]{3,}\b(19|20)\d{2}\b", up))
            return (has_brand and (has_year or has_characteristics)) or generic

        for ln in lines:
            if len(ln) < 8:
                continue
            if looks_like_vehicle(ln):
                cleaned = self._clean_vehicle_description(ln)
                if cleaned:
                    candidates.append(cleaned)

        # De-duplicate preserving order
        unique: List[str] = []
        seen = set()
        for c in candidates:
            key = c.upper()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _clean_vehicle_description(self, desc: str) -> str:
        cleaned = re.sub(r"\s+", " ", desc).strip().upper()
        cleaned = re.sub(r"^(VEH[IÍ]CULO|VEHICLE|UNIDAD):\s*", "", cleaned)
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        cleaned = re.sub(r"^[-\*]\s*", "", cleaned)
        return cleaned if len(cleaned) > 5 else ""