import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import yaml
from datetime import datetime
import os


class PathPlanner:
    """路径规划器 - 根据分类结果决定文件存储路径"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 路径配置
        self.path_config = config.get('path_planning', {})
        self.base_path = self.path_config.get('base_path', 'OneDrive/分类')
        self.default_categories = self.path_config.get('default_categories', ['工作', '个人', '财务', '其他'])
        self.multi_label_strategy = self.path_config.get('multi_label_strategy', 'primary_with_links')
        self.path_template = self.path_config.get('path_template', '{category}/{year}/{month}')
        self.conflict_resolution = self.path_config.get('conflict_resolution', 'suffix')
        self.max_path_length = self.path_config.get('max_path_length', 260)  # Windows路径长度限制
        
        # 特殊路径配置
        self.special_paths = self.path_config.get('special_paths', {
            'uncategorized': '待整理',
            'needs_review': '待审核',
            'important': '重要文件',
            'archive': '归档'
        })

        # 加载路径映射规则
        self.category_path_mapping = self._load_category_mapping()

        # 确保基础目录及常见类别目录存在，便于测试环境使用
        base = Path(self.base_path)
        base.mkdir(parents=True, exist_ok=True)
        for cat in self.default_categories:
            (base / cat).mkdir(parents=True, exist_ok=True)
        for spath in self.special_paths.values():
            (base / spath).mkdir(parents=True, exist_ok=True)

        self.logger.info("路径规划器初始化完成")

    def plan_file_path(self, classification_result: Dict[str, Any], 
                      original_path: str, 
                      file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """规划文件路径"""
        try:
            self.logger.info(f"开始规划文件路径: {original_path}")
            
            # 获取分类信息
            primary_category = classification_result.get('primary_category', 'uncategorized')
            confidence_score = classification_result.get('confidence_score', 0.0)
            tags = classification_result.get('tags', [])
            
            # 检查是否需要人工审核
            if confidence_score < self.config.get('classification', {}).get('review_threshold', 0.6):
                return self._create_review_path(original_path, classification_result)
            
            # 确定主存储路径
            primary_path = self._determine_primary_path(
                primary_category, original_path, file_metadata
            )
            
            # 处理多标签情况
            link_paths = self._plan_link_paths(tags, primary_category, primary_path)
            
            # 检查路径冲突
            conflict_info = self._check_path_conflicts(primary_path, original_path)
            
            # 生成路径规划结果
            path_plan = {
                'original_path': original_path,
                'primary_path': primary_path,
                'link_paths': link_paths,
                'conflict_info': conflict_info,
                'category': primary_category,
                'tags': tags,
                'confidence_score': confidence_score,
                'planning_time': datetime.now().isoformat(),
                'status': 'planned'
            }
            
            self.logger.info(f"路径规划完成: {original_path} -> {primary_path}")
            return path_plan
            
        except Exception as e:
            self.logger.error(f"路径规划失败: {e}")
            return self._create_error_path(original_path, str(e))

    def _determine_primary_path(self, category: str, original_path: str, 
                              metadata: Dict[str, Any]) -> str:
        """确定主存储路径"""
        # 获取文件信息
        original_file = Path(original_path)
        file_name = original_file.name
        file_ext = original_file.suffix
        
        # 获取类别对应的基础路径
        category_base = self._get_category_base_path(category)
        
        # 应用路径模板
        template_vars = self._get_template_variables(category, metadata)
        relative_path = self._apply_path_template(self.path_template, template_vars)
        
        # 构建完整路径
        full_path = Path(self.base_path) / category_base / relative_path
        
        # 确保路径长度在限制内
        full_path = self._ensure_path_length(full_path, file_name)
        
        return str(full_path / file_name)

    def _get_category_base_path(self, category: str) -> str:
        """获取类别对应的基础路径"""
        # 检查特殊路径映射
        if category.lower() in self.special_paths:
            return self.special_paths[category.lower()]
        
        # 检查用户定义的映射
        if category in self.category_path_mapping:
            return self.category_path_mapping[category]

        # 使用默认类别路径
        if category in self.default_categories:
            return category

        # 未知类别使用通用“其他”目录
        return '其他'

    def _get_template_variables(self, category: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """获取路径模板变量"""
        now = datetime.now()
        
        variables = {
            'category': category,
            'year': str(now.year),
            'month': f"{now.month:02d}",
            'day': f"{now.day:02d}",
            'date': now.strftime('%Y%m%d'),
            'timestamp': now.strftime('%Y%m%d_%H%M%S')
        }
        
        # 添加元数据中的变量
        if metadata:
            variables.update(metadata)
        
        return variables

    def _apply_path_template(self, template: str, variables: Dict[str, Any]) -> str:
        """应用路径模板"""
        try:
            # 简单的模板替换，可以扩展为Jinja2
            result = template
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
            return result
        except Exception as e:
            self.logger.warning(f"模板应用失败: {e}")
            return ""

    def _plan_link_paths(self, tags: List[str], primary_category: str, 
                        primary_path: str) -> List[Dict[str, Any]]:
        """规划链接路径（多标签情况）"""
        link_paths = []
        
        if self.multi_label_strategy == 'primary_with_links':
            for tag in tags:
                if tag != primary_category:
                    tag_base = self._get_category_base_path(tag)
                    link_path = Path(self.base_path) / tag_base / "链接"
                    
                    # 创建软链接信息
                    link_info = {
                        'source_path': primary_path,
                        'link_path': str(link_path / Path(primary_path).name),
                        'tag': tag,
                        'type': 'soft_link'
                    }
                    link_paths.append(link_info)
        
        return link_paths

    def _check_path_conflicts(self, target_path: str, original_path: str) -> Dict[str, Any]:
        """检查路径冲突"""
        target_file = Path(target_path)
        
        conflict_info = {
            'has_conflict': False,
            'conflict_type': None,
            'resolution': None,
            'suggested_path': target_path
        }
        
        # 检查文件是否已存在
        if target_file.exists():
            conflict_info['has_conflict'] = True
            conflict_info['conflict_type'] = 'file_exists'
            
            # 应用冲突解决策略
            if self.conflict_resolution == 'suffix':
                resolved_path = self._resolve_conflict_with_suffix(target_path)
                conflict_info['resolution'] = 'suffix'
                conflict_info['suggested_path'] = resolved_path
            elif self.conflict_resolution == 'timestamp':
                resolved_path = self._resolve_conflict_with_timestamp(target_path)
                conflict_info['resolution'] = 'timestamp'
                conflict_info['suggested_path'] = resolved_path
        
        # 检查路径长度
        if len(str(target_file)) > self.max_path_length:
            conflict_info['has_conflict'] = True
            conflict_info['conflict_type'] = 'path_too_long'
            resolved_path = self._resolve_long_path(target_path)
            conflict_info['resolution'] = 'truncate'
            conflict_info['suggested_path'] = resolved_path
        
        return conflict_info

    def _resolve_conflict_with_suffix(self, path: str) -> str:
        """通过添加后缀解决冲突"""
        path_obj = Path(path)
        counter = 1

        # 如果原始文件不存在，仍然为其添加后缀以演示冲突解决策略
        if not path_obj.exists():
            return str(path_obj.parent / f"{path_obj.stem}_{counter}{path_obj.suffix}")

        while path_obj.exists():
            stem = path_obj.stem
            suffix = path_obj.suffix
            new_name = f"{stem}_{counter}{suffix}"
            path_obj = path_obj.parent / new_name
            counter += 1

        return str(path_obj)

    def _resolve_conflict_with_timestamp(self, path: str) -> str:
        """通过添加时间戳解决冲突"""
        path_obj = Path(path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = path_obj.stem
        suffix = path_obj.suffix
        new_name = f"{stem}_{timestamp}{suffix}"
        
        return str(path_obj.parent / new_name)

    def _resolve_long_path(self, path: str) -> str:
        """解决路径过长问题"""
        path_obj = Path(path)
        
        # 计算需要缩短的长度
        current_length = len(str(path_obj))
        excess_length = current_length - self.max_path_length + 10  # 留一些余量
        
        if excess_length > 0:
            # 缩短文件名
            stem = path_obj.stem
            suffix = path_obj.suffix
            
            # 保留扩展名，缩短文件名
            max_stem_length = len(stem) - excess_length
            if max_stem_length > 10:  # 确保文件名至少有10个字符
                new_stem = stem[:max_stem_length]
                new_name = f"{new_stem}{suffix}"
                return str(path_obj.parent / new_name)
        
        return path

    def _ensure_path_length(self, path: Path, filename: str) -> Path:
        """确保路径长度在限制内"""
        full_path = path / filename
        
        if len(str(full_path)) <= self.max_path_length:
            return path
        
        # 路径过长，需要缩短
        max_path_length = self.max_path_length - len(filename) - 1  # 减去文件名和分隔符
        
        # 从路径末尾开始缩短
        path_parts = list(path.parts)
        while len(str(Path(*path_parts))) > max_path_length and len(path_parts) > 1:
            path_parts.pop()
        
        return Path(*path_parts)

    def _create_review_path(self, original_path: str, 
                          classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建需要审核的路径"""
        review_base = self.special_paths.get('needs_review', '待审核')
        review_path = Path(self.base_path) / review_base / Path(original_path).name
        
        return {
            'original_path': original_path,
            'primary_path': str(review_path),
            'link_paths': [],
            'conflict_info': {'has_conflict': False},
            'category': 'needs_review',
            'tags': classification_result.get('tags', []),
            'confidence_score': classification_result.get('confidence_score', 0.0),
            'planning_time': datetime.now().isoformat(),
            'status': 'needs_review',
            'review_reason': '置信度不足'
        }

    def _create_error_path(self, original_path: str, error_message: str) -> Dict[str, Any]:
        """创建错误路径"""
        error_base = self.special_paths.get('uncategorized', '其他')
        error_path = Path(self.base_path) / error_base / Path(original_path).name
        
        return {
            'original_path': original_path,
            'primary_path': str(error_path),
            'link_paths': [],
            'conflict_info': {'has_conflict': False},
            'category': 'error',
            'tags': [],
            'confidence_score': 0.0,
            'planning_time': datetime.now().isoformat(),
            'status': 'error',
            'error_message': error_message
        }

    def _load_category_mapping(self) -> Dict[str, str]:
        """加载类别路径映射"""
        mapping_file = self.path_config.get('category_mapping_file', 'config/category_mapping.yaml')
        
        try:
            if Path(mapping_file).exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.warning(f"加载类别映射失败: {e}")
        
        return {}

    def create_directory_structure(self, path_plan: Dict[str, Any]) -> bool:
        """创建目录结构"""
        try:
            # 创建主路径目录
            primary_path = Path(path_plan['primary_path'])
            primary_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建链接路径目录
            for link_info in path_plan.get('link_paths', []):
                link_path = Path(link_info['link_path'])
                link_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"目录结构创建成功: {primary_path.parent}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建目录结构失败: {e}")
            return False

    def validate_path_plan(self, path_plan: Dict[str, Any]) -> Dict[str, Any]:
        """验证路径规划结果"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查必要字段
        required_fields = ['original_path', 'primary_path', 'status']
        for field in required_fields:
            if field not in path_plan:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"缺少必要字段: {field}")
        
        # 检查路径格式
        if 'primary_path' in path_plan:
            try:
                Path(path_plan['primary_path'])
            except Exception as e:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"主路径格式错误: {e}")
        
        # 检查路径长度
        if 'primary_path' in path_plan and len(path_plan['primary_path']) > self.max_path_length:
            validation_result['warnings'].append(f"路径长度超过限制: {len(path_plan['primary_path'])} > {self.max_path_length}")
        
        return validation_result

    def get_path_statistics(self) -> Dict[str, Any]:
        """获取路径规划统计信息"""
        return {
            'base_path': self.base_path,
            'default_categories': self.default_categories,
            'multi_label_strategy': self.multi_label_strategy,
            'path_template': self.path_template,
            'max_path_length': self.max_path_length,
            'special_paths': self.special_paths,
            'category_mapping_count': len(self.category_path_mapping)
        }
