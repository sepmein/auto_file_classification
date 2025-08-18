#!/usr/bin/env python3
"""
索引更新器演示脚本

展示如何使用IndexUpdater模块进行：
- 索引更新
- 审计日志查询
- 文件状态管理
- 统计信息获取
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

from ods.storage.index_updater import IndexUpdater


def demo_basic_index_update():
    """演示基本的索引更新操作"""
    print("=== 基本索引更新演示 ===")
    
    # 创建临时配置
    temp_dir = tempfile.mkdtemp()
    config = {
        'database': {
            'sqlite_path': str(Path(temp_dir) / 'audit.db'),
            'audit_table': 'file_operations',
            'status_table': 'file_status'
        },
        'vector_store': {
            'chroma_path': str(Path(temp_dir) / 'chroma_db'),
            'collection_name': 'documents'
        },
        'llama_index': {
            'enable': False,  # 简化演示
            'index_path': str(Path(temp_dir) / 'llama_index')
        },
        'classification': {
            'review_threshold': 0.6
        }
    }
    
    try:
        # 初始化索引更新器
        index_updater = IndexUpdater(config)
        print("✓ 索引更新器初始化成功")
        
        # 模拟文件移动结果
        move_result = {
            'moved': True,
            'original_path': '/home/user/documents/report.pdf',
            'primary_target_path': '/home/user/OneDrive/分类/工作/2024/01/report.pdf',
            'link_creations': [
                {'path': '/home/user/OneDrive/分类/项目A/report.pdf', 'ok': True},
                {'path': '/home/user/OneDrive/分类/重要/report.pdf', 'ok': True}
            ]
        }
        
        # 模拟文档数据
        document_data = {
            'text_content': '这是一份关于项目进展的季度报告，包含了详细的财务分析和未来规划。',
            'summary': '项目季度报告',
            'embedding': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            'metadata': {
                'file_type': 'pdf',
                'file_size': 2048000,
                'author': '张三',
                'creation_date': '2024-01-15'
            }
        }
        
        # 模拟分类结果
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.92,
            'tags': ['工作', '项目A', '重要'],
            'rules_applied': ['keyword_rule', 'content_rule']
        }
        
        # 执行索引更新
        start_time = datetime.now()
        update_result = index_updater.update_indexes(
            move_result, document_data, classification_result, 2.5
        )
        
        print(f"✓ 索引更新完成")
        print(f"  操作ID: {update_result['operation_id']}")
        print(f"  成功状态: {update_result['success']}")
        print(f"  处理时间: {update_result['timestamp']}")
        
        # 显示详细结果
        results = update_result['results']
        print(f"  向量库更新: {results['vector_update']['success']}")
        print(f"  审计日志: {results['audit_log']['success']}")
        print(f"  状态更新: {results['status_update']['success']}")
        
    except Exception as e:
        print(f"✗ 索引更新失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_audit_log_query():
    """演示审计日志查询"""
    print("\n=== 审计日志查询演示 ===")
    
    temp_dir = tempfile.mkdtemp()
    config = {
        'database': {
            'sqlite_path': str(Path(temp_dir) / 'audit.db'),
            'audit_table': 'file_operations',
            'status_table': 'file_status'
        },
        'vector_store': {
            'chroma_path': str(Path(temp_dir) / 'chroma_db'),
            'collection_name': 'documents'
        },
        'llama_index': {
            'enable': False,
            'index_path': str(Path(temp_dir) / 'llama_index')
        },
        'classification': {
            'review_threshold': 0.6
        }
    }
    
    try:
        index_updater = IndexUpdater(config)
        
        # 创建一些测试记录
        test_files = [
            {
                'path': '/home/user/documents/report1.pdf',
                'category': '工作',
                'confidence': 0.9
            },
            {
                'path': '/home/user/documents/personal.pdf',
                'category': '个人',
                'confidence': 0.85
            },
            {
                'path': '/home/user/documents/invoice.pdf',
                'category': '财务',
                'confidence': 0.78
            }
        ]
        
        for i, file_info in enumerate(test_files):
            move_result = {
                'moved': True,
                'original_path': file_info['path'],
                'primary_target_path': f'/home/user/OneDrive/分类/{file_info["category"]}/file{i}.pdf'
            }
            
            document_data = {
                'text_content': f'这是{file_info["category"]}文档的内容',
                'embedding': [0.1 * (i + 1)] * 10
            }
            
            classification_result = {
                'primary_category': file_info['category'],
                'confidence_score': file_info['confidence'],
                'tags': [file_info['category']]
            }
            
            index_updater.update_indexes(
                move_result, document_data, classification_result, 1.0
            )
        
        print("✓ 测试记录创建完成")
        
        # 查询所有记录
        all_records = index_updater.get_audit_records(limit=10)
        print(f"✓ 查询到 {len(all_records)} 条记录")
        
        # 按类别查询
        work_records = index_updater.get_audit_records(category='工作')
        print(f"✓ 工作类别记录: {len(work_records)} 条")
        
        # 按文件路径查询
        specific_records = index_updater.get_audit_records(
            file_path='/home/user/documents/report1.pdf'
        )
        print(f"✓ 特定文件记录: {len(specific_records)} 条")
        
        # 显示最新记录详情
        if all_records:
            latest = all_records[0]
            print(f"  最新记录:")
            print(f"    文件: {latest['file_path']}")
            print(f"    类别: {latest['category']}")
            print(f"    置信度: {latest['confidence_score']}")
            print(f"    状态: {latest['status']}")
            print(f"    时间: {latest['created_at']}")
        
    except Exception as e:
        print(f"✗ 审计日志查询失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_file_status_management():
    """演示文件状态管理"""
    print("\n=== 文件状态管理演示 ===")
    
    temp_dir = tempfile.mkdtemp()
    config = {
        'database': {
            'sqlite_path': str(Path(temp_dir) / 'audit.db'),
            'audit_table': 'file_operations',
            'status_table': 'file_status'
        },
        'vector_store': {
            'chroma_path': str(Path(temp_dir) / 'chroma_db'),
            'collection_name': 'documents'
        },
        'llama_index': {
            'enable': False,
            'index_path': str(Path(temp_dir) / 'llama_index')
        },
        'classification': {
            'review_threshold': 0.6
        }
    }
    
    try:
        index_updater = IndexUpdater(config)
        
        # 创建测试文件
        test_file = Path(temp_dir) / 'test_document.txt'
        test_file.write_text('这是一个测试文档')
        
        # 更新文件状态
        move_result = {
            'primary_target_path': str(test_file)
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.75,
            'tags': ['工作', '测试']
        }
        
        index_updater._update_file_status(move_result, classification_result)
        print("✓ 文件状态更新完成")
        
        # 查询文件状态
        status = index_updater.get_file_status(str(test_file))
        if status:
            print(f"✓ 文件状态查询成功:")
            print(f"  路径: {status['file_path']}")
            print(f"  类别: {status['category']}")
            print(f"  标签: {status['tags']}")
            print(f"  状态: {status['status']}")
            print(f"  需要审核: {status['needs_review']}")
            print(f"  最后分类: {status['last_classified']}")
        
        # 测试低置信度文件（需要审核）
        low_confidence_file = Path(temp_dir) / 'uncertain_document.txt'
        low_confidence_file.write_text('不确定内容的文档')
        
        low_confidence_result = {
            'primary_category': '其他',
            'confidence_score': 0.45,  # 低于审核阈值
            'tags': ['其他']
        }
        
        index_updater._update_file_status(
            {'primary_target_path': str(low_confidence_file)},
            low_confidence_result
        )
        
        # 查询需要审核的文件
        files_needing_review = index_updater.get_files_needing_review()
        print(f"✓ 需要审核的文件: {len(files_needing_review)} 个")
        
        for file_info in files_needing_review:
            print(f"  - {file_info['file_path']} (置信度: {file_info.get('confidence_score', 'N/A')})")
        
    except Exception as e:
        print(f"✗ 文件状态管理失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_statistics():
    """演示统计信息获取"""
    print("\n=== 统计信息演示 ===")
    
    temp_dir = tempfile.mkdtemp()
    config = {
        'database': {
            'sqlite_path': str(Path(temp_dir) / 'audit.db'),
            'audit_table': 'file_operations',
            'status_table': 'file_status'
        },
        'vector_store': {
            'chroma_path': str(Path(temp_dir) / 'chroma_db'),
            'collection_name': 'documents'
        },
        'llama_index': {
            'enable': False,
            'index_path': str(Path(temp_dir) / 'llama_index')
        },
        'classification': {
            'review_threshold': 0.6
        }
    }
    
    try:
        index_updater = IndexUpdater(config)
        
        # 创建多样化的测试数据
        categories = ['工作', '个人', '财务', '其他']
        for i in range(10):
            category = categories[i % len(categories)]
            confidence = 0.6 + (i % 4) * 0.1  # 0.6-0.9
            
            move_result = {
                'moved': True,
                'original_path': f'/test/file{i}.pdf',
                'primary_target_path': f'/test/dst/{category}/file{i}.pdf'
            }
            
            document_data = {
                'text_content': f'这是{category}文档{i}的内容',
                'embedding': [0.1 * (i + 1)] * 10
            }
            
            classification_result = {
                'primary_category': category,
                'confidence_score': confidence,
                'tags': [category]
            }
            
            index_updater.update_indexes(
                move_result, document_data, classification_result, 1.0
            )
        
        print("✓ 测试数据创建完成")
        
        # 获取统计信息
        stats = index_updater.get_statistics()
        
        print("✓ 统计信息:")
        print(f"  总操作数: {stats['total_operations']}")
        print(f"  成功操作数: {stats['successful_operations']}")
        print(f"  成功率: {stats['success_rate']:.2%}")
        print(f"  总文件数: {stats['total_files']}")
        print(f"  需要审核的文件: {stats['files_needing_review']}")
        
        print("  分类分布:")
        for category, count in stats['category_distribution'].items():
            print(f"    {category}: {count} 个文件")
        
    except Exception as e:
        print(f"✗ 统计信息获取失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_rollback_operation():
    """演示操作回滚"""
    print("\n=== 操作回滚演示 ===")
    
    temp_dir = tempfile.mkdtemp()
    config = {
        'database': {
            'sqlite_path': str(Path(temp_dir) / 'audit.db'),
            'audit_table': 'file_operations',
            'status_table': 'file_status'
        },
        'vector_store': {
            'chroma_path': str(Path(temp_dir) / 'chroma_db'),
            'collection_name': 'documents'
        },
        'llama_index': {
            'enable': False,
            'index_path': str(Path(temp_dir) / 'llama_index')
        },
        'classification': {
            'review_threshold': 0.6
        }
    }
    
    try:
        index_updater = IndexUpdater(config)
        
        # 创建一个操作记录
        move_result = {
            'moved': True,
            'original_path': '/test/document.pdf',
            'primary_target_path': '/test/dst/category/document.pdf'
        }
        
        document_data = {
            'text_content': '需要回滚的文档',
            'embedding': [0.1, 0.2, 0.3]
        }
        
        classification_result = {
            'primary_category': '工作',
            'confidence_score': 0.9,
            'tags': ['工作']
        }
        
        update_result = index_updater.update_indexes(
            move_result, document_data, classification_result, 1.0
        )
        
        operation_id = update_result['operation_id']
        print(f"✓ 操作记录创建完成，ID: {operation_id}")
        
        # 执行回滚
        rollback_result = index_updater.rollback_operation(operation_id)
        
        print(f"✓ 回滚操作结果:")
        print(f"  成功: {rollback_result['success']}")
        print(f"  操作ID: {rollback_result['operation_id']}")
        print(f"  消息: {rollback_result.get('message', 'N/A')}")
        
        # 测试回滚不存在的操作
        fake_rollback = index_updater.rollback_operation("fake-operation-id")
        print(f"  假操作回滚: {fake_rollback['success']} ({fake_rollback['reason']})")
        
    except Exception as e:
        print(f"✗ 操作回滚失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主函数"""
    print("索引更新器演示程序")
    print("=" * 50)
    
    # 运行各个演示
    demo_basic_index_update()
    demo_audit_log_query()
    demo_file_status_management()
    demo_statistics()
    demo_rollback_operation()
    
    print("\n" + "=" * 50)
    print("演示完成！")


if __name__ == "__main__":
    main()
