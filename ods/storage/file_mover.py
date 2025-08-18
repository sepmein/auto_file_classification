"""
文件移动器（占位符）

用于后续实现文件移动和重命名功能
"""

import logging
import os
import shutil
import subprocess
import sys
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class FileMover:
	"""文件移动器 - 执行实际的文件移动、重命名与链接创建

	特性:
	- 主文件移动/重命名到目标路径
	- 为多标签创建软链接或快捷方式（Windows .lnk / Unix symlink）
	- 原位置清理（可选）
	- 事务性与回滚支持
	- 详细的操作报告
	"""

	def __init__(self, config: Dict[str, Any]):
		self.config = config
		self.logger = logging.getLogger(__name__)

		file_cfg = config.get('file', {})
		self.dry_run = config.get('system', {}).get('dry_run', False)
		self.cleanup_empty_dirs = file_cfg.get('cleanup_empty_dirs', False)
		self.allow_symlink = file_cfg.get('allow_symlink', True)
		self.allow_windows_shortcut = file_cfg.get('allow_windows_shortcut', True)
		self.use_hardlink_on_windows = file_cfg.get('use_hardlink_on_windows', False)

		self.logger.info("文件移动器初始化完成")

	def move_file(self, path_plan: Dict[str, Any], naming_result: Dict[str, Any]) -> Dict[str, Any]:
		"""执行移动与链接创建的主入口

		Args:
			path_plan: 路径规划结果（包含 primary_path 与 link_paths）
			naming_result: 命名生成结果（包含 new_path/new_filename 等）

		Returns:
			操作报告字典
		"""
		report: Dict[str, Any] = {
			'old_path': path_plan.get('original_path', ''),
			'primary_target_path': naming_result.get('new_path') or path_plan.get('primary_path'),
			'link_creations': [],
			'moved': False,
			'rolled_back': False,
			'errors': [],
			'completed_at': None,
		}

		operations_log: List[Dict[str, Any]] = []

		try:
			old_path = Path(report['old_path'])
			target_path = Path(report['primary_target_path'])

			if not old_path.exists():
				raise FileNotFoundError(f"源文件不存在: {old_path}")

			# 确保目标目录存在
			target_path.parent.mkdir(parents=True, exist_ok=True)

			# 执行移动/重命名
			self._move_main_file(old_path, target_path, operations_log)
			report['moved'] = True

			# 根据 link_paths 创建链接/快捷方式，使用重命名后的文件名
			link_paths = path_plan.get('link_paths', [])
			if link_paths:
				for link_info in link_paths:
					created = self._create_link_for_tag(target_path, link_info, operations_log)
					report['link_creations'].append(created)

			# 清理原目录（可选）
			if self.cleanup_empty_dirs:
				self._cleanup_empty_directories(old_path.parent, operations_log)

			return report

		except Exception as exc:
			msg = f"移动执行失败: {exc}"
			self.logger.error(msg, exc_info=True)
			report['errors'].append(str(exc))
			# 回滚
			try:
				self._rollback(operations_log)
				report['rolled_back'] = True
			except Exception as rb_exc:
				self.logger.error(f"回滚失败: {rb_exc}", exc_info=True)
				report['errors'].append(f"回滚失败: {rb_exc}")
			return report
		finally:
			report['completed_at'] = datetime.now().isoformat()

	def _move_main_file(self, old_path: Path, new_path: Path, operations_log: List[Dict[str, Any]]):
		"""移动主文件，记录操作以便回滚"""
		self.logger.info(f"移动文件: {old_path} -> {new_path}")
		if self.dry_run:
			self.logger.info("Dry-run: 跳过实际移动")
			operations_log.append({'op': 'move_dry', 'from': str(old_path), 'to': str(new_path)})
			return

		# 如果目标存在，避免覆盖：添加后缀
			
		final_target = new_path
		counter = 1
		while final_target.exists():
			final_target = new_path.with_name(f"{new_path.stem}_{counter}{new_path.suffix}")
			counter += 1
		if final_target != new_path:
			self.logger.warning(f"目标已存在，使用新路径: {final_target}")

		shutil.move(str(old_path), str(final_target))
		operations_log.append({'op': 'move', 'from': str(old_path), 'to': str(final_target)})

	def _create_link_for_tag(self, primary_target: Path, link_info: Dict[str, Any], operations_log: List[Dict[str, Any]]) -> Dict[str, Any]:
		"""为标签创建链接或快捷方式，返回创建结果"""
		link_target_dir = Path(link_info.get('link_path', '')).parent
		link_target_dir.mkdir(parents=True, exist_ok=True)

		# 链接文件应当与主文件同名（已在工作流命名阶段调整），确保名称
		link_file_path = Path(link_info.get('link_path', ''))
		if link_file_path.name != primary_target.name:
			link_file_path = link_file_path.with_name(primary_target.name)

		self.logger.info(f"创建链接: {link_file_path} -> {primary_target}")

		if self.dry_run:
			operations_log.append({'op': 'link_dry', 'path': str(link_file_path)})
			return {'path': str(link_file_path), 'type': link_info.get('type', 'link'), 'ok': True, 'dry_run': True}

		ok = False
		error = None
		try:
			if os.name == 'nt':
				ok = self._create_windows_link(link_file_path, primary_target)
			else:
				ok = self._create_unix_symlink(link_file_path, primary_target)
			if ok:
				operations_log.append({'op': 'link', 'path': str(link_file_path)})
		except Exception as exc:
			error = str(exc)
			self.logger.error(f"创建链接失败: {exc}")

		return {'path': str(link_file_path), 'type': link_info.get('type', 'link'), 'ok': ok, 'error': error}

	def _create_unix_symlink(self, link_path: Path, target: Path) -> bool:
		"""在 Unix/macOS 上创建符号链接"""
		if not self.allow_symlink:
			return False
		# 如果已存在，先移除
		if link_path.exists() or link_path.is_symlink():
			try:
				link_path.unlink()
			except Exception:
				pass
		os.symlink(str(target), str(link_path))
		return True

	def _create_windows_link(self, link_path: Path, target: Path) -> bool:
		"""在 Windows 上创建快捷方式或硬链接/符号链接（按配置）"""
		# 优先硬链接（同卷且允许）
		try:
			if self.use_hardlink_on_windows:
				return self._try_create_hardlink_windows(link_path, target)
			# 尝试符号链接（需要权限）
			if self.allow_symlink:
				if link_path.exists() or link_path.is_symlink():
					try:
						link_path.unlink()
					except Exception:
						pass
					os.symlink(str(target), str(link_path), target_is_directory=False)
					return True
		except Exception:
			# 继续尝试创建 .lnk
			pass

		# 创建 .lnk 快捷方式
		if self.allow_windows_shortcut:
			return self._create_windows_shortcut_lnk(link_path, target)
		return False

	def _try_create_hardlink_windows(self, link_path: Path, target: Path) -> bool:
		"""尝试创建硬链接（仅同一卷可用）"""
		try:
			if link_path.exists():
				link_path.unlink()
			os.link(str(target), str(link_path))
			return True
		except Exception:
			return False

	def _create_windows_shortcut_lnk(self, link_path: Path, target: Path) -> bool:
		"""通过可用方式创建 .lnk 快捷方式。

		优先使用 pywin32 的 win32com；若不可用，尝试 PowerShell。"""
		lnk_path = link_path.with_suffix('.lnk') if link_path.suffix.lower() != '.lnk' else link_path

		# 1) 尝试 win32com
		try:
			import win32com.client  # type: ignore
			ws = win32com.client.Dispatch('WScript.Shell')
			shortcut = ws.CreateShortcut(str(lnk_path))
			shortcut.TargetPath = str(target)
			shortcut.WorkingDirectory = str(target.parent)
			shortcut.IconLocation = str(target)
			shortcut.Save()
			return True
		except Exception:
			pass

		# 2) 尝试 PowerShell 脚本创建 .lnk
		try:
			ps_script = (
				f"$WScriptShell = New-Object -ComObject WScript.Shell;"
				f"$Shortcut = $WScriptShell.CreateShortcut('{str(lnk_path).replace("'","''")}');"
				f"$Shortcut.TargetPath = '{str(target).replace("'","''")}';"
				f"$Shortcut.WorkingDirectory = '{str(target.parent).replace("'","''")}';"
				f"$Shortcut.Save();"
			)
			completed = subprocess.run([
				"powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script
			], capture_output=True, text=True)
			if completed.returncode == 0:
				return True
			self.logger.warning(f"PowerShell创建快捷方式失败: {completed.stderr}")
		except Exception as exc:
			self.logger.warning(f"PowerShell创建快捷方式异常: {exc}")
		return False

	def _cleanup_empty_directories(self, start_dir: Path, operations_log: List[Dict[str, Any]]):
		"""自下而上清理空目录"""
		try:
			curr = start_dir
			while True:
				if not curr.exists() or any(curr.iterdir()):
					break
				if self.dry_run:
					operations_log.append({'op': 'rmdir_dry', 'path': str(curr)})
					break
				curr.rmdir()
				operations_log.append({'op': 'rmdir', 'path': str(curr)})
				if curr.parent == curr:
					break
				curr = curr.parent
		except Exception as exc:
			self.logger.warning(f"清理空目录失败: {exc}")

	def _rollback(self, operations_log: List[Dict[str, Any]]):
		"""根据操作日志回滚：逆序撤销 move 与 link 创建"""
		for entry in reversed(operations_log):
			op = entry.get('op')
			if op == 'move':
				# 将文件移回原处
				src = Path(entry['to'])
				dst = Path(entry['from'])
				try:
					if src.exists():
						shutil.move(str(src), str(dst))
						self.logger.info(f"回滚: 移回 {src} -> {dst}")
				except Exception as exc:
					self.logger.error(f"回滚移动失败: {exc}")
			elif op == 'link':
				p = Path(entry['path'])
				try:
					if p.exists() or p.is_symlink():
						p.unlink()
						self.logger.info(f"回滚: 删除链接 {p}")
				except Exception as exc:
					self.logger.warning(f"回滚删除链接失败: {exc}")
