#!/usr/bin/env python3
"""
Vehicle matching service that works with preprocessed data from the database.
Handles the matching of preprocessed vehicles against the AMIS catalog.
"""

import asyncio
import logging
import sys
import pathlib
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add packages to path for local development
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "db" / "src"))
sys.path.insert(0, str(project_root / "packages" / "mq" / "src"))

from app.db.session import engine
from app.db.models import Run, Row, AmisRecord, Component, RunStatus
from app.mq.queue_factory import QueueFactory

logger = logging.getLogger(__name__)

class VehicleMatchingService:
    """Service for matching preprocessed vehicles against AMIS catalog"""
    
    def __init__(self):
        self.similarity_threshold = 0.8  # Minimum similarity score for matches
        self.max_candidates = 5  # Maximum number of candidates to return
    
    async def process_matching_request(self, run_id: str, case_id: str):
        """Process a matching request for preprocessed data"""
        try:
            logger.info(f"Processing matching request for run {run_id}")
            
            # Create a new CODIFY run
            codify_run = await self._create_codify_run(run_id, case_id)
            
            # Get preprocessed data
            preprocessed_data = await self._get_preprocessed_data(run_id)
            
            if not preprocessed_data:
                logger.warning(f"No preprocessed data found for run {run_id}")
                await self._update_run_status(codify_run.id, RunStatus.FAILED, 
                                            error="No preprocessed data found")
                return
            
            # Process each vehicle for matching
            matching_results = []
            for vehicle_data in preprocessed_data:
                try:
                    result = await self._match_single_vehicle(vehicle_data)
                    matching_results.append(result)
                except Exception as e:
                    logger.error(f"Error matching vehicle {vehicle_data.get('row_index')}: {e}")
                    # Continue with other vehicles
                    matching_results.append({
                        "row_index": vehicle_data.get("row_index"),
                        "error": str(e),
                        "success": False
                    })
            
            # Store results in database
            await self._store_matching_results(codify_run.id, matching_results)
            
            # Update run status
            successful_matches = sum(1 for r in matching_results if r.get("success", False))
            await self._update_run_status(
                codify_run.id, 
                RunStatus.SUCCESS,
                metrics={
                    "total_vehicles": len(matching_results),
                    "successful_matches": successful_matches,
                    "failed_matches": len(matching_results) - successful_matches
                }
            )
            
            logger.info(f"✅ Matching completed for run {run_id}: {successful_matches}/{len(matching_results)} vehicles matched")
            
        except Exception as e:
            logger.error(f"Error processing matching request for run {run_id}: {e}")
            await self._update_run_status(codify_run.id, RunStatus.FAILED, error=str(e))
    
    async def _create_codify_run(self, original_run_id: str, case_id: str) -> Run:
        """Create a new CODIFY run"""
        import uuid
        
        codify_run = Run(
            id=str(uuid.uuid4()),
            case_id=case_id,
            component=Component.CODIFY,
            status=RunStatus.STARTED,
            file_name=f"matching_for_{original_run_id}",
            created_at=pd.Timestamp.utcnow()
        )
        
        with Session(engine) as session:
            session.add(codify_run)
            session.commit()
            session.refresh(codify_run)
        
        logger.info(f"Created CODIFY run {codify_run.id} for case {case_id}")
        return codify_run
    
    async def _get_preprocessed_data(self, run_id: str) -> List[Dict[str, Any]]:
        """Get preprocessed data from database"""
        with Session(engine) as session:
            rows = session.query(Row).filter(
                Row.run_id == run_id,
                Row.transformed_data.isnot(None)
            ).all()
            
            preprocessed_data = []
            for row in rows:
                if row.transformed_data:
                    vehicle_data = {
                        "row_index": row.row_index,
                        "vin": row.transformed_data.get("vin"),
                        "brand": row.transformed_data.get("brand"),
                        "model": row.transformed_data.get("model"),
                        "model_year": row.transformed_data.get("model_year"),
                        "description": row.transformed_data.get("description"),
                        "license_plate": row.transformed_data.get("license_plate"),
                        "matching_key": row.transformed_data.get("matching_key"),
                        "raw_data": row.raw_data
                    }
                    preprocessed_data.append(vehicle_data)
            
            return preprocessed_data
    
    async def _match_single_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Match a single vehicle against AMIS catalog"""
        row_index = vehicle_data["row_index"]
        brand = vehicle_data.get("brand")
        model = vehicle_data.get("model")
        year = vehicle_data.get("model_year")
        description = vehicle_data.get("description")
        
        logger.info(f"Matching vehicle {row_index}: {brand} {model} {year}")
        
        # Find candidates in AMIS catalog
        candidates = await self._find_candidates(brand, model, year, description)
        
        if not candidates:
            return {
                "row_index": row_index,
                "success": False,
                "error": "No candidates found",
                "candidates": [],
                "confidence": 0.0,
                "decision": "no_match"
            }
        
        # Score and rank candidates
        scored_candidates = await self._score_candidates(vehicle_data, candidates)
        
        # Get best match
        best_match = scored_candidates[0] if scored_candidates else None
        
        if not best_match or best_match["score"] < self.similarity_threshold:
            return {
                "row_index": row_index,
                "success": False,
                "error": f"No matches above threshold {self.similarity_threshold}",
                "candidates": scored_candidates[:self.max_candidates],
                "confidence": best_match["score"] if best_match else 0.0,
                "decision": "no_match"
            }
        
        # Determine decision
        decision = "auto_accept" if best_match["score"] >= 0.9 else "needs_review"
        
        return {
            "row_index": row_index,
            "success": True,
            "suggested_cvegs": best_match["cvegs"],
            "candidates": scored_candidates[:self.max_candidates],
            "confidence": best_match["score"],
            "decision": decision,
            "matched_brand": best_match["brand"],
            "matched_model": best_match["model"],
            "matched_year": best_match["year"]
        }
    
    async def _find_candidates(self, brand: str, model: str, year: int, description: str) -> List[Dict[str, Any]]:
        """Find candidate vehicles in AMIS catalog"""
        with Session(engine) as session:
            # Build query for exact matches first
            query = session.query(AmisRecord).filter(
                AmisRecord.brand.ilike(f"%{brand}%") if brand else True,
                AmisRecord.model.ilike(f"%{model}%") if model else True,
                AmisRecord.year == year if year else True
            )
            
            candidates = query.limit(50).all()  # Limit for performance
            
            if not candidates and description:
                # Fallback to description search
                query = session.query(AmisRecord).filter(
                    AmisRecord.description.ilike(f"%{description[:50]}%")  # First 50 chars
                )
                candidates = query.limit(20).all()
            
            return [
                {
                    "cvegs": record.cvegs,
                    "brand": record.brand,
                    "model": record.model,
                    "year": record.year,
                    "description": record.description,
                    "body_type": record.body_type,
                    "use_type": record.use_type
                }
                for record in candidates
            ]
    
    async def _score_candidates(self, vehicle_data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank candidates"""
        scored_candidates = []
        
        target_brand = vehicle_data.get("brand", "").upper()
        target_model = vehicle_data.get("model", "").upper()
        target_year = vehicle_data.get("model_year")
        
        for candidate in candidates:
            score = 0.0
            score_components = {}
            
            # Brand matching (40% weight)
            brand_score = self._calculate_text_similarity(target_brand, candidate["brand"].upper())
            score += brand_score * 0.4
            score_components["brand"] = brand_score
            
            # Model matching (40% weight)
            model_score = self._calculate_text_similarity(target_model, candidate["model"].upper())
            score += model_score * 0.4
            score_components["model"] = model_score
            
            # Year matching (20% weight)
            year_score = 1.0 if target_year and candidate["year"] == target_year else 0.0
            score += year_score * 0.2
            score_components["year"] = year_score
            
            candidate["score"] = score
            candidate["score_components"] = score_components
            scored_candidates.append(candidate)
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_candidates
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple string matching"""
        if not text1 or not text2:
            return 0.0
        
        text1 = text1.upper().strip()
        text2 = text2.upper().strip()
        
        if text1 == text2:
            return 1.0
        
        if text1 in text2 or text2 in text1:
            return 0.8
        
        # Simple word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return overlap / union if union > 0 else 0.0
    
    async def _store_matching_results(self, codify_run_id: str, results: List[Dict[str, Any]]):
        """Store matching results in database"""
        from app.db.models import Codify
        
        with Session(engine) as session:
            for result in results:
                if result.get("success", False):
                    codify_result = Codify(
                        run_id=codify_run_id,
                        row_idx=result["row_index"],
                        suggested_cvegs=result.get("suggested_cvegs"),
                        confidence=result.get("confidence", 0.0),
                        candidates=result.get("candidates", []),
                        decision=result.get("decision", "no_match")
                    )
                else:
                    codify_result = Codify(
                        run_id=codify_run_id,
                        row_idx=result["row_index"],
                        suggested_cvegs=None,
                        confidence=0.0,
                        candidates=result.get("candidates", []),
                        decision="no_match"
                    )
                
                session.add(codify_result)
            
            session.commit()
        
        logger.info(f"Stored {len(results)} matching results for run {codify_run_id}")
    
    async def _update_run_status(self, run_id: str, status: RunStatus, metrics: dict = None, error: str = None):
        """Update run status in database"""
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = status
                run.finished_at = pd.Timestamp.utcnow()
                
                if metrics:
                    run.metrics = run.metrics or {}
                    run.metrics.update(metrics)
                
                if error:
                    run.metrics = run.metrics or {}
                    run.metrics['error'] = error
                
                session.commit()
                logger.info(f"Updated run {run_id} status to {status.value}")
