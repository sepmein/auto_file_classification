"""
命令行界面

提供基础的命令行功能
"""

import click
import logging
from pathlib import Path
from typing import Optional

from .core.config import Config
from .core.workflow import DocumentClassificationWorkflow
from .parsers.document_parser import DocumentParser


def setup_logging(log_level: str = "INFO") -> None:
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@click.group()
@click.option('--config', '-c', help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.pass_context
def main(ctx, config: Optional[str], verbose: bool):
    """基于LLM和向量数据库的自动文档分类系统"""
    
    # 设置日志
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    # 加载配置
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config(config)
    
    if verbose:
        click.echo(f"配置文件: {ctx.obj['config'].config_path}")


@main.command()
@click.pass_context
def init(ctx):
    """初始化系统"""
    config = ctx.obj['config']
    
    click.echo("正在初始化系统...")
    
    # 创建必要的目录
    for directory in [config.system.temp_directory, Path(config.database.path).parent]:
        Path(directory).mkdir(parents=True, exist_ok=True)
        click.echo(f"创建目录: {directory}")
    
    # 保存配置
    config.save()
    click.echo(f"配置文件已保存: {config.config_path}")
    
    click.echo("系统初始化完成！")


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.pass_context
def parse(ctx, file_path: str):
    """解析单个文件（测试功能）"""
    config = ctx.obj['config']

    click.echo(f"正在解析文件: {file_path}")

    # 创建解析器
    parser = DocumentParser(config.get_config_dict())

    # 解析文件
    result = parser.parse(file_path)

    if result.success:
        click.echo(f"解析成功！")
        click.echo(f"解析器类型: {result.parser_type}")
        click.echo(f"文档标题: {result.content.title}")
        click.echo(f"文档字数: {result.content.word_count}")
        click.echo(f"文档摘要: {result.summary}")
    else:
        click.echo(f"解析失败: {result.error}", err=True)


@main.command()
@click.argument("source_directory", type=click.Path(exists=True), required=False)
@click.option("--dry-run", is_flag=True, help="仅模拟运行，不实际移动文件")
@click.option("--recursive", "-r", is_flag=True, help="递归处理子目录")
@click.option("--filter-ext", multiple=True, help="只处理指定扩展名的文件")
@click.pass_context
def apply(
    ctx,
    source_directory: Optional[str],
    dry_run: bool,
    recursive: bool,
    filter_ext: tuple,
):
    """执行文档分类整理 (Stage 1 MVP)"""
    config = ctx.obj["config"]

    # 更新配置
    if dry_run:
        config.system.dry_run = True
        click.echo("🔍 模拟运行模式 - 不会实际移动文件")

    # 确定源目录
    if not source_directory:
        source_directory = config.file.source_directory
        if not source_directory:
            click.echo("❌ 未指定源目录，请提供目录路径或在配置中设置", err=True)
            return

    source_path = Path(source_directory)
    if not source_path.exists():
        click.echo(f"❌ 源目录不存在: {source_path}", err=True)
        return

    click.echo(f"📁 处理目录: {source_path}")
    click.echo(f"🎯 目标目录: {config.file.target_directory}")

    try:
        # 创建工作流
        workflow = DocumentClassificationWorkflow(config.get_config_dict())

        # 收集文件
        files_to_process = []

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for file_path in source_path.glob(pattern):
            if file_path.is_file():
                # 检查扩展名过滤
                if filter_ext:
                    if file_path.suffix.lower() not in filter_ext:
                        continue
                else:
                    # 检查是否在支持的扩展名中
                    if file_path.suffix.lower() not in config.file.supported_extensions:
                        continue

                files_to_process.append(file_path)

        if not files_to_process:
            click.echo("ℹ️  没有找到需要处理的文件")
            return

        click.echo(f"📋 找到 {len(files_to_process)} 个文件待处理")

        # 处理文件
        results = {
            "total": len(files_to_process),
            "success": 0,
            "failed": 0,
            "needs_review": 0,
            "details": [],
        }

        with click.progressbar(files_to_process, label="处理文件") as files:
            for file_path in files:
                try:
                    result = workflow.process_file(file_path)

                    # 分析结果
                    if result.get("move_success", False):
                        results["success"] += 1
                        status = "✅ 成功"
                    elif result.get("classification", {}).get("needs_review", False):
                        results["needs_review"] += 1
                        status = "⚠️  需要审核"
                    else:
                        results["failed"] += 1
                        status = "❌ 失败"

                    # 记录详细信息
                    details = {
                        "file": str(file_path),
                        "status": status,
                        "category": result.get("classification", {}).get(
                            "primary_category", "未知"
                        ),
                        "confidence": result.get("classification", {}).get(
                            "confidence_score", 0.0
                        ),
                        "new_path": result.get("move_result", {}).get(
                            "primary_target_path", ""
                        ),
                        "error": result.get("error", ""),
                    }
                    results["details"].append(details)

                except Exception as e:
                    results["failed"] += 1
                    click.echo(f"\n❌ 处理失败: {file_path} - {e}")

        # 显示结果汇总
        click.echo("\n" + "=" * 50)
        click.echo("📊 处理结果汇总")
        click.echo("=" * 50)
        click.echo(f"总文件数: {results['total']}")
        click.echo(f"成功处理: {results['success']}")
        click.echo(f"需要审核: {results['needs_review']}")
        click.echo(f"处理失败: {results['failed']}")

        # 显示详细结果
        if ctx.obj.get("verbose", False):
            click.echo("\n📋 详细结果:")
            for detail in results["details"]:
                click.echo(f"{detail['status']} {detail['file']}")
                if detail["category"] != "未知":
                    click.echo(
                        f"    分类: {detail['category']} (置信度: {detail['confidence']:.2f})"
                    )
                if detail["new_path"]:
                    click.echo(f"    新路径: {detail['new_path']}")
                if detail["error"]:
                    click.echo(f"    错误: {detail['error']}")

        # 需要审核的文件
        if results["needs_review"] > 0:
            click.echo(f"\n⚠️  有 {results['needs_review']} 个文件需要人工审核")
            click.echo("💡 使用 'ods review' 命令处理这些文件")

    except Exception as e:
        click.echo(f"❌ 工作流执行失败: {e}", err=True)


@main.command()
@click.pass_context  
def info(ctx):
    """显示系统信息"""
    config = ctx.obj['config']
    
    click.echo("=== 系统配置信息 ===")
    click.echo(f"配置文件: {config.config_path}")
    click.echo(f"数据库路径: {config.database.path}")
    click.echo(f"临时目录: {config.system.temp_directory}")
    click.echo(f"支持的文件类型: {', '.join(config.file.supported_extensions)}")
    
    # 解析器信息
    parser = DocumentParser(config.get_config_dict())
    parser_info = parser.get_parser_info()
    
    click.echo("\n=== 解析器信息 ===")
    click.echo(f"可用解析器: {', '.join(parser_info['available_parsers'])}")
    click.echo(f"支持的扩展名: {', '.join(parser_info['supported_extensions'])}")


if __name__ == '__main__':
    main()
