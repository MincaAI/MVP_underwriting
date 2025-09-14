import time
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import structlog

from ..config.settings import get_settings, get_insurer_config
from ..models.vehicle import VehicleInput, VehicleAttributes, MatchResult
from .data_loader import DataLoader
from .preprocessor import VehiclePreprocessor
from .llm_extractor import LLMAttributeExtractor

logger = structlog.get_logger()


class CVEGSMatcher:
    """Core vehicle-to-CVEGS matching engine."""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_loader = DataLoader()
        self.preprocessor = VehiclePreprocessor()
        self.llm_extractor = LLMAttributeExtractor()
        
        # Initialize TF-IDF vectorizer for semantic similarity
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # We'll handle Spanish stop words manually
            ngram_range=(1, 2),
            lowercase=True
        )
        
        # Cache for vectorized datasets
        self.vectorized_datasets: Dict[str, Any] = {}
    
    async def initialize_insurer(self, insurer_id: str):
        """Initialize data for a specific insurer."""
        insurer_config = get_insurer_config(insurer_id)
        
        # Load dataset
        dataset = self.data_loader.load_dataset(insurer_config)
        
        # Prepare TF-IDF vectors for semantic matching
        if insurer_id not in self.vectorized_datasets:
            self._prepare_semantic_vectors(insurer_id, dataset)
        
        logger.info("Insurer initialized", 
                   insurer_id=insurer_id, 
                   records=len(dataset))
    
    def _prepare_semantic_vectors(self, insurer_id: str, dataset: pd.DataFrame):
        """Prepare TF-IDF vectors for semantic similarity matching."""
        try:
            # Combine description text for vectorization
            descriptions = dataset['description'].fillna('').astype(str).tolist()
            
            # Fit and transform descriptions
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(descriptions)
            
            # Store vectorized data
            self.vectorized_datasets[insurer_id] = {
                'tfidf_matrix': tfidf_matrix,
                'vectorizer': self.tfidf_vectorizer,
                'dataset_indices': dataset.index.tolist()
            }
            
            logger.info("Semantic vectors prepared", 
                       insurer_id=insurer_id,
                       vector_shape=tfidf_matrix.shape)
            
        except Exception as e:
            logger.error("Failed to prepare semantic vectors", 
                        insurer_id=insurer_id, error=str(e))
    
    async def match_vehicle(self, vehicle_input: VehicleInput) -> MatchResult:
        """
        Match a single vehicle description to CVEGS code.
        
        Args:
            vehicle_input: Vehicle input with description and metadata
            
        Returns:
            MatchResult with best match and confidence score
        """
        start_time = time.time()
        
        try:
            # Initialize insurer data if needed
            await self.initialize_insurer(vehicle_input.insurer_id)
            
            # Step 1: Preprocess the input (with Excel data context)
            preprocessed = self.preprocessor.preprocess(
                vehicle_input.description, 
                vehicle_input.year,
                known_brand=vehicle_input.brand,
                known_model=vehicle_input.model
            )
            
            # Step 2: Create Excel attributes from pre-extracted fields
            excel_attributes = self._create_excel_attributes(vehicle_input)
            
            # Step 3: Extract additional attributes using LLM (focus on description details)
            llm_attributes = await self.llm_extractor.extract_attributes(
                vehicle_input.description,
                known_brand=vehicle_input.brand,
                known_model=vehicle_input.model,
                known_year=vehicle_input.year
            )
            
            # Step 4: Combine Excel, rule-based and LLM attributes
            combined_attributes = self._combine_attributes(
                preprocessed['attributes'], 
                llm_attributes,
                excel_attributes
            )
            
            # Step 5: Find candidate matches (enhanced filtering)
            candidates = self._find_enhanced_candidates(
                vehicle_input.insurer_id,
                combined_attributes
            )
            
            if candidates.empty:
                return self._create_no_match_result(
                    vehicle_input, combined_attributes, start_time
                )
            
            # Step 6: Score candidates using enhanced attribute-based matching
            scored_candidates = await self._score_candidates_enhanced(
                vehicle_input.insurer_id,
                vehicle_input.description,
                combined_attributes,
                candidates
            )
            
            # Step 7: Select best match with tie-breaker logic
            best_match, tie_breaker_used = await self._select_best_match_with_tiebreaker(
                vehicle_input, scored_candidates
            )
            
            # Step 8: Calculate final confidence with enhanced scoring
            confidence_score = self._calculate_enhanced_confidence(
                combined_attributes, 
                best_match, 
                scored_candidates
            )
            
            # Step 9: Create enhanced result
            processing_time = (time.time() - start_time) * 1000
            
            # Generate attribute match breakdown
            attribute_matches = self._generate_attribute_matches(
                combined_attributes, best_match
            )
            
            result = MatchResult(
                cvegs_code=str(best_match['cvegs_code']),
                confidence_score=confidence_score,
                confidence_level="high",  # Will be set by validator
                matched_brand=str(best_match['brand']),
                matched_model=str(best_match['model']),
                matched_year=int(best_match['actual_year']) if pd.notna(best_match['actual_year']) else None,
                matched_description=str(best_match['description']),
                extracted_attributes=combined_attributes,
                processing_time_ms=processing_time,
                candidates_evaluated=len(candidates),
                match_method="enhanced_attribute_based",
                attribute_matches=attribute_matches,
                tie_breaker_used=tie_breaker_used,
                source_row=vehicle_input.source_row,
                warnings=self._generate_enhanced_warnings(combined_attributes, best_match, confidence_score)
            )
            
            logger.info("Vehicle matched successfully",
                       description=vehicle_input.description,
                       cvegs_code=result.cvegs_code,
                       confidence=confidence_score,
                       processing_time_ms=processing_time)
            
            return result
            
        except Exception as e:
            logger.error("Error matching vehicle", 
                        description=vehicle_input.description, 
                        error=str(e))
            
            processing_time = (time.time() - start_time) * 1000
            return self._create_error_result(vehicle_input, str(e), processing_time)
    
    def _combine_attributes(self, 
                          rule_based: VehicleAttributes, 
                          llm_based: VehicleAttributes,
                          excel_attributes: Optional[VehicleAttributes] = None) -> VehicleAttributes:
        """Combine Excel, rule-based and LLM-extracted attributes with priority hierarchy."""
        
        # Start with empty dict to build from scratch
        combined_dict = {}
        
        # First, apply rule-based attributes (lowest priority)
        rule_dict = rule_based.dict()
        for key, value in rule_dict.items():
            if value is not None and key not in ['excel_confidence', 'llm_confidence']:
                combined_dict[key] = value
        
        # Apply LLM attributes (medium confidence) - override rule-based
        llm_dict = llm_based.dict()
        for key, llm_value in llm_dict.items():
            if llm_value is not None and key not in ['excel_confidence', 'llm_confidence']:
                combined_dict[key] = llm_value
        
        # Apply Excel attributes (highest confidence) - these override everything else
        if excel_attributes:
            excel_dict = excel_attributes.dict()
            for key, excel_value in excel_dict.items():
                if excel_value is not None and key not in ['excel_confidence', 'llm_confidence']:
                    combined_dict[key] = excel_value
        
        # Set confidence scores
        combined_dict['excel_confidence'] = 0.95 if excel_attributes else 0.0
        combined_dict['llm_confidence'] = llm_based.llm_confidence if hasattr(llm_based, 'llm_confidence') else 0.8
        
        # Ensure we have defaults for required fields that might be missing
        defaults = {
            'brand': None,
            'model': None,
            'year': None,
            'vin': None,
            'coverage_package': None,
            'fuel_type': None,
            'drivetrain': None,
            'body_style': None,
            'trim_level': None,
            'engine_size': None,
            'transmission': None,
            'doors': None
        }
        
        for key, default_value in defaults.items():
            if key not in combined_dict:
                combined_dict[key] = default_value
        
        return VehicleAttributes(**combined_dict)
    
    def _create_excel_attributes(self, vehicle_input: VehicleInput) -> Optional[VehicleAttributes]:
        """Create VehicleAttributes from Excel pre-extracted fields."""
        # Only create if we have some Excel data
        if not any([vehicle_input.brand, vehicle_input.model, vehicle_input.year, 
                   vehicle_input.vin, vehicle_input.coverage_package]):
            return None
            
        return VehicleAttributes(
            brand=vehicle_input.brand,
            model=vehicle_input.model,
            year=vehicle_input.year,
            vin=vehicle_input.vin,
            coverage_package=vehicle_input.coverage_package,
            excel_confidence=0.95  # High confidence for structured Excel data
        )
    
    def _find_enhanced_candidates(self, 
                                insurer_id: str, 
                                attributes: VehicleAttributes) -> pd.DataFrame:
        """Enhanced candidate finding with stricter Excel-based filtering."""
        
        # Step 6: First filter by brand and year (strict)
        if attributes.brand and attributes.year:
            candidates = self.data_loader.filter_candidates(
                insurer_id=insurer_id,
                brand=attributes.brand,
                year=attributes.year
            )
            
            # Step 7: Within brand+year, match model/sub-brand with fuzzy logic
            if not candidates.empty and attributes.model:
                candidates = self._filter_by_model_fuzzy(candidates, attributes.model)
        else:
            # Fallback to broader search if Excel data incomplete
            return self._find_candidates_fallback(insurer_id, attributes)
        
        # If strict filtering yields no results, try progressive relaxation
        if candidates.empty:
            return self._find_candidates_progressive(insurer_id, attributes)
        
        # Limit candidates to prevent performance issues
        max_candidates = self.settings.max_candidates
        if len(candidates) > max_candidates:
            candidates = candidates.head(max_candidates)
        
        logger.debug("Enhanced candidates found", 
                    insurer_id=insurer_id,
                    brand=attributes.brand,
                    year=attributes.year,
                    model=attributes.model,
                    candidates_found=len(candidates))
        
        return candidates
    
    def _filter_by_model_fuzzy(self, candidates: pd.DataFrame, target_model: str) -> pd.DataFrame:
        """Filter candidates by model with fuzzy matching and alias handling."""
        from rapidfuzz import fuzz
        
        def model_similarity(candidate_model: str) -> float:
            if pd.isna(candidate_model):
                return 0.0
            
            candidate_model = str(candidate_model).upper().strip()
            target_model_upper = target_model.upper().strip()
            
            # Exact match
            if candidate_model == target_model_upper:
                return 1.0
            
            # Fuzzy matching for variations like "L200" vs "L 200"
            ratio = fuzz.ratio(target_model_upper, candidate_model) / 100.0
            
            # Boost score for partial matches
            if target_model_upper in candidate_model or candidate_model in target_model_upper:
                ratio = max(ratio, 0.9)
            
            return ratio
        
        # Calculate similarity scores
        candidates = candidates.copy()
        candidates['model_similarity'] = candidates['model'].apply(model_similarity)
        
        # Filter by similarity threshold
        similarity_threshold = 0.8
        filtered = candidates[candidates['model_similarity'] >= similarity_threshold]
        
        # Sort by similarity
        return filtered.sort_values('model_similarity', ascending=False)
    
    def _find_candidates_progressive(self, 
                                   insurer_id: str, 
                                   attributes: VehicleAttributes) -> pd.DataFrame:
        """Progressive candidate search with relaxed constraints."""
        
        # Try brand + year without model
        if attributes.brand and attributes.year:
            candidates = self.data_loader.filter_candidates(
                insurer_id=insurer_id,
                brand=attributes.brand,
                year=attributes.year
            )
            if not candidates.empty:
                return candidates
        
        # Try brand only
        if attributes.brand:
            candidates = self.data_loader.filter_candidates(
                insurer_id=insurer_id,
                brand=attributes.brand
            )
            if not candidates.empty:
                return candidates
        
        # Last resort: return empty
        return pd.DataFrame()
    
    def _find_candidates_fallback(self, 
                                insurer_id: str, 
                                attributes: VehicleAttributes) -> pd.DataFrame:
        """Fallback candidate search for incomplete Excel data."""
        
        # Use original logic for cases where Excel extraction failed
        candidates = self.data_loader.filter_candidates(
            insurer_id=insurer_id,
            brand=attributes.brand,
            year=attributes.year,
            model=attributes.model
        )
        
        # Progressive relaxation
        if candidates.empty and attributes.brand:
            candidates = self.data_loader.filter_candidates(
                insurer_id=insurer_id,
                brand=attributes.brand,
                year=attributes.year
            )
        
        if candidates.empty and attributes.brand:
            candidates = self.data_loader.filter_candidates(
                insurer_id=insurer_id,
                brand=attributes.brand
            )
        
        return candidates
    
    async def _score_candidates_enhanced(self, 
                                       insurer_id: str,
                                       original_description: str,
                                       attributes: VehicleAttributes,
                                       candidates: pd.DataFrame) -> pd.DataFrame:
        """Enhanced candidate scoring following the detailed attribute matching guidelines."""
        
        if candidates.empty:
            return candidates
        
        # Make a copy to avoid modifying original
        scored = candidates.copy()
        
        # Step 9: Attribute-Based Matching with detailed checks
        scored['fuel_match'] = scored.apply(
            lambda row: self._check_fuel_match(attributes.fuel_type, row), axis=1
        )
        scored['drivetrain_match'] = scored.apply(
            lambda row: self._check_drivetrain_match(attributes.drivetrain, row), axis=1
        )
        scored['body_match'] = scored.apply(
            lambda row: self._check_body_style_match(attributes.body_style, row), axis=1
        )
        scored['trim_match'] = scored.apply(
            lambda row: self._check_trim_match(attributes.trim_level, row), axis=1
        )
        
        # Calculate attribute-based score with proper weights
        scored['attribute_score'] = (
            scored['fuel_match'] * 1.0 +
            scored['drivetrain_match'] * 1.0 +
            scored['body_match'] * 1.0 +
            scored['trim_match'] * 0.5
        ) / 3.5  # Normalize to 0-1
        
        # Semantic similarity (reduced weight since we have better attribute matching)
        scored['semantic_score'] = await self._calculate_semantic_scores(
            insurer_id, original_description, candidates
        )
        
        # Token overlap (for fallback)
        scored['token_score'] = self._calculate_token_scores(
            original_description, candidates
        )
        
        # Enhanced combined score (favor attribute matching)
        scored['combined_score'] = (
            scored['attribute_score'] * 0.6 +  # Higher weight for attribute matching
            scored['semantic_score'] * 0.25 +
            scored['token_score'] * 0.15
        )
        
        # Sort by combined score
        scored = scored.sort_values('combined_score', ascending=False)
        
        return scored
    
    def _calculate_attribute_score(self, 
                                 attributes: VehicleAttributes, 
                                 candidate_row: pd.Series) -> float:
        """Calculate attribute-based similarity score."""
        score = 0.0
        total_weight = 0.0
        
        # Brand match (high weight)
        if attributes.brand and pd.notna(candidate_row.get('brand')):
            weight = 0.3
            total_weight += weight
            if attributes.brand.upper() == str(candidate_row['brand']).upper():
                score += weight
        
        # Model match (high weight)
        if attributes.model and pd.notna(candidate_row.get('model')):
            weight = 0.3
            total_weight += weight
            if attributes.model.upper() in str(candidate_row['model']).upper():
                score += weight
        
        # Year match (medium weight)
        if attributes.year and pd.notna(candidate_row.get('actual_year')):
            weight = 0.2
            total_weight += weight
            if attributes.year == candidate_row['actual_year']:
                score += weight
        
        # Fuel type match (low weight)
        if attributes.fuel_type:
            weight = 0.1
            total_weight += weight
            desc = str(candidate_row.get('description', '')).upper()
            if attributes.fuel_type.upper() in desc:
                score += weight
        
        # Drivetrain match (low weight)
        if attributes.drivetrain:
            weight = 0.1
            total_weight += weight
            desc = str(candidate_row.get('description', '')).upper()
            if attributes.drivetrain.upper() in desc:
                score += weight
        
        # Normalize score
        return score / total_weight if total_weight > 0 else 0.0
    
    async def _calculate_semantic_scores(self, 
                                       insurer_id: str,
                                       description: str, 
                                       candidates: pd.DataFrame) -> List[float]:
        """Calculate semantic similarity scores using TF-IDF."""
        
        if insurer_id not in self.vectorized_datasets:
            return [0.0] * len(candidates)
        
        try:
            vectorized_data = self.vectorized_datasets[insurer_id]
            vectorizer = vectorized_data['vectorizer']
            tfidf_matrix = vectorized_data['tfidf_matrix']
            
            # Vectorize input description
            input_vector = vectorizer.transform([description])
            
            # Get candidate indices in the original dataset
            candidate_indices = candidates.index.tolist()
            
            # Calculate similarities
            similarities = []
            for idx in candidate_indices:
                if idx < tfidf_matrix.shape[0]:
                    candidate_vector = tfidf_matrix[idx:idx+1]
                    similarity = cosine_similarity(input_vector, candidate_vector)[0][0]
                    similarities.append(similarity)
                else:
                    similarities.append(0.0)
            
            return similarities
            
        except Exception as e:
            logger.warning("Failed to calculate semantic scores", error=str(e))
            return [0.0] * len(candidates)
    
    def _calculate_token_scores(self, 
                              description: str, 
                              candidates: pd.DataFrame) -> List[float]:
        """Calculate token overlap scores."""
        
        input_tokens = set(self.preprocessor.get_search_tokens(description))
        
        scores = []
        for _, row in candidates.iterrows():
            candidate_tokens = row.get('tokens', set())
            if isinstance(candidate_tokens, set) and input_tokens:
                # Jaccard similarity
                intersection = len(input_tokens.intersection(candidate_tokens))
                union = len(input_tokens.union(candidate_tokens))
                score = intersection / union if union > 0 else 0.0
            else:
                score = 0.0
            scores.append(score)
        
        return scores
    
    async def _select_best_match_with_tiebreaker(self, 
                                               vehicle_input: VehicleInput,
                                               scored_candidates: pd.DataFrame) -> Tuple[pd.Series, bool]:
        """Select the best match with LLM tie-breaker for close scores."""
        if scored_candidates.empty:
            raise ValueError("No candidates to select from")
        
        # Check for ties (multiple candidates with very close scores)
        best_score = scored_candidates.iloc[0]['combined_score']
        tie_threshold = 0.05  # 5% difference considered a tie
        
        tied_candidates = scored_candidates[
            scored_candidates['combined_score'] >= (best_score - tie_threshold)
        ]
        
        # If no tie or only one candidate, return the best
        if len(tied_candidates) <= 1:
            return scored_candidates.iloc[0], False
        
        # Use LLM tie-breaker for multiple close matches
        try:
            best_match_cvegs = await self._resolve_ties_with_llm(
                vehicle_input, tied_candidates.head(3)  # Limit to top 3 for efficiency
            )
            
            # Find the candidate with the LLM-selected CVEGS code
            selected_candidate = tied_candidates[
                tied_candidates['cvegs_code'] == best_match_cvegs
            ]
            
            if not selected_candidate.empty:
                return selected_candidate.iloc[0], True
            
        except Exception as e:
            logger.warning("LLM tie-breaker failed, using highest score", error=str(e))
        
        # Fallback to highest score
        return scored_candidates.iloc[0], False
    
    def _calculate_enhanced_confidence(self, 
                                     attributes: VehicleAttributes,
                                     best_match: pd.Series,
                                     scored_candidates: pd.DataFrame) -> float:
        """Calculate enhanced confidence score with Excel data confidence."""
        
        if scored_candidates.empty:
            return 0.0
        
        # Base confidence from combined score
        base_confidence = best_match['combined_score']
        
        # Excel data confidence boost (high confidence for structured data)
        excel_boost = 0.0
        if attributes.brand and attributes.brand.upper() == str(best_match['brand']).upper():
            excel_boost += 0.15  # Higher boost for Excel-extracted brand
        if attributes.model and attributes.model.upper() in str(best_match['model']).upper():
            excel_boost += 0.15  # Higher boost for Excel-extracted model
        if attributes.year and attributes.year == best_match.get('actual_year'):
            excel_boost += 0.1   # Year match from Excel
        
        # Attribute match boost
        attribute_boost = 0.0
        if hasattr(best_match, 'fuel_match') and best_match.get('fuel_match', False):
            attribute_boost += 0.05
        if hasattr(best_match, 'drivetrain_match') and best_match.get('drivetrain_match', False):
            attribute_boost += 0.05
        if hasattr(best_match, 'body_match') and best_match.get('body_match', False):
            attribute_boost += 0.05
        
        # Reduce confidence if there are many similar matches
        competition_penalty = 0.0
        if len(scored_candidates) > 1:
            second_best_score = scored_candidates.iloc[1]['combined_score']
            score_gap = best_match['combined_score'] - second_best_score
            if score_gap < 0.05:  # Very close scores
                competition_penalty = 0.1
        
        # Factor in Excel data confidence
        excel_confidence_factor = attributes.excel_confidence if hasattr(attributes, 'excel_confidence') else 0.8
        
        final_confidence = min(1.0, (
            base_confidence + excel_boost + attribute_boost - competition_penalty
        ) * excel_confidence_factor)
        
        return max(0.0, final_confidence)
    
    def _generate_enhanced_warnings(self, 
                                  attributes: VehicleAttributes,
                                  best_match: pd.Series,
                                  confidence: float) -> List[str]:
        """Generate enhanced warnings for the match result."""
        warnings = []
        
        if confidence < 0.7:
            warnings.append("Low confidence match - manual review recommended")
        elif confidence < 0.85:
            warnings.append("Medium confidence match - consider review")
        
        # Excel data completeness warnings
        if not attributes.brand:
            warnings.append("Brand not provided in Excel data")
        if not attributes.model:
            warnings.append("Model not provided in Excel data")
        if not attributes.year:
            warnings.append("Year not provided in Excel data")
        
        # Mismatch warnings
        if attributes.brand and attributes.brand.upper() != str(best_match['brand']).upper():
            warnings.append(f"Brand mismatch: Excel '{attributes.brand}' vs matched '{best_match['brand']}'")
        
        if attributes.model and attributes.model.upper() not in str(best_match['model']).upper():
            warnings.append(f"Model mismatch: Excel '{attributes.model}' vs matched '{best_match['model']}'")
        
        # Attribute match warnings
        if hasattr(best_match, 'fuel_match') and not best_match.get('fuel_match', True):
            warnings.append("Fuel type mismatch detected")
        
        if hasattr(best_match, 'drivetrain_match') and not best_match.get('drivetrain_match', True):
            warnings.append("Drivetrain mismatch detected")
        
        return warnings
    
    def _check_fuel_match(self, input_fuel: Optional[str], candidate_row: pd.Series) -> bool:
        """Step 10: Check fuel type matching with Spanish/English variations."""
        if not input_fuel:
            return True  # No constraint
        
        candidate_desc = str(candidate_row.get('description', '')).upper()
        input_fuel_upper = input_fuel.upper()
        
        # Fuel type mappings
        fuel_mappings = {
            'DIESEL': ['DIESEL', 'TD', 'TDI'],
            'GASOLINA': ['GASOLINA', 'GASOLINE', 'GAS', 'NAFTA'],
            'ELECTRIC': ['ELECTRIC', 'ELECTRICO'],
            'HYBRID': ['HYBRID', 'HIBRIDO']
        }
        
        # Check for matches
        if input_fuel_upper in fuel_mappings:
            return any(variant in candidate_desc for variant in fuel_mappings[input_fuel_upper])
        else:
            # Direct match fallback
            return input_fuel_upper in candidate_desc
    
    def _check_drivetrain_match(self, input_drivetrain: Optional[str], candidate_row: pd.Series) -> bool:
        """Step 11: Check drivetrain matching."""
        if not input_drivetrain:
            return True  # No constraint
        
        candidate_desc = str(candidate_row.get('description', '')).upper()
        input_drivetrain_upper = input_drivetrain.upper()
        
        # Direct match for drivetrain (usually standardized)
        drivetrain_variants = {
            '4X4': ['4X4', '4WD', 'AWD'],
            '4X2': ['4X2', '2WD', 'FWD', 'RWD']
        }
        
        if input_drivetrain_upper in drivetrain_variants:
            return any(variant in candidate_desc for variant in drivetrain_variants[input_drivetrain_upper])
        else:
            return input_drivetrain_upper in candidate_desc
    
    def _check_body_style_match(self, input_body: Optional[str], candidate_row: pd.Series) -> bool:
        """Step 12: Check body style/doors matching with complex mappings."""
        if not input_body:
            return True  # No constraint
        
        candidate_desc = str(candidate_row.get('description', '')).upper()
        input_body_upper = input_body.upper()
        
        # Body style mappings (Spanish/English with abbreviations)
        body_mappings = {
            'DOUBLE_CAB': ['DC', 'DOBLE CABINA', 'DOUBLE CAB', '4P', 'CB'],
            'SINGLE_CAB': ['SC', 'CABINA SIMPLE', 'SINGLE CAB', '2P'],
            'SEDAN': ['SEDAN', '4P', '4 PUERTAS', '4 DOORS'],
            'SUV': ['SUV', 'SPORT UTILITY'],
            'HATCHBACK': ['HATCHBACK', '5P', '5 PUERTAS'],
            'PICKUP': ['PICKUP', 'PICK UP', 'CAMIONETA']
        }
        
        if input_body_upper in body_mappings:
            return any(variant in candidate_desc for variant in body_mappings[input_body_upper])
        else:
            return input_body_upper in candidate_desc
    
    def _check_trim_match(self, input_trim: Optional[str], candidate_row: pd.Series) -> bool:
        """Step 13: Check trim/package keywords matching."""
        if not input_trim:
            return True  # No constraint
        
        candidate_desc = str(candidate_row.get('description', '')).upper()
        input_trim_upper = input_trim.upper()
        
        # Direct match for trim levels (usually specific names)
        return input_trim_upper in candidate_desc
    
    def _generate_attribute_matches(self, 
                                  attributes: VehicleAttributes, 
                                  best_match: pd.Series) -> Dict[str, bool]:
        """Generate detailed attribute match breakdown for result."""
        matches = {
            'brand_match': False,
            'model_match': False,
            'year_match': False,
            'fuel_match': True,  # Default true if not specified
            'drivetrain_match': True,
            'body_match': True,
            'trim_match': True
        }
        
        # Brand match
        if attributes.brand:
            matches['brand_match'] = (
                attributes.brand.upper() == str(best_match['brand']).upper()
            )
        
        # Model match
        if attributes.model:
            matches['model_match'] = (
                attributes.model.upper() in str(best_match['model']).upper()
            )
        
        # Year match
        if attributes.year:
            matches['year_match'] = (
                attributes.year == best_match.get('actual_year')
            )
        
        # Attribute matches
        if attributes.fuel_type:
            matches['fuel_match'] = self._check_fuel_match(attributes.fuel_type, best_match)
        
        if attributes.drivetrain:
            matches['drivetrain_match'] = self._check_drivetrain_match(attributes.drivetrain, best_match)
        
        if attributes.body_style:
            matches['body_match'] = self._check_body_style_match(attributes.body_style, best_match)
        
        if attributes.trim_level:
            matches['trim_match'] = self._check_trim_match(attributes.trim_level, best_match)
        
        return matches
    
    async def _resolve_ties_with_llm(self, 
                                   vehicle_input: VehicleInput, 
                                   tied_candidates: pd.DataFrame) -> str:
        """Use LLM to resolve ties between close matches."""
        
        candidates_text = "\n".join([
            f"Option {i+1}: {row['description']} (CVEGS: {row['cvegs_code']})"
            for i, (_, row) in enumerate(tied_candidates.iterrows())
        ])
        
        llm_prompt = f"""
Vehicle to match:
Description: "{vehicle_input.description}"
Brand: {vehicle_input.brand or 'Unknown'}
Model: {vehicle_input.model or 'Unknown'}
Year: {vehicle_input.year or 'Unknown'}

Candidate matches:
{candidates_text}

Which option is the closest match to the vehicle description? 
Consider the specific details like fuel type, drivetrain, body style, and trim level.
Respond with only the CVEGS code of the best match.
"""
        
        try:
            # Call LLM for disambiguation
            response = await self.llm_extractor.call_openai(llm_prompt, max_tokens=50)
            
            # Extract CVEGS code from response
            response_text = response.strip()
            
            # Try to find matching CVEGS code in tied candidates
            for _, row in tied_candidates.iterrows():
                if str(row['cvegs_code']) in response_text:
                    return str(row['cvegs_code'])
            
            # Fallback to first candidate if no clear match
            return str(tied_candidates.iloc[0]['cvegs_code'])
            
        except Exception as e:
            logger.error("LLM tie-breaker failed", error=str(e))
            return str(tied_candidates.iloc[0]['cvegs_code'])
    
    def _create_no_match_result(self, 
                              vehicle_input: VehicleInput,
                              attributes: VehicleAttributes,
                              start_time: float) -> MatchResult:
        """Create result for when no match is found."""
        processing_time = (time.time() - start_time) * 1000
        
        return MatchResult(
            cvegs_code="NO_MATCH",
            confidence_score=0.0,
            confidence_level="very_low",
            matched_brand="",
            matched_model="",
            matched_year=None,
            matched_description="No match found",
            extracted_attributes=attributes,
            processing_time_ms=processing_time,
            candidates_evaluated=0,
            match_method="no_match",
            warnings=["No matching vehicle found in dataset"]
        )
    
    def _create_error_result(self, 
                           vehicle_input: VehicleInput,
                           error_message: str,
                           processing_time: float) -> MatchResult:
        """Create result for when an error occurs."""
        return MatchResult(
            cvegs_code="ERROR",
            confidence_score=0.0,
            confidence_level="very_low",
            matched_brand="",
            matched_model="",
            matched_year=None,
            matched_description="Error occurred during matching",
            extracted_attributes=VehicleAttributes(),
            processing_time_ms=processing_time,
            candidates_evaluated=0,
            match_method="error",
            warnings=[f"Error: {error_message}"]
        )
