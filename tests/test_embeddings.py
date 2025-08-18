"""
嵌入模块测试
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from ods.embeddings.embedder import Embedder
from ods.embeddings.models import LocalEmbeddingModel, APIEmbeddingModel, EmbeddingModelFactory
from ods.embeddings.text_processor import TextProcessor


class TestTextProcessor:
    """文本处理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'max_chunk_size': 100,
            'overlap_size': 20,
            'min_chunk_size': 50
        }
        self.processor = TextProcessor(self.config)
    
    def test_clean_text(self):
        """测试文本清理"""
        text = "  这是一个测试文本  \n\n  包含多余空白  "
        cleaned = self.processor.clean_text(text)
        assert "这是一个测试文本" in cleaned
        assert cleaned.count("  ") == 0
    
    def test_split_into_chunks(self):
        """测试文本分块"""
        text = "第一句。第二句。第三句。第四句。第五句。"
        chunks = self.processor.split_into_chunks(text, chunk_size=20)
        assert len(chunks) > 1
        assert all(len(chunk) <= 20 for chunk in chunks)
    
    def test_generate_summary(self):
        """测试摘要生成"""
        text = "第一句。第二句。第三句。第四句。第五句。"
        summary = self.processor.generate_summary(text, max_length=10)
        assert len(summary) <= 10
        assert "第一句" in summary
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        text = "这是一个关于机器学习的文档，包含深度学习和自然语言处理的内容。"
        keywords = self.processor.extract_keywords(text, top_k=5)
        assert len(keywords) <= 5
        assert all(isinstance(k, str) for k in keywords)


class TestEmbeddingModels:
    """嵌入模型测试"""
    
    def test_local_model_config(self):
        """测试本地模型配置"""
        config = {
            'model_name': 'BAAI/bge-m3',
            'dimension': 1024,
            'max_length': 8192
        }
        
        with patch('torch.cuda.is_available', return_value=False):
            with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                mock_model.get_sentence_embedding_dimension.return_value = 1024
                mock_transformer.return_value = mock_model
                
                model = LocalEmbeddingModel(config)
                assert model.dimension == 1024
                assert model.max_length == 8192
    
    def test_api_model_config(self):
        """测试API模型配置"""
        config = {
            'model_name': 'text-embedding-ada-002',
            'api_key': 'test_key',
            'provider': 'openai'
        }
        
        with patch('openai.OpenAI') as mock_client:
            model = APIEmbeddingModel(config)
            assert model.provider == 'openai'
            assert model.api_key == 'test_key'
    
    def test_model_factory(self):
        """测试模型工厂"""
        config = {'type': 'local', 'model_name': 'test-model'}
        
        with patch('torch.cuda.is_available', return_value=False):
            with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                mock_model.get_sentence_embedding_dimension.return_value = 768
                mock_transformer.return_value = mock_model
                
                model = EmbeddingModelFactory.create_model(config)
                assert isinstance(model, LocalEmbeddingModel)


class TestEmbedder:
    """嵌入生成器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'embedding': {
                'type': 'local',
                'model_name': 'BAAI/bge-m3',
                'dimension': 1024,
                'max_length': 8192
            },
            'text_processing': {
                'max_chunk_size': 1000,
                'overlap_size': 100
            },
            'batch_size': 32,
            'max_workers': 4,
            'chunk_strategy': 'smart',
            'fallback_strategy': 'retry'
        }
    
    @patch('ods.embeddings.models.LocalEmbeddingModel')
    def test_embedder_initialization(self, mock_model_class):
        """测试嵌入生成器初始化"""
        mock_model = Mock()
        mock_model.get_model_info.return_value = {'type': 'local', 'status': 'loaded'}
        mock_model_class.return_value = mock_model
        
        embedder = Embedder(self.config)
        assert embedder.chunk_strategy == 'smart'
        assert embedder.fallback_strategy == 'retry'
    
    @patch('ods.embeddings.models.LocalEmbeddingModel')
    def test_process_document(self, mock_model_class):
        """测试文档处理"""
        # 模拟嵌入模型
        mock_model = Mock()
        mock_model.encode_single.return_value = np.random.rand(1024)
        mock_model.get_model_info.return_value = {'type': 'local', 'status': 'loaded'}
        mock_model_class.return_value = mock_model
        
        embedder = Embedder(self.config)
        
        # 测试文档数据
        document_data = {
            'file_path': '/test/file.txt',
            'text_content': '这是一个测试文档',
            'metadata': {'size': 100}
        }
        
        result = embedder.process_document(document_data)
        
        assert result['status'] == 'success'
        assert 'embedding' in result
        assert result['embedding_dimension'] == 1024
        assert 'summary' in result
        assert 'keywords' in result
    
    @patch('ods.embeddings.models.LocalEmbeddingModel')
    def test_smart_chunking(self, mock_model_class):
        """测试智能分块"""
        mock_model = Mock()
        mock_model.max_length = 100
        mock_model.encode_single.return_value = np.random.rand(1024)
        mock_model.get_model_info.return_value = {'type': 'local', 'status': 'loaded'}
        mock_model_class.return_value = mock_model
        
        embedder = Embedder(self.config)
        
        # 长文本应该被分块
        long_text = "第一句。" * 50  # 超过100字符
        
        result = embedder._smart_chunk_text(long_text)
        assert len(result) > 1
        assert all(len(chunk) <= 100 for chunk in result)
    
    @patch('ods.embeddings.models.LocalEmbeddingModel')
    def test_batch_processing(self, mock_model_class):
        """测试批量处理"""
        mock_model = Mock()
        mock_model.encode_single.return_value = np.random.rand(1024)
        mock_model.get_model_info.return_value = {'type': 'local', 'status': 'loaded'}
        mock_model_class.return_value = mock_model
        
        embedder = Embedder(self.config)
        
        # 准备多个文档
        documents = [
            {
                'file_path': f'/test/file{i}.txt',
                'text_content': f'这是第{i}个测试文档',
                'metadata': {'index': i}
            }
            for i in range(3)
        ]
        
        results = embedder.process_batch(documents)
        
        assert len(results) == 3
        assert all(r['status'] == 'success' for r in results)


class TestEmbeddingIntegration:
    """嵌入模块集成测试"""
    
    def test_text_processing_pipeline(self):
        """测试文本处理流水线"""
        config = {
            'max_chunk_size': 200,
            'overlap_size': 50,
            'clean_text': True,
            'remove_stopwords': False,
            'lemmatize': False
        }
        
        processor = TextProcessor(config)
        
        # 测试文本
        text = "  这是一个关于机器学习的文档。\n\n它包含深度学习和自然语言处理的内容。  "
        
        # 清理文本
        cleaned = processor.clean_text(text)
        assert "机器学习" in cleaned
        
        # 分块
        chunks = processor.split_into_chunks(cleaned)
        assert len(chunks) >= 1
        
        # 生成摘要
        summary = processor.generate_summary(cleaned)
        assert len(summary) <= 200
        
        # 提取关键词
        keywords = processor.extract_keywords(cleaned)
        assert len(keywords) > 0
    
    def test_embedding_workflow(self):
        """测试嵌入工作流"""
        # 这个测试需要实际的模型，所以使用模拟
        pass


if __name__ == "__main__":
    pytest.main([__file__])
