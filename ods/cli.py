"""
命令行界面

提供基础的命令行功能
"""

import click
import logging
from pathlib import Path
from typing import Optional

from .core.config import Config
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
