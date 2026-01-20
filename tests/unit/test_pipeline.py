"""
Unit tests for the pipeline module.
"""

import pytest
from pathlib import Path


class TestIngest:
    """Tests for pipeline/ingest.py"""
    
    def test_extract_text_from_pdf_mock(self, tmp_path):
        """Test PDF extraction with a mock file."""
        # This is a placeholder test
        # In a real test, we'd create a test PDF
        assert True
    
    def test_load_documents_missing_dir(self):
        """Test that missing directory raises error."""
        from backend.pipeline.ingest import load_documents
        
        with pytest.raises(FileNotFoundError):
            load_documents("nonexistent_directory")


class TestEmbeddings:
    """Tests for pipeline/embeddings.py"""
    
    @pytest.mark.skip(reason="Requires Qdrant connection")
    def test_embed_text_returns_vector(self):
        """Test that embed_text returns a vector of correct dimension."""
        from backend.pipeline.embeddings import EmbeddingService
        
        service = EmbeddingService()
        vector = service.embed_text("test query")
        
        assert isinstance(vector, list)
        assert len(vector) == 1024  # BGE-M3 dimension


class TestGraphBuilder:
    """Tests for pipeline/graph_builder.py"""
    
    @pytest.mark.skip(reason="Requires Neo4j connection")
    def test_create_case_node(self):
        """Test case node creation."""
        from backend.pipeline.graph_builder import GraphBuilder
        
        builder = GraphBuilder()
        builder.create_case_node(
            case_id="test_1",
            name="Test Case",
            citation="2024 SCC 1",
            date="2024-01-01",
            court="Supreme Court",
        )
        builder.close()
