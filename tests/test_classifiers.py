"""
分类器模块测试
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from ods.classifiers.classifier import DocumentClassifier
from ods.classifiers.retrieval_agent import RetrievalAgent
from ods.classifiers.llm_classifier import LLMClassifier
from ods.classifiers.rule_checker import RuleChecker


class TestRetrievalAgent:
    """检索代理测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'database': {
                'vector_db_path': '.ods/test_vector_db'
            },
            'collection_name': 'test_documents',
            'top_k': 5,
            'similarity_threshold': 0.7
        }
        
        # 模拟ChromaDB
        with patch('ods.classifiers.retrieval_agent.chromadb') as mock_chroma:
            with patch('ods.classifiers.retrieval_agent.Path') as mock_path:
                mock_path.return_value.mkdir.return_value = None
                mock_client = Mock()
                mock_collection = Mock()
                mock_chroma.PersistentClient.return_value = mock_client
                mock_client.get_collection.return_value = mock_collection
                mock_client.create_collection.return_value = mock_collection
                
                self.retrieval_agent = RetrievalAgent(self.config)
                self.mock_collection = mock_collection
    
    def test_add_document(self):
        """测试添加文档"""
        # 模拟数据
        doc_id = "test_doc_1"
        embedding = np.random.rand(1024)
        metadata = {"category": "工作", "file_type": ".pdf"}
        text_chunk = "这是一个测试文档"
        
        # 模拟成功添加
        self.mock_collection.add.return_value = None
        
        result = self.retrieval_agent.add_document(doc_id, embedding, metadata, text_chunk)
        
        assert result is True
        self.mock_collection.add.assert_called_once()
    
    def test_search_similar_documents(self):
        """测试搜索相似文档"""
        # 模拟搜索结果
        mock_results = {
            'ids': [['doc1', 'doc2']],
            'metadatas': [{'doc1': {'category': '工作'}, 'doc2': {'category': '个人'}}],
            'distances': [[0.1, 0.3]],
            'documents': [['text1', 'text2']]
        }
        self.mock_collection.query.return_value = mock_results
        
        query_embedding = np.random.rand(1024)
        results = self.retrieval_agent.search_similar_documents(query_embedding, top_k=2)
        
        assert len(results) == 2
        assert results[0]['doc_id'] == 'doc1'
        assert results[0]['similarity_score'] == 0.9  # 1 - 0.1
    
    def test_get_category_examples(self):
        """测试获取类别示例"""
        # 模拟类别示例
        mock_results = {
            'ids': ['doc1', 'doc2'],
            'metadatas': [{'category': '工作'}, {'category': '工作'}],
            'text_chunk': ['示例1', '示例2']
        }
        self.mock_collection.get.return_value = mock_results
        
        examples = self.retrieval_agent.get_category_examples('工作', top_k=2)
        
        assert len(examples) == 2
        assert examples[0]['doc_id'] == 'doc1'
        assert examples[0]['metadata']['category'] == '工作'


class TestLLMClassifier:
    """LLM分类器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'test_key',
                'temperature': 0.1,
                'max_tokens': 1000
            },
            'classification': {
                'categories': ['工作', '个人', '财务', '其他'],
                'confidence_threshold': 0.8,
                'review_threshold': 0.6,
                'max_tags': 3
            }
        }
        
        # 模拟检索代理
        with patch('ods.classifiers.llm_classifier.RetrievalAgent') as mock_retrieval:
            mock_retrieval.return_value = Mock()
            self.llm_classifier = LLMClassifier(self.config)
    
    @patch('ods.classifiers.llm_classifier.OpenAI')
    def test_setup_llm_client(self, mock_openai):
        """测试LLM客户端设置"""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # 重新初始化以测试客户端设置
        config = self.config.copy()
        config['llm']['api_key'] = 'valid_key'
        
        with patch('ods.classifiers.llm_classifier.RetrievalAgent'):
            classifier = LLMClassifier(config)
            assert classifier.llm_client is not None
    
    def test_parse_llm_response(self):
        """测试LLM响应解析"""
        # 测试JSON响应
        json_response = '{"primary_category": "工作", "confidence_score": 0.9}'
        result = self.llm_classifier._parse_llm_response(json_response)
        
        assert result['primary_category'] == '工作'
        assert result['confidence_score'] == 0.9
        
        # 测试文本响应
        text_response = '这个文档属于工作类别，置信度: 0.8'
        result = self.llm_classifier._parse_llm_response(text_response)
        
        assert result['primary_category'] == '工作'
        assert result['confidence_score'] == 0.8
    
    def test_fallback_classification(self):
        """测试备用分类"""
        document_data = {
            'file_path': '/test/document.pdf',
            'summary': '测试文档内容'
        }
        
        result = self.llm_classifier._fallback_classification(document_data)
        
        assert result['primary_category'] == '文档'
        assert result['confidence_score'] == 0.3
        assert result['needs_review'] is True


class TestRuleChecker:
    """规则检查器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'rules': {
                'rules_file': 'config/test_rules.yaml',
                'enable_rules': True,
                'strict_mode': False
            }
        }
        
        # 模拟YAML文件
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load') as mock_yaml:
                mock_yaml.return_value = {}
                self.rule_checker = RuleChecker(self.config)
    
    def test_file_extension_rules(self):
        """测试文件扩展名规则"""
        # 添加规则
        self.rule_checker.add_rule('file_extension', '.pdf', '文档', 1)
        
        document_data = {'file_path': '/test/document.pdf'}
        classification_result = {'primary_category': '其他', 'confidence_score': 0.5}
        
        result = self.rule_checker.apply_rules(classification_result, document_data)
        
        assert result['primary_category'] == '文档'
        assert result['confidence_score'] == 0.7  # 0.5 + 0.2
        assert 'rule_applied' in result
    
    def test_file_name_rules(self):
        """测试文件名规则"""
        # 添加规则
        self.rule_checker.add_rule('file_name', '发票', '财务', 2)
        
        document_data = {'file_path': '/test/发票2024.pdf'}
        classification_result = {'primary_category': '其他', 'confidence_score': 0.5}
        
        result = self.rule_checker.apply_rules(classification_result, document_data)
        
        assert result['primary_category'] == '财务'
        assert result['confidence_score'] == 0.7
    
    def test_content_keywords_rules(self):
        """测试内容关键词规则"""
        # 添加规则
        self.rule_checker.add_rule('content_keywords', '合同', '工作', 3)
        
        document_data = {
            'file_path': '/test/document.pdf',
            'text_content': '这是一份合同文档',
            'summary': '合同内容摘要'
        }
        classification_result = {'primary_category': '其他', 'confidence_score': 0.5}
        
        result = self.rule_checker.apply_rules(classification_result, document_data)

        assert result['primary_category'] == '工作'
        assert result['confidence_score'] == 0.7

    def test_simple_rules_add_tag(self):
        """测试简单规则添加标签"""
        config = {
            'rules': {
                'enable_rules': False,
                'simple_rules': [
                    {'if_filename': '发票', 'add_tag': '发票'}
                ]
            }
        }
        rule_checker = RuleChecker(config)
        classification_result = {'primary_category': '其他', 'confidence_score': 0.5}
        document_data = {'file_path': '/test/发票123.pdf'}
        result = rule_checker.apply_rules(classification_result, document_data)
        assert '发票' in result['tags']

    def test_simple_rules_require_review(self):
        """测试标签组合触发审核"""
        config = {
            'rules': {
                'enable_rules': False,
                'simple_rules': [
                    {'if_tag_combo': ['保密', '财务'], 'action': 'require_review'}
                ]
            }
        }
        rule_checker = RuleChecker(config)
        classification_result = {
            'primary_category': '财务',
            'secondary_categories': ['保密'],
            'confidence_score': 0.9
        }
        document_data = {'file_path': '/test/document.pdf'}
        result = rule_checker.apply_rules(classification_result, document_data)
        assert result['needs_review'] is True


class TestDocumentClassifier:
    """文档分类器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'classification': {
                'categories': ['工作', '个人', '财务', '其他'],
                'confidence_threshold': 0.8,
                'review_threshold': 0.6,
                'max_tags': 3
            }
        }
        
        # 模拟所有组件
        with patch('ods.classifiers.classifier.RetrievalAgent') as mock_retrieval:
            with patch('ods.classifiers.classifier.LLMClassifier') as mock_llm:
                with patch('ods.classifiers.classifier.RuleChecker') as mock_rules:
                    mock_retrieval.return_value = Mock()
                    mock_llm.return_value = Mock()
                    mock_rules.return_value = Mock()
                    
                    self.classifier = DocumentClassifier(self.config)
    
    def test_classify_document(self):
        """测试文档分类"""
        # 模拟LLM分类结果
        llm_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'needs_review': False
        }
        self.classifier.llm_classifier.classify_document.return_value = llm_result
        
        # 模拟规则检查结果
        rule_result = llm_result.copy()
        self.classifier.rule_checker.apply_rules.return_value = rule_result
        
        # 模拟向量数据库添加
        self.classifier.retrieval_agent.add_document.return_value = True
        
        document_data = {
            'file_path': '/test/document.pdf',
            'summary': '工作相关文档',
            'embedding': np.random.rand(1024),
            'metadata': {'size': 1024}
        }
        
        result = self.classifier.classify_document(document_data)
        
        assert result['primary_category'] == '工作'
        assert result['classification_method'] == 'llm_with_rules'
        assert 'total_processing_time' in result
    
    def test_batch_classify(self):
        """测试批量分类"""
        documents = [
            {'file_path': '/test/doc1.pdf', 'summary': '文档1'},
            {'file_path': '/test/doc2.pdf', 'summary': '文档2'}
        ]
        
        # 模拟分类结果
        with patch.object(self.classifier, 'classify_document') as mock_classify:
            mock_classify.side_effect = [
                {'primary_category': '工作', 'confidence_score': 0.9},
                {'primary_category': '个人', 'confidence_score': 0.8}
            ]
            
            results = self.classifier.batch_classify(documents)
            
            assert len(results) == 2
            assert results[0]['batch_index'] == 0
            assert results[1]['batch_index'] == 1
    
    def test_get_classification_statistics(self):
        """测试获取分类统计"""
        # 模拟统计结果
        self.classifier.retrieval_agent.get_collection_stats.return_value = {
            'total_documents': 10,
            'categories': ['工作', '个人']
        }
        self.classifier.rule_checker.get_rules_summary.return_value = {
            'total_rules': 5,
            'enabled': True
        }
        
        stats = self.classifier.get_classification_statistics()
        
        assert 'vector_database' in stats
        assert 'rules' in stats
        assert 'categories' in stats
        assert stats['categories'] == ['工作', '个人', '财务', '其他']


class TestClassificationIntegration:
    """分类集成测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'test_key'
            },
            'classification': {
                'categories': ['工作', '个人', '财务', '其他'],
                'confidence_threshold': 0.8,
                'review_threshold': 0.6
            },
            'database': {
                'vector_db_path': '.ods/test_vector_db'
            }
        }
    
    @patch('ods.classifiers.retrieval_agent.chromadb')
    @patch('ods.classifiers.llm_classifier.OpenAI')
    def test_full_classification_pipeline(self, mock_openai, mock_chroma):
        """测试完整分类流水线"""
        # 模拟所有组件
        mock_chroma.PersistentClient.return_value = Mock()
        mock_openai.return_value = Mock()
        
        # 创建分类器
        classifier = DocumentClassifier(self.config)
        
        # 测试文档
        document_data = {
            'file_path': '/test/document.pdf',
            'summary': '这是一份关于项目管理的文档，包含项目计划、时间安排和资源分配等内容。',
            'embedding': np.random.rand(1024),
            'metadata': {'size': 2048}
        }
        
        # 执行分类
        result = classifier.classify_document(document_data)
        
        # 验证结果
        assert result is not None
        assert 'primary_category' in result
        assert 'confidence_score' in result
        assert 'needs_review' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
