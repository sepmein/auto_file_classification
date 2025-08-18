import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import json

from ods.storage.index_updater import IndexUpdater


class TestIndexUpdater:
    """索引更新器测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.config = {
            'database': {
                'sqlite_path': str(Path(self.temp_dir) / 'test_audit.db'),
                'audit_table': 'file_operations',
                'status_table': 'file_status'
            },
            'vector_store': {
                'chroma_path': str(Path(self.temp_dir) / 'chroma_db'),
                'collection_name': 'test_documents'
            },
            'llama_index': {
                'enable': False,  # 禁用LlamaIndex以避免复杂依赖
                'index_path': str(Path(self.temp_dir) / 'llama_index')
            },
            'classification': {
                'review_threshold': 0.6
            }
        }
        
        self.index_updater = IndexUpdater(self.config)

    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_database(self):
        """测试数据库初始化"""
        # 检查数据库文件是否创建
        db_path = Path(self.config['database']['sqlite_path'])
        assert db_path.exists()
        
        # 检查表是否创建
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'file_operations' in tables
            assert 'file_status' in tables

    def test_update_indexes_success(self):
        """测试成功的索引更新"""
        move_result = {
            'moved': True,
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf',
            'link_creations': []
        }
        
        document_data = {
            'text_content': '这是一个测试文档的内容',
            'summary': '测试文档摘要',
            'embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
            'metadata': {
                'file_type': 'pdf',
                'file_size': 1024000,
                'author': '测试用户'
            }
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作', '项目A'],
            'rules_applied': ['rule1', 'rule2']
        }
        
        result = self.index_updater.update_indexes(
            move_result, document_data, classification_result, 1.5
        )
        
        assert result['success'] is True
        assert 'operation_id' in result
        assert 'results' in result
        
        # 检查各个子操作的结果
        results = result['results']
        assert results['vector_update']['success'] is True
        assert results['audit_log']['success'] is True
        assert results['status_update']['success'] is True

    def test_update_indexes_file_not_moved(self):
        """测试文件未移动的情况"""
        move_result = {
            'moved': False,
            'original_path': '/test/document.pdf',
            'error_message': '权限不足'
        }
        
        document_data = {
            'text_content': '测试内容',
            'embedding': [0.1, 0.2, 0.3]
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        result = self.index_updater.update_indexes(
            move_result, document_data, classification_result, 1.0
        )
        
        assert result['success'] is False
        results = result['results']
        assert results['vector_update']['success'] is False
        assert results['vector_update']['reason'] == 'file_not_moved'

    def test_log_audit_record(self):
        """测试审计日志记录"""
        operation_id = "test-operation-123"
        move_result = {
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {
            'text_content': '测试内容'
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作', '项目A'],
            'rules_applied': ['rule1']
        }
        
        result = self.index_updater._log_audit_record(
            operation_id, move_result, document_data, classification_result, 1.5
        )
        
        assert result['success'] is True
        assert result['operation_id'] == operation_id
        
        # 验证数据库中的记录
        with sqlite3.connect(self.config['database']['sqlite_path']) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM file_operations WHERE id = ?", 
                (operation_id,)
            )
            row = cursor.fetchone()
            
            assert row is not None
            assert row[1] == '/test/document.pdf'  # file_path
            assert row[6] == '工作'  # category
            assert row[7] == '["工作", "项目A"]'  # tags

    def test_update_file_status(self):
        """测试文件状态更新"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / 'test_file.txt'
        test_file.write_text('test content')
        
        move_result = {
            'primary_target_path': str(test_file)
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        result = self.index_updater._update_file_status(move_result, classification_result)
        
        assert result['success'] is True
        
        # 验证数据库中的状态记录
        with sqlite3.connect(self.config['database']['sqlite_path']) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM file_status WHERE file_path = ?", 
                (str(test_file),)
            )
            row = cursor.fetchone()
            
            assert row is not None
            assert row[4] == '工作'  # category
            assert row[5] == '["工作"]'  # tags
            assert row[6] == 'classified'  # status

    def test_get_audit_records(self):
        """测试审计记录查询"""
        # 先插入一些测试记录
        operation_id = "test-operation-456"
        move_result = {
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {'text_content': '测试内容'}
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        self.index_updater._log_audit_record(
            operation_id, move_result, document_data, classification_result, 1.0
        )
        
        # 查询记录
        records = self.index_updater.get_audit_records()
        assert len(records) >= 1
        
        # 按文件路径查询
        records = self.index_updater.get_audit_records(file_path='/test/document.pdf')
        assert len(records) >= 1
        assert records[0]['file_path'] == '/test/document.pdf'
        
        # 按类别查询
        records = self.index_updater.get_audit_records(category='工作')
        assert len(records) >= 1
        assert records[0]['category'] == '工作'

    def test_get_file_status(self):
        """测试文件状态查询"""
        # 创建测试文件并更新状态
        test_file = Path(self.temp_dir) / 'test_file.txt'
        test_file.write_text('test content')
        
        move_result = {'primary_target_path': str(test_file)}
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        self.index_updater._update_file_status(move_result, classification_result)
        
        # 查询状态
        status = self.index_updater.get_file_status(str(test_file))
        assert status is not None
        assert status['category'] == '工作'
        assert status['status'] == 'classified'

    def test_get_files_needing_review(self):
        """测试获取需要审核的文件"""
        # 创建测试文件并更新状态（低置信度）
        test_file = Path(self.temp_dir) / 'test_file.txt'
        test_file.write_text('test content')
        
        move_result = {'primary_target_path': str(test_file)}
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.5,  # 低于审核阈值
            'tags': ['工作']
        }
        
        self.index_updater._update_file_status(move_result, classification_result)
        
        # 查询需要审核的文件
        files_needing_review = self.index_updater.get_files_needing_review()
        assert len(files_needing_review) >= 1
        assert files_needing_review[0]['file_path'] == str(test_file)

    def test_get_statistics(self):
        """测试统计信息获取"""
        # 先创建一些测试数据
        for i in range(3):
            operation_id = f"test-operation-{i}"
            move_result = {
                'moved': True,
                'original_path': f'/test/document{i}.pdf',
                'primary_target_path': f'/test/dst/category/document{i}.pdf'
            }
            
            document_data = {'text_content': f'测试内容{i}'}
            classification_result = {
                'primary_category': '工作' if i % 2 == 0 else '个人',
                'confidence_score': 0.9,
                'tags': ['工作' if i % 2 == 0 else '个人']
            }
            
            self.index_updater.update_indexes(
                move_result, document_data, classification_result, 1.0
            )
        
        # 获取统计信息
        stats = self.index_updater.get_statistics()
        
        assert 'total_operations' in stats
        assert 'successful_operations' in stats
        assert 'success_rate' in stats
        assert 'total_files' in stats
        assert 'category_distribution' in stats
        
        assert stats['total_operations'] >= 3
        assert stats['success_rate'] > 0

    def test_rollback_operation(self):
        """测试操作回滚"""
        # 先创建一个操作记录
        operation_id = "test-rollback-operation"
        move_result = {
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {'text_content': '测试内容'}
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        self.index_updater._log_audit_record(
            operation_id, move_result, document_data, classification_result, 1.0
        )
        
        # 执行回滚
        result = self.index_updater.rollback_operation(operation_id)
        
        assert result['success'] is True
        assert result['operation_id'] == operation_id

    def test_rollback_nonexistent_operation(self):
        """测试回滚不存在的操作"""
        result = self.index_updater.rollback_operation("nonexistent-operation")
        
        assert result['success'] is False
        assert result['reason'] == 'operation_not_found'

    @patch('chromadb.PersistentClient')
    def test_vector_store_update(self, mock_chroma_client):
        """测试向量库更新"""
        # Mock ChromaDB
        mock_collection = Mock()
        mock_chroma_client.return_value.get_collection.return_value = mock_collection
        
        move_result = {
            'moved': True,
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {
            'text_content': '测试内容',
            'embedding': [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        result = self.index_updater._update_vector_store(
            move_result, document_data, classification_result
        )
        
        assert result['success'] is True
        mock_collection.add.assert_called_once()

    def test_vector_store_update_no_embedding(self):
        """测试向量库更新（无嵌入向量）"""
        move_result = {
            'moved': True,
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {
            'text_content': '测试内容'
            # 没有embedding
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        result = self.index_updater._update_vector_store(
            move_result, document_data, classification_result
        )
        
        assert result['success'] is False
        assert result['reason'] == 'no_embedding'
