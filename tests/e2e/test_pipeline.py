import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from libs.db.database import get_async_db_session
from libs.db.models import Case, Run, Row, CodifyResult, Export
from libs.storage.s3 import S3Client
from libs.mq.consumer import SQSPublisher

class TestPipeline:
    """End-to-end tests for the insurance data processing pipeline"""
    
    @pytest.fixture
    async def sample_data(self):
        """Create sample Excel file for testing"""
        data = {
            'MARCA': ['TOYOTA', 'HONDA', 'NISSAN'],
            'MODELO': ['COROLLA', 'CIVIC', 'SENTRA'],
            'AÑO': [2020, 2019, 2021],
            'COBERTURA': ['TODO RIESGO', 'COLISION', 'RESPONSABILIDAD CIVIL']
        }
        df = pd.DataFrame(data)
        
        test_file = Path('test_sample.xlsx')
        df.to_excel(test_file, index=False)
        
        yield test_file
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_complete_pipeline(self, sample_data: Path):
        """Test complete pipeline: ingest -> extract -> codify -> transform -> export"""
        
        # 1. Upload file and create case
        case_id = await self._create_case(sample_data)
        assert case_id is not None
        
        # 2. Run extraction
        await self._run_extraction(case_id, sample_data)
        
        # 3. Verify extraction results
        rows = await self._get_case_rows(case_id)
        assert len(rows) == 3
        assert rows[0].vehicle_make == 'TOYOTA'
        
        # 4. Run codification
        run_id = await self._run_codification(case_id)
        assert run_id is not None
        
        # 5. Verify codification results
        codify_results = await self._get_codify_results(run_id)
        assert len(codify_results) == 3
        assert all(result.confidence > 0.7 for result in codify_results)
        
        # 6. Run transformation
        await self._run_transformation(run_id, "sample-broker")
        
        # 7. Run export
        export_id = await self._run_export(run_id)
        assert export_id is not None
        
        # 8. Verify export results
        export = await self._get_export(export_id)
        assert export.format == "Gcotiza"
        assert export.row_count == 3
        assert export.error_count == 0
    
    async def _create_case(self, file_path: Path) -> str:
        """Create a case by uploading file"""
        s3_client = S3Client()
        
        # Upload file to S3
        s3_key = f"test/{file_path.name}"
        await s3_client.upload_file(str(file_path), s3_key)
        
        # Create case in database
        async with get_async_db_session() as db:
            case = Case(
                filename=file_path.name,
                file_type="xlsx",
                file_size=file_path.stat().st_size,
                s3_key=s3_key,
                status="pending",
                user_id="test-user",
                broker_profile="sample-broker"
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)
            return str(case.id)
    
    async def _run_extraction(self, case_id: str, file_path: Path):
        """Trigger extraction job"""
        publisher = SQSPublisher()
        
        message = {
            "case_id": case_id,
            "file_key": f"test/{file_path.name}",
            "file_type": "xlsx"
        }
        
        await publisher.send_message("extractor", message)
        
        # Wait for processing (in real test, would poll for completion)
        await asyncio.sleep(5)
    
    async def _get_case_rows(self, case_id: str) -> list[Row]:
        """Get extracted rows for a case"""
        async with get_async_db_session() as db:
            result = await db.execute(
                "SELECT * FROM rows WHERE case_id = %s ORDER BY created_at",
                [case_id]
            )
            return result.fetchall()
    
    async def _run_codification(self, case_id: str) -> str:
        """Run codification and return run_id"""
        async with get_async_db_session() as db:
            # Create run
            run = Run(
                case_id=case_id,
                status="created",
                broker_profile="sample-broker"
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            
            # Get row IDs
            rows_result = await db.execute(
                "SELECT id FROM rows WHERE case_id = %s",
                [case_id]
            )
            row_ids = [row[0] for row in rows_result.fetchall()]
            
            # Send codification message
            publisher = SQSPublisher()
            message = {
                "run_id": str(run.id),
                "row_ids": row_ids
            }
            await publisher.send_message("codifier", message)
            
            # Wait for processing
            await asyncio.sleep(10)
            
            return str(run.id)
    
    async def _get_codify_results(self, run_id: str) -> list[CodifyResult]:
        """Get codification results"""
        async with get_async_db_session() as db:
            result = await db.execute(
                "SELECT * FROM codify_results WHERE run_id = %s",
                [run_id]
            )
            return result.fetchall()
    
    async def _run_transformation(self, run_id: str, profile: str):
        """Run transformation step"""
        publisher = SQSPublisher()
        
        message = {
            "run_id": run_id,
            "profile_name": profile
        }
        
        await publisher.send_message("transform", message)
        await asyncio.sleep(5)
    
    async def _run_export(self, run_id: str) -> str:
        """Run export step"""
        publisher = SQSPublisher()
        
        message = {
            "run_id": run_id,
            "format": "Gcotiza"
        }
        
        await publisher.send_message("exporter", message)
        await asyncio.sleep(10)
        
        # Get export record
        async with get_async_db_session() as db:
            result = await db.execute(
                "SELECT id FROM exports WHERE run_id = %s",
                [run_id]
            )
            return result.fetchone()[0]
    
    async def _get_export(self, export_id: str) -> Export:
        """Get export record"""
        async with get_async_db_session() as db:
            result = await db.execute(
                "SELECT * FROM exports WHERE id = %s",
                [export_id]
            )
            return result.fetchone()

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_malformed_excel_file(self):
        """Test handling of malformed Excel files"""
        # Create malformed file
        malformed_file = Path('malformed.xlsx')
        malformed_file.write_text("This is not an Excel file")
        
        try:
            case_id = await self._create_case_with_file(malformed_file)
            await self._run_extraction_expect_error(case_id)
        finally:
            malformed_file.unlink()
    
    @pytest.mark.asyncio
    async def test_missing_required_columns(self):
        """Test handling when required columns are missing"""
        # Create Excel with missing columns
        data = {'ONLY_ONE_COLUMN': ['value1', 'value2']}
        df = pd.DataFrame(data)
        
        test_file = Path('missing_columns.xlsx')
        df.to_excel(test_file, index=False)
        
        try:
            case_id = await self._create_case_with_file(test_file)
            await self._run_extraction_expect_warnings(case_id)
        finally:
            test_file.unlink()
    
    @pytest.mark.asyncio 
    async def test_low_confidence_codification(self):
        """Test handling of low-confidence codification results"""
        # Create data with unusual vehicle makes/models
        data = {
            'MARCA': ['UNKNOWN_MAKE', 'WEIRD_BRAND'],
            'MODELO': ['STRANGE_MODEL', 'UNUSUAL_CAR'],
            'AÑO': [2020, 2021],
            'COBERTURA': ['TODO RIESGO', 'COLISION']
        }
        df = pd.DataFrame(data)
        
        test_file = Path('low_confidence.xlsx')
        df.to_excel(test_file, index=False)
        
        try:
            case_id = await self._create_case_with_file(test_file)
            run_id = await self._run_full_pipeline(case_id)
            
            # Verify that low confidence results are flagged for review
            codify_results = await self._get_codify_results(run_id)
            assert any(result.needs_review for result in codify_results)
            
        finally:
            test_file.unlink()

class TestPerformance:
    """Performance tests for the pipeline"""
    
    @pytest.mark.asyncio
    async def test_large_file_processing(self):
        """Test processing large Excel files (1000+ rows)"""
        # Create large dataset
        data = {
            'MARCA': ['TOYOTA'] * 1000,
            'MODELO': ['COROLLA'] * 1000,
            'AÑO': [2020] * 1000,
            'COBERTURA': ['TODO RIESGO'] * 1000
        }
        df = pd.DataFrame(data)
        
        large_file = Path('large_test.xlsx')
        df.to_excel(large_file, index=False)
        
        try:
            import time
            start_time = time.time()
            
            case_id = await self._create_case_with_file(large_file)
            await self._run_full_pipeline(case_id)
            
            processing_time = time.time() - start_time
            
            # Should process 1000 rows in less than 60 seconds
            assert processing_time < 60
            
            # Verify all rows processed
            rows = await self._get_case_rows(case_id)
            assert len(rows) == 1000
            
        finally:
            large_file.unlink()
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing of multiple cases"""
        # Create multiple small files
        files = []
        case_ids = []
        
        try:
            for i in range(5):
                data = {
                    'MARCA': ['TOYOTA', 'HONDA'],
                    'MODELO': ['COROLLA', 'CIVIC'],
                    'AÑO': [2020, 2021],
                    'COBERTURA': ['TODO RIESGO', 'COLISION']
                }
                df = pd.DataFrame(data)
                
                file_path = Path(f'concurrent_test_{i}.xlsx')
                df.to_excel(file_path, index=False)
                files.append(file_path)
                
                case_id = await self._create_case_with_file(file_path)
                case_ids.append(case_id)
            
            # Process all concurrently
            tasks = []
            for case_id in case_ids:
                task = self._run_full_pipeline(case_id)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Verify all completed successfully
            for case_id in case_ids:
                rows = await self._get_case_rows(case_id)
                assert len(rows) == 2
                
        finally:
            for file_path in files:
                if file_path.exists():
                    file_path.unlink()