import uuid
import sys
import pathlib

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "packages" / "ml" / "src"))

from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import Run, Row, Codify, Component, RunStatus
from app.ml.retrieve import VehicleRetriever
from app.ml.embed import get_embedder
from app.ml.normalize import normalize_text
from .rerank import rerank
from .policy import decision_for

# Default thresholds
T_HIGH = 0.90
T_LOW = 0.70

def build_label(brand: str = None, model: str = None, year: int = None, 
                body: str = None, use: str = None, description: str = None) -> str:
    """
    Build a normalized label for vehicle matching.
    
    Args:
        brand: Vehicle brand
        model: Vehicle model
        year: Manufacturing year
        body: Body type
        use: Intended use
        description: Description
        
    Returns:
        Normalized label string
    """
    parts = []
    
    if brand:
        parts.append(normalize_text(brand))
    if model:
        parts.append(normalize_text(model))
    if year:
        parts.append(str(year))
    if body:
        parts.append(normalize_text(body))
    if use:
        parts.append(normalize_text(use))
    if description:
        parts.append(normalize_text(description))
    
    return " ".join(parts).strip()

def top_k(brand: str = "", model: str = "", year: int = None, 
          body: str = None, use: str = None, description: str = None,
          k: int = 25) -> list:
    """
    Get top-k similar vehicles using semantic search.
    
    Args:
        brand: Vehicle brand
        model: Vehicle model
        year: Manufacturing year
        body: Body type
        use: Intended use
        description: Description
        k: Number of results to return
        
    Returns:
        List of (cvegs, score, label) tuples
    """
    # Initialize retriever
    embedder = get_embedder()
    retriever = VehicleRetriever(engine, embedder)
    
    # Build query
    query_parts = []
    if brand:
        query_parts.append(brand)
    if model:
        query_parts.append(model)
    if year:
        query_parts.append(str(year))
    if body:
        query_parts.append(body)
    if use:
        query_parts.append(use)
    if description:
        query_parts.append(description)
    
    query = " ".join(query_parts).strip()
    
    if not query:
        return []
    
    # Search with fallback
    results, strategy = retriever.search_with_fallback(
        query=query,
        brand=brand if brand else None,
        model=model if model else None,
        year=year,
        body=body if body else None,
        limit=k
    )
    
    # Convert to expected format
    candidates = []
    for result in results:
        cvegs = result.get("cvegs", "")
        score = result.get("similarity", 0.0)
        
        # Build label from result
        label = build_label(
            brand=result.get("brand"),
            model=result.get("model"),
            year=result.get("year"),
            body=result.get("body"),
            use=result.get("use"),
            description=result.get("description")
        )
        
        candidates.append((cvegs, score, label))
    
    return candidates

def process_run(run_id: str):
    """
    Process a codification run by finding CVEGS matches for all rows.
    
    Args:
        run_id: ID of the run to process
    """
    with Session(engine) as s:
        run = s.get(Run, run_id)
        assert run and run.component == Component.CODIFY, f"Invalid run {run_id} for CODIFY component"
        
        # Get all rows for this run
        rows = (
            s.query(Row)
             .filter(Row.run_id == run_id)
             .order_by(Row.row_idx)
             .all()
        )
        
        total = 0
        auto = 0
        review = 0
        nomatch = 0
        
        for r in rows:
            canon = r.transformed or {}   # expects brand/model/year/body/use/description
            
            # Build label for matching
            label = build_label(
                canon.get("brand"), canon.get("model"),
                canon.get("year"),  canon.get("body"),
                canon.get("use"),   canon.get("description"),
            )
            
            # Get candidates using semantic search
            cands = top_k(
                canon.get("brand", ""), canon.get("model", ""),
                canon.get("year"), canon.get("body"), canon.get("use"), 
                canon.get("description", ""),
                k=25
            )
            
            # Rerank candidates
            ranked = rerank(label, cands)
            
            if ranked:
                best_cvegs, best_score, _ = ranked[0]
                dec = decision_for(best_score, T_HIGH, T_LOW)
            else:
                best_cvegs, best_score, dec = None, 0.0, "no_match"

            # Store codification result
            s.add(Codify(
                run_id=run_id, 
                row_idx=r.row_idx,
                suggested_cvegs=best_cvegs,
                confidence=best_score,
                candidates=[{
                    "cvegs": c, 
                    "score": float(s), 
                    "label": lab
                } for c, s, lab in ranked],
                decision=dec,
            ))

            # Update counters
            total += 1
            auto   += (dec == "auto_accept")
            review += (dec == "needs_review")
            nomatch += (dec == "no_match")

        # Update run status and metrics
        run.status = RunStatus.SUCCESS
        run.metrics = {
            "rows_total": total,
            "auto_accept": auto,
            "needs_review": review,
            "no_match": nomatch,
            "t_high": T_HIGH, 
            "t_low": T_LOW
        }
        s.commit()

        print(f"Codification completed for run {run_id}")
        print(f"Total rows: {total}")
        print(f"Auto accept: {auto} ({auto/total*100:.1f}%)")
        print(f"Needs review: {review} ({review/total*100:.1f}%)")
        print(f"No match: {nomatch} ({nomatch/total*100:.1f}%)")