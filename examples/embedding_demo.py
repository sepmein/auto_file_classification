"""
嵌入模块演示脚本
展示如何使用嵌入生成器处理文档
"""

import sys
import os
from pathlib import Path
import logging
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ods.embeddings.embedder import Embedder
from ods.embeddings.text_processor import TextProcessor
from ods.embeddings.models import EmbeddingModelFactory


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config():
    """加载配置"""
    config_path = project_root / "config" / "rules.yaml"
    
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return None


def demo_text_processor():
    """演示文本处理器"""
    print("\n=== 文本处理器演示 ===")
    
    config = {
        'max_chunk_size': 200,
        'overlap_size': 50,
        'min_chunk_size': 100
    }
    
    processor = TextProcessor(config)
    
    # 测试文本
    sample_text = """
    这是一个关于人工智能和机器学习的文档。人工智能（AI）是计算机科学的一个分支，
    它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    机器学习是人工智能的一个重要分支，它使计算机能够在没有明确编程的情况下学习和改进。
    
    深度学习是机器学习的一个子集，它使用多层神经网络来模拟人脑的工作方式。
    自然语言处理（NLP）是人工智能的另一个重要领域，它使计算机能够理解、
    解释和生成人类语言。
    
    这些技术正在改变我们的世界，从自动驾驶汽车到智能助手，从医疗诊断到金融分析，
    人工智能的应用无处不在。
    """
    
    print(f"原始文本长度: {len(sample_text)} 字符")
    
    # 清理文本
    cleaned_text = processor.clean_text(sample_text)
    print(f"清理后文本长度: {len(cleaned_text)} 字符")
    
    # 分块
    chunks = processor.split_into_chunks(cleaned_text)
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块 {i+1}: {len(chunk)} 字符")
    
    # 生成摘要
    summary = processor.generate_summary(cleaned_text, max_length=100)
    print(f"摘要: {summary}")
    
    # 提取关键词
    keywords = processor.extract_keywords(cleaned_text, top_k=8)
    print(f"关键词: {', '.join(keywords)}")
    
    # 文本统计
    stats = processor.get_text_statistics(cleaned_text)
    print(f"文本统计: {stats}")


def demo_embedding_models():
    """演示嵌入模型"""
    print("\n=== 嵌入模型演示 ===")
    
    # 显示默认配置
    default_configs = EmbeddingModelFactory.get_default_configs()
    print("默认模型配置:")
    for name, config in default_configs.items():
        print(f"  {name}:")
        for key, value in config.items():
            print(f"    {key}: {value}")
    
    # 测试本地模型配置（不实际加载模型）
    print("\n本地模型配置示例:")
    local_config = {
        'type': 'local',
        'model_name': 'BAAI/bge-m3',
        'device': 'cpu',
        'max_length': 8192
    }
    print(f"  {local_config}")
    
    # 测试API模型配置
    print("\nAPI模型配置示例:")
    api_config = {
        'type': 'api',
        'provider': 'openai',
        'model_name': 'text-embedding-ada-002',
        'api_key': 'your-api-key-here'
    }
    print(f"  {api_config}")


def demo_embedder():
    """演示嵌入生成器"""
    print("\n=== 嵌入生成器演示 ===")
    
    # 配置（使用模拟模型避免实际下载）
    config = {
        'embedding': {
            'type': 'local',
            'model_name': 'BAAI/bge-m3',
            'dimension': 1024,
            'max_length': 8192
        },
        'text_processing': {
            'max_chunk_size': 1000,
            'overlap_size': 100,
            'min_chunk_size': 100
        },
        'batch_size': 16,
        'max_workers': 2,
        'chunk_strategy': 'smart',
        'fallback_strategy': 'retry'
    }
    
    print("嵌入生成器配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # 注意：这里不实际创建Embedder实例，因为需要真实的模型
    print("\n注意: 实际使用需要安装相应的模型依赖")
    print("可以通过以下方式安装:")
    print("  pip install sentence-transformers torch")
    print("  或者使用API模型: pip install openai")


def demo_workflow_integration():
    """演示工作流集成"""
    print("\n=== 工作流集成演示 ===")
    
    print("嵌入模块已集成到LangGraph工作流中:")
    print("  1. parse_document -> 解析文档")
    print("  2. generate_embedding -> 生成嵌入向量")
    print("  3. classify_document -> 分类文档")
    print("  4. apply_rules -> 应用规则")
    print("  5. move_file -> 移动文件")
    print("  6. update_index -> 更新索引")
    
    print("\n嵌入节点的主要功能:")
    print("  - 文本预处理和清理")
    print("  - 长文本智能分块")
    print("  - 向量嵌入生成")
    print("  - 摘要和关键词提取")
    print("  - 批量处理支持")
    print("  - 错误处理和重试机制")


def main():
    """主函数"""
    print("基于LLM和向量数据库的自动文档分类系统")
    print("嵌入生成模块演示")
    print("=" * 50)
    
    setup_logging()
    
    # 加载配置
    config = load_config()
    if config:
        print(f"配置文件加载成功: {len(config)} 个配置项")
    else:
        print("使用默认配置")
    
    try:
        # 演示各个组件
        demo_text_processor()
        demo_embedding_models()
        demo_embedder()
        demo_workflow_integration()
        
        print("\n=== 演示完成 ===")
        print("\n下一步:")
        print("1. 安装必要的依赖包")
        print("2. 配置嵌入模型参数")
        print("3. 运行测试验证功能")
        print("4. 集成到实际工作流中")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        logging.error(f"演示错误: {e}", exc_info=True)


if __name__ == "__main__":
    main()
