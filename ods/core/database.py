"""
数据库管理模块

负责SQLite数据库的创建、连接和基础操作
"""

import sqlite3
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class Database:
    """数据库管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据库管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 数据库配置
        db_config = config.get("database", {})
        self.db_path = db_config.get("path", ".ods/db.sqlite")
        
        # 确保数据库目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        self.logger.info(f"数据库初始化完成: {self.db_path}")
    
    def _init_database(self) -> None:
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 文件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    file_extension TEXT,
                    creation_time TIMESTAMP,
                    modification_time TIMESTAMP,
                    last_processed TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 分类结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    category TEXT NOT NULL,
                    confidence REAL,
                    tags TEXT,  -- JSON格式的标签列表
                    parser_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            ''')
            
            # 操作日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    operation_type TEXT NOT NULL,
                    old_path TEXT,
                    new_path TEXT,
                    old_name TEXT,
                    new_name TEXT,
                    tags TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            ''')
            
            # 用户反馈表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    original_category TEXT,
                    corrected_category TEXT,
                    original_tags TEXT,
                    corrected_tags TEXT,
                    feedback_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files (id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files (file_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_status ON files (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_classifications_file_id ON classifications (file_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_file_id ON operation_logs (file_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_type ON operation_logs (operation_type)')
            
            conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[sqlite3.Row]: 查询结果
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        执行更新语句
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def insert_file(self, file_path: str, file_info: Dict[str, Any]) -> int:
        """
        插入文件记录
        
        Args:
            file_path: 文件路径
            file_info: 文件信息
            
        Returns:
            int: 插入记录的ID
        """
        query = '''
            INSERT INTO files (file_path, file_name, file_size, file_extension, 
                             creation_time, modification_time, last_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            file_path,
            file_info.get('file_name', ''),
            file_info.get('file_size', 0),
            file_info.get('file_extension', ''),
            file_info.get('creation_time'),
            file_info.get('modification_time'),
            datetime.now()
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def update_file_status(self, file_id: int, status: str) -> None:
        """
        更新文件状态
        
        Args:
            file_id: 文件ID
            status: 新状态
        """
        query = 'UPDATE files SET status = ?, updated_at = ? WHERE id = ?'
        self.execute_update(query, (status, datetime.now(), file_id))
    
    def get_file_by_path(self, file_path: str) -> Optional[sqlite3.Row]:
        """
        根据路径获取文件记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[sqlite3.Row]: 文件记录
        """
        query = 'SELECT * FROM files WHERE file_path = ?'
        results = self.execute_query(query, (file_path,))
        return results[0] if results else None
    
    def insert_classification(self, file_id: int, classification: Dict[str, Any]) -> int:
        """
        插入分类结果
        
        Args:
            file_id: 文件ID
            classification: 分类结果
            
        Returns:
            int: 插入记录的ID
        """
        import json
        
        query = '''
            INSERT INTO classifications (file_id, category, confidence, tags, parser_type)
            VALUES (?, ?, ?, ?, ?)
        '''
        params = (
            file_id,
            classification.get('category', ''),
            classification.get('confidence', 0.0),
            json.dumps(classification.get('tags', []), ensure_ascii=False),
            classification.get('parser_type', '')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def log_operation(self, file_id: int, operation: Dict[str, Any]) -> int:
        """
        记录操作日志
        
        Args:
            file_id: 文件ID
            operation: 操作信息
            
        Returns:
            int: 插入记录的ID
        """
        import json
        
        query = '''
            INSERT INTO operation_logs (file_id, operation_type, old_path, new_path,
                                      old_name, new_name, tags, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            file_id,
            operation.get('operation_type', ''),
            operation.get('old_path', ''),
            operation.get('new_path', ''),
            operation.get('old_name', ''),
            operation.get('new_name', ''),
            json.dumps(operation.get('tags', []), ensure_ascii=False),
            operation.get('success', False),
            operation.get('error_message', '')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_operation_logs(self, file_id: Optional[int] = None, limit: int = 100) -> List[sqlite3.Row]:
        """
        获取操作日志
        
        Args:
            file_id: 文件ID（可选）
            limit: 返回记录数限制
            
        Returns:
            List[sqlite3.Row]: 操作日志
        """
        if file_id:
            query = '''
                SELECT * FROM operation_logs 
                WHERE file_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            '''
            return self.execute_query(query, (file_id, limit))
        else:
            query = '''
                SELECT * FROM operation_logs
                ORDER BY created_at DESC
                LIMIT ?
            '''
            return self.execute_query(query, (limit,))

    def rollback_operation(self, operation_id: int) -> bool:
        """根据操作日志回滚文件移动。

        Args:
            operation_id: 操作日志ID

        Returns:
            bool: 回滚是否成功
        """
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM operation_logs WHERE id = ?', (operation_id,))
                row = cursor.fetchone()
            if not row:
                return False

            old_path = row['old_path']
            new_path = row['new_path']
            if not old_path or not new_path:
                return False

            src = Path(new_path)
            dst = Path(old_path)
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))

            # 更新文件记录路径
            self.execute_update(
                'UPDATE files SET file_path = ?, updated_at = ? WHERE id = ?',
                (old_path, datetime.now(), row['file_id'])
            )

            # 记录回滚操作
            self.log_operation(row['file_id'], {
                'operation_type': 'rollback',
                'old_path': new_path,
                'new_path': old_path,
                'old_name': row['new_name'],
                'new_name': row['old_name'],
                'tags': [],
                'success': True,
                'error_message': ''
            })
            return True
        except Exception as e:
            self.logger.error(f"回滚操作失败: {e}")
            return False
    
    def insert_feedback(self, feedback: Dict[str, Any]) -> int:
        """
        插入用户反馈
        
        Args:
            feedback: 反馈信息
            
        Returns:
            int: 插入记录的ID
        """
        import json
        
        query = '''
            INSERT INTO user_feedback (file_id, original_category, corrected_category,
                                     original_tags, corrected_tags, feedback_type)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        params = (
            feedback.get('file_id'),
            feedback.get('original_category', ''),
            feedback.get('corrected_category', ''),
            json.dumps(feedback.get('original_tags', []), ensure_ascii=False),
            json.dumps(feedback.get('corrected_tags', []), ensure_ascii=False),
            feedback.get('feedback_type', '')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {}
        
        # 文件总数
        result = self.execute_query('SELECT COUNT(*) as count FROM files')
        stats['total_files'] = result[0]['count'] if result else 0
        
        # 各状态文件数
        result = self.execute_query('''
            SELECT status, COUNT(*) as count 
            FROM files 
            GROUP BY status
        ''')
        stats['files_by_status'] = {row['status']: row['count'] for row in result}
        
        # 分类统计
        result = self.execute_query('''
            SELECT category, COUNT(*) as count 
            FROM classifications 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        stats['classifications'] = {row['category']: row['count'] for row in result}
        
        # 操作统计
        result = self.execute_query('''
            SELECT operation_type, COUNT(*) as count, 
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count
            FROM operation_logs 
            GROUP BY operation_type
        ''')
        stats['operations'] = {
            row['operation_type']: {
                'total': row['count'],
                'success': row['success_count']
            }
            for row in result
        }
        
        return stats
