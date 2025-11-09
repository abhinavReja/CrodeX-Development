import os
import shutil
import time
import threading
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CleanupManager:
    """
    Manages cleanup of temporary files and old projects
    Implements automatic cleanup with scheduled tasks
    """
    
    def __init__(self, base_path: str, retention_hours: int = 24):
        """
        Initialize CleanupManager
        
        Args:
            base_path: Base path for project files
            retention_hours: Hours to retain files before cleanup
        """
        self.base_path = Path(base_path)
        self.retention_hours = retention_hours
        self.cleanup_thread = None
        self.running = False
        
        logger.info(f"CleanupManager initialized with retention: {retention_hours} hours")
    
    def cleanup_old_projects(self) -> Dict[str, int]:
        """
        Clean up projects older than retention period
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            stats = {
                'projects_checked': 0,
                'projects_deleted': 0,
                'space_freed': 0,
                'errors': 0
            }
            
            if not self.base_path.exists():
                return stats
            
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
            
            # Iterate through project directories
            for project_dir in self.base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                stats['projects_checked'] += 1
                
                try:
                    # Check last modified time
                    mtime = datetime.fromtimestamp(project_dir.stat().st_mtime)
                    
                    if mtime < cutoff_time:
                        # Calculate size before deletion
                        size = self._get_directory_size(project_dir)
                        
                        # Delete project
                        shutil.rmtree(project_dir)
                        
                        stats['projects_deleted'] += 1
                        stats['space_freed'] += size
                        
                        logger.info(f"Cleaned up old project: {project_dir.name}")
                
                except Exception as e:
                    logger.error(f"Error cleaning project {project_dir}: {str(e)}")
                    stats['errors'] += 1
            
            logger.info(f"Cleanup complete: {stats['projects_deleted']} projects deleted, "
                       f"{self._format_size(stats['space_freed'])} freed")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_project(self, project_id: str) -> bool:
        """
        Clean up specific project
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if successful
        """
        try:
            project_path = self.base_path / project_id
            
            if not project_path.exists():
                logger.warning(f"Project not found: {project_id}")
                return False
            
            # Calculate size before deletion
            size = self._get_directory_size(project_path)
            
            # Delete project directory
            shutil.rmtree(project_path)
            
            logger.info(f"Cleaned up project {project_id}: "
                       f"{self._format_size(size)} freed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up project {project_id}: {str(e)}")
            return False
    
    def cleanup_temp_files(self, temp_dir: str) -> int:
        """
        Clean up temporary files in directory
        
        Args:
            temp_dir: Temporary directory path
            
        Returns:
            Number of files deleted
        """
        try:
            temp_path = Path(temp_dir)
            count = 0
            
            if not temp_path.exists():
                return count
            
            for item in temp_path.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        count += 1
                except Exception as e:
                    logger.error(f"Error deleting {item}: {str(e)}")
            
            logger.info(f"Cleaned up {count} temporary items")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning temp files: {str(e)}")
            return 0
    
    def start_scheduled_cleanup(self, interval_hours: int = 1):
        """
        Start scheduled cleanup task
        
        Args:
            interval_hours: Hours between cleanup runs
        """
        if self.running:
            logger.warning("Scheduled cleanup already running")
            return
        
        self.running = True
        
        def cleanup_task():
            while self.running:
                try:
                    logger.info("Running scheduled cleanup...")
                    self.cleanup_old_projects()
                    
                    # Sleep for interval
                    time.sleep(interval_hours * 3600)
                    
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        self.cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"Started scheduled cleanup (interval: {interval_hours} hours)")
    
    def stop_scheduled_cleanup(self):
        """Stop scheduled cleanup task"""
        if not self.running:
            return
        
        self.running = False
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Stopped scheduled cleanup")
    
    def get_cleanup_candidates(self) -> List[Dict]:
        """
        Get list of projects eligible for cleanup
        
        Returns:
            List of dictionaries with project information
        """
        candidates = []
        
        if not self.base_path.exists():
            return candidates
        
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        for project_dir in self.base_path.iterdir():
            if not project_dir.is_dir():
                continue
            
            try:
                mtime = datetime.fromtimestamp(project_dir.stat().st_mtime)
                
                if mtime < cutoff_time:
                    size = self._get_directory_size(project_dir)
                    
                    candidates.append({
                        'project_id': project_dir.name,
                        'last_modified': mtime.isoformat(),
                        'size': size,
                        'size_formatted': self._format_size(size),
                        'age_hours': (datetime.now() - mtime).total_seconds() / 3600
                    })
            
            except Exception as e:
                logger.error(f"Error checking project {project_dir}: {str(e)}")
        
        return candidates
    
    def get_disk_usage(self) -> Dict:
        """
        Get disk usage statistics
        
        Returns:
            Dictionary with disk usage information
        """
        try:
            total_size = 0
            project_count = 0
            
            if self.base_path.exists():
                for project_dir in self.base_path.iterdir():
                    if project_dir.is_dir():
                        total_size += self._get_directory_size(project_dir)
                        project_count += 1
            
            # Get system disk usage
            stat = shutil.disk_usage(self.base_path)
            
            return {
                'total_projects': project_count,
                'total_size': total_size,
                'total_size_formatted': self._format_size(total_size),
                'disk_total': stat.total,
                'disk_used': stat.used,
                'disk_free': stat.free,
                'disk_percent': (stat.used / stat.total) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting disk usage: {str(e)}")
            return {}
    
    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of directory
        
        Args:
            directory: Directory path
            
        Returns:
            Size in bytes
        """
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        total_size += filepath.stat().st_size
                    except (OSError, FileNotFoundError):
                        continue
        except Exception as e:
            logger.error(f"Error calculating directory size: {str(e)}")
        
        return total_size
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def force_cleanup_all(self) -> Dict:
        """
        Force cleanup of all projects (emergency cleanup)
        
        Returns:
            Cleanup statistics
        """
        try:
            stats = {
                'projects_deleted': 0,
                'space_freed': 0,
                'errors': 0
            }
            
            if not self.base_path.exists():
                return stats
            
            for project_dir in self.base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                try:
                    size = self._get_directory_size(project_dir)
                    shutil.rmtree(project_dir)
                    
                    stats['projects_deleted'] += 1
                    stats['space_freed'] += size
                    
                except Exception as e:
                    logger.error(f"Error deleting {project_dir}: {str(e)}")
                    stats['errors'] += 1
            
            logger.warning(f"Force cleanup: {stats['projects_deleted']} projects deleted")
            return stats
            
        except Exception as e:
            logger.error(f"Error in force cleanup: {str(e)}")
            return {'error': str(e)}

