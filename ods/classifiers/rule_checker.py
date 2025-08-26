"""
规则检查器模块
负责应用用户定义的规则来调整分类结果
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import yaml


class RuleChecker:
    """规则检查器 - 应用用户定义的规则调整分类结果"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 规则配置
        self.rules_config = config.get('rules', {})
        self.rules_file = self.rules_config.get('rules_file', 'config/rules.yaml')
        # 如果未提供规则配置，则默认禁用规则以避免意外影响
        self.enable_rules = self.rules_config.get('enable_rules', bool(self.rules_config))
        self.strict_mode = self.rules_config.get('strict_mode', False)
        
        # 加载规则
        self.rules = self._load_rules()
        # 简单规则（阶段2）
        extra_simple = self.rules_config.get('simple_rules', [])
        if extra_simple:
            self.simple_rules.extend(extra_simple)
        
        # 规则类型
        self.rule_types = {
            'file_extension': self._check_file_extension_rules,
            'file_name': self._check_file_name_rules,
            'content_keywords': self._check_content_keywords_rules,
            'file_size': self._check_file_size_rules,
            'file_path': self._check_file_path_rules,
            'custom': self._check_custom_rules
        }
    
    def _load_rules(self) -> Dict[str, Any]:
        """加载规则配置"""
        try:
            if not self.enable_rules:
                self.logger.info("规则检查已禁用")
                self.simple_rules = []
                return {}

            rules_path = Path(self.rules_file)
            if not rules_path.exists():
                self.logger.warning(f"规则文件不存在: {rules_path}")
                return self._get_default_rules()

            with open(rules_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # 提取简单规则
            self.simple_rules = data.get('simple_rules', [])
            for key in ['simple_rules']:
                data.pop(key, None)

            # 验证规则格式
            validated_rules = self._validate_rules(data)
            self.logger.info(f"成功加载 {len(validated_rules)} 条规则，{len(self.simple_rules)} 条简单规则")
            return validated_rules

        except Exception as e:
            self.logger.error(f"加载规则失败: {e}")
            return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """获取默认规则"""
        self.simple_rules = []
        return {
            'file_extension': {
                '.pdf': {'category': '文档', 'priority': 1},
                '.docx': {'category': '文档', 'priority': 1},
                '.doc': {'category': '文档', 'priority': 1},
                '.txt': {'category': '文本', 'priority': 1},
                '.md': {'category': '文本', 'priority': 1},
                '.jpg': {'category': '图片', 'priority': 1},
                '.png': {'category': '图片', 'priority': 1},
                '.xlsx': {'category': '表格', 'priority': 1},
                '.pptx': {'category': '演示', 'priority': 1}
            },
            'file_name': {
                '发票': {'category': '财务', 'priority': 2},
                '合同': {'category': '工作', 'priority': 2},
                '简历': {'category': '个人', 'priority': 2},
                '报告': {'category': '工作', 'priority': 2}
            },
            'content_keywords': {
                '发票': {'category': '财务', 'priority': 3},
                '金额': {'category': '财务', 'priority': 3},
                '合同': {'category': '工作', 'priority': 3},
                '项目': {'category': '工作', 'priority': 3},
                '个人': {'category': '个人', 'priority': 3}
            }
        }
    
    def _validate_rules(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """验证规则格式"""
        validated_rules = {}
        
        for rule_type, rule_data in rules.items():
            if rule_type in self.rule_types:
                if isinstance(rule_data, dict):
                    validated_rules[rule_type] = rule_data
                else:
                    self.logger.warning(f"规则类型 {rule_type} 格式无效，跳过")
            else:
                self.logger.warning(f"未知规则类型: {rule_type}")
        
        return validated_rules
    
    def apply_rules(self, classification_result: Dict[str, Any],
                   document_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用规则调整分类结果"""
        try:
            result = classification_result.copy()

            if self.enable_rules and self.rules:
                self.logger.info("开始应用规则检查")

                # 收集所有规则匹配结果
                rule_matches = []

                for rule_type, rule_checker in self.rule_types.items():
                    if rule_type in self.rules:
                        matches = rule_checker(document_data, self.rules[rule_type])
                        rule_matches.extend(matches)

                if rule_matches:
                    # 按优先级排序规则匹配
                    rule_matches.sort(key=lambda x: x['priority'], reverse=True)

                    # 应用最高优先级的规则
                    top_rule = rule_matches[0]
                    self.logger.info(f"应用规则: {top_rule['rule_type']} -> {top_rule['category']}")

                    result['primary_category'] = top_rule['category']
                    result['rule_applied'] = {
                        'rule_type': top_rule['rule_type'],
                        'rule_value': top_rule['rule_value'],
                        'priority': top_rule['priority'],
                        'confidence_boost': 0.2
                    }

                    # 提高置信度
                    original_confidence = result.get('confidence_score', 0.0)
                    result['confidence_score'] = min(1.0, original_confidence + 0.2)

                    # 更新推理
                    original_reasoning = result.get('reasoning', '')
                    result['reasoning'] = f"{original_reasoning} (应用规则: {top_rule['rule_type']}={top_rule['rule_value']})"

                    if result['confidence_score'] >= 0.8:
                        result['needs_review'] = False

            # 无论是否应用复杂规则，都执行简单规则以生成标签等
            result = self._apply_simple_rules(result, document_data)
            return result

        except Exception as e:
            self.logger.error(f"应用规则失败: {e}")
            return classification_result
    
    def _check_file_extension_rules(self, document_data: Dict[str, Any], 
                                   rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查文件扩展名规则"""
        matches = []
        file_path = document_data.get('file_path', '')
        
        if file_path:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in rules:
                rule_info = rules[file_ext]
                matches.append({
                    'rule_type': 'file_extension',
                    'rule_value': file_ext,
                    'category': rule_info['category'],
                    'priority': rule_info.get('priority', 1)
                })
        
        return matches
    
    def _check_file_name_rules(self, document_data: Dict[str, Any], 
                              rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查文件名规则"""
        matches = []
        file_path = document_data.get('file_path', '')
        
        if file_path:
            file_name = Path(file_path).stem.lower()
            for keyword, rule_info in rules.items():
                if keyword.lower() in file_name:
                    matches.append({
                        'rule_type': 'file_name',
                        'rule_value': keyword,
                        'category': rule_info['category'],
                        'priority': rule_info.get('priority', 1)
                    })
        
        return matches
    
    def _check_content_keywords_rules(self, document_data: Dict[str, Any], 
                                    rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查内容关键词规则"""
        matches = []
        text_content = document_data.get('text_content', '')
        summary = document_data.get('summary', '')
        
        # 合并文本内容
        full_text = f"{text_content} {summary}".lower()
        
        for keyword, rule_info in rules.items():
            if keyword.lower() in full_text:
                matches.append({
                    'rule_type': 'content_keywords',
                    'rule_value': keyword,
                    'category': rule_info['category'],
                    'priority': rule_info.get('priority', 1)
                })
        
        return matches
    
    def _check_file_size_rules(self, document_data: Dict[str, Any], 
                              rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查文件大小规则"""
        matches = []
        file_size = document_data.get('metadata', {}).get('size', 0)
        
        for size_rule, rule_info in rules.items():
            # 解析大小规则（如 ">10MB", "<1MB"）
            if self._evaluate_size_rule(file_size, size_rule):
                matches.append({
                    'rule_type': 'file_size',
                    'rule_value': size_rule,
                    'category': rule_info['category'],
                    'priority': rule_info.get('priority', 1)
                })
        
        return matches
    
    def _check_file_path_rules(self, document_data: Dict[str, Any], 
                              rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查文件路径规则"""
        matches = []
        file_path = document_data.get('file_path', '')
        
        if file_path:
            file_path_lower = str(file_path).lower()
            for path_pattern, rule_info in rules.items():
                if path_pattern.lower() in file_path_lower:
                    matches.append({
                        'rule_type': 'file_path',
                        'rule_value': path_pattern,
                        'category': rule_info['category'],
                        'priority': rule_info.get('priority', 1)
                    })
        
        return matches
    
    def _check_custom_rules(self, document_data: Dict[str, Any],
                           rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查自定义规则"""
        matches = []
        
        for rule_name, rule_config in rules.items():
            try:
                # 自定义规则应该包含条件表达式和结果
                condition = rule_config.get('condition', '')
                if condition and self._evaluate_custom_condition(condition, document_data):
                    matches.append({
                        'rule_type': 'custom',
                        'rule_value': rule_name,
                        'category': rule_config['category'],
                        'priority': rule_config.get('priority', 1)
                    })
            except Exception as e:
                self.logger.warning(f"自定义规则 {rule_name} 执行失败: {e}")

        return matches

    def _apply_simple_rules(self, result: Dict[str, Any],
                            document_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用简单规则并生成标签"""
        try:
            # 构建初始标签集合
            tags = result.get('tags')
            if tags is None:
                tags = []
                primary = result.get('primary_category')
                if primary:
                    tags.append(primary)
                tags.extend(result.get('secondary_categories', []))
                tags.extend(result.get('suggested_tags', []))

            file_name = Path(document_data.get('file_path', '')).name
            content = document_data.get('text_content') or document_data.get('summary', '')

            for rule in self.simple_rules:
                try:
                    if 'if_filename' in rule and 'add_tag' in rule:
                        if rule['if_filename'] in file_name:
                            tags.append(rule['add_tag'])

                    if 'if_content_regex' in rule and 'add_tag' in rule:
                        if re.search(rule['if_content_regex'], content, re.IGNORECASE):
                            tags.append(rule['add_tag'])

                    if 'if_tag_combo' in rule and rule.get('action') == 'require_review':
                        combo = rule['if_tag_combo']
                        if all(t in tags for t in combo):
                            result['needs_review'] = True
                except Exception as e:
                    self.logger.warning(f"简单规则执行失败: {e}")

            # 去重并保存
            result['tags'] = list(dict.fromkeys(tags))
            return result

        except Exception as e:
            self.logger.warning(f"应用简单规则失败: {e}")
            result['tags'] = result.get('tags') or []
            return result
    
    def _evaluate_size_rule(self, file_size: int, size_rule: str) -> bool:
        """评估文件大小规则"""
        try:
            # 解析大小规则
            if '>' in size_rule:
                threshold = self._parse_size_string(size_rule.split('>')[1])
                return file_size > threshold
            elif '<' in size_rule:
                threshold = self._parse_size_string(size_rule.split('<')[1])
                return file_size < threshold
            elif '=' in size_rule:
                threshold = self._parse_size_string(size_rule.split('=')[1])
                return file_size == threshold
            else:
                return False
        except:
            return False
    
    def _parse_size_string(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.strip().upper()
        if 'KB' in size_str:
            return int(float(size_str.replace('KB', '')) * 1024)
        elif 'MB' in size_str:
            return int(float(size_str.replace('MB', '')) * 1024 * 1024)
        elif 'GB' in size_str:
            return int(float(size_str.replace('GB', '')) * 1024 * 1024 * 1024)
        else:
            return int(float(size_str))
    
    def _evaluate_custom_condition(self, condition: str, document_data: Dict[str, Any]) -> bool:
        """评估自定义条件"""
        try:
            # 简单的条件评估，支持基本的逻辑运算
            # 这里可以实现更复杂的条件解析器
            
            # 示例：检查文件路径是否包含特定字符串
            if 'path_contains' in condition:
                pattern = re.search(r'path_contains\("([^"]+)"\)', condition)
                if pattern:
                    search_term = pattern.group(1)
                    file_path = document_data.get('file_path', '')
                    return search_term.lower() in str(file_path).lower()
            
            # 示例：检查文件大小是否大于某个值
            elif 'size_greater_than' in condition:
                pattern = re.search(r'size_greater_than\((\d+)\)', condition)
                if pattern:
                    threshold = int(pattern.group(1))
                    file_size = document_data.get('metadata', {}).get('size', 0)
                    return file_size > threshold
            
            return False
            
        except Exception as e:
            self.logger.warning(f"自定义条件评估失败: {e}")
            return False
    
    def add_rule(self, rule_type: str, rule_value: str, 
                 category: str, priority: int = 1) -> bool:
        """添加新规则"""
        try:
            if rule_type not in self.rules:
                self.rules[rule_type] = {}
            
            self.rules[rule_type][rule_value] = {
                'category': category,
                'priority': priority
            }
            
            self.logger.info(f"添加规则: {rule_type} -> {rule_value} -> {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加规则失败: {e}")
            return False
    
    def remove_rule(self, rule_type: str, rule_value: str) -> bool:
        """删除规则"""
        try:
            if rule_type in self.rules and rule_value in self.rules[rule_type]:
                del self.rules[rule_type][rule_value]
                self.logger.info(f"删除规则: {rule_type} -> {rule_value}")
                return True
            else:
                self.logger.warning(f"规则不存在: {rule_type} -> {rule_value}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除规则失败: {e}")
            return False
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        summary = {
            'total_rules': 0,
            'rules_by_type': {},
            'enabled': self.enable_rules,
            'strict_mode': self.strict_mode
        }
        
        for rule_type, rules in self.rules.items():
            summary['rules_by_type'][rule_type] = len(rules)
            summary['total_rules'] += len(rules)
        
        return summary
    
    def export_rules(self, export_path: str) -> bool:
        """导出规则配置"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.rules, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"规则配置已导出到: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出规则失败: {e}")
            return False
    
    def import_rules(self, import_path: str) -> bool:
        """导入规则配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                new_rules = yaml.safe_load(f)
            
            # 验证规则格式
            validated_rules = self._validate_rules(new_rules)
            
            # 更新规则
            self.rules.update(validated_rules)
            
            self.logger.info(f"成功导入 {len(validated_rules)} 条规则")
            return True
            
        except Exception as e:
            self.logger.error(f"导入规则失败: {e}")
            return False
