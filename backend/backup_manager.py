import os
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class BackupManager:
    """Database backup and restore utilities"""
    
    def __init__(self, mongodb_uri: str, backup_dir: str = "./backups"):
        self.mongodb_uri = mongodb_uri
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    async def create_backup(self, database_name: str = "postnatal_stories") -> Dict:
        """Create MongoDB backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            
            # Use mongodump command
            cmd = [
                "mongodump",
                "--uri", self.mongodb_uri,
                "--db", database_name,
                "--out", backup_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Backup created successfully: {backup_path}")
                return {
                    "success": True,
                    "backup_path": backup_path,
                    "timestamp": timestamp,
                    "message": "Backup created successfully"
                }
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "Backup failed"
                }
                
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Backup failed"
            }
    
    async def restore_backup(self, backup_path: str, database_name: str = "postnatal_stories") -> Dict:
        """Restore MongoDB backup"""
        try:
            cmd = [
                "mongorestore",
                "--uri", self.mongodb_uri,
                "--db", database_name,
                "--drop",  # Drop existing collections
                os.path.join(backup_path, database_name)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Restore completed successfully from: {backup_path}")
                return {
                    "success": True,
                    "message": "Database restored successfully"
                }
            else:
                logger.error(f"Restore failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "Restore failed"
                }
                
        except Exception as e:
            logger.error(f"Restore error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Restore failed"
            }
    
    def list_backups(self) -> List[Dict]:
        """List available backups"""
        backups = []
        try:
            for item in os.listdir(self.backup_dir):
                if item.startswith("backup_"):
                    backup_path = os.path.join(self.backup_dir, item)
                    if os.path.isdir(backup_path):
                        stat = os.stat(backup_path)
                        backups.append({
                            "name": item,
                            "path": backup_path,
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "size_mb": round(self._get_directory_size(backup_path) / (1024*1024), 2)
                        })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 30) -> Dict:
        """Remove backups older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            removed_count = 0
            
            for backup in self.list_backups():
                backup_date = datetime.fromisoformat(backup["created"])
                if backup_date < cutoff_date:
                    backup_path = backup["path"]
                    subprocess.run(["rm", "-rf", backup_path])
                    removed_count += 1
                    logger.info(f"Removed old backup: {backup['name']}")
            
            return {
                "success": True,
                "removed_count": removed_count,
                "message": f"Cleaned up {removed_count} old backups"
            }
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Cleanup failed"
            }
    
    def _get_directory_size(self, path: str) -> int:
        """Get directory size in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total += os.path.getsize(filepath)
        return total

# Backup scheduler
class BackupScheduler:
    """Automated backup scheduling"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.running = False
    
    async def start_daily_backup(self, hour: int = 2):
        """Start daily backup at specified hour"""
        self.running = True
        logger.info(f"Starting daily backup scheduler at {hour}:00")
        
        while self.running:
            now = datetime.now()
            next_backup = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # If we've passed today's backup time, schedule for tomorrow
            if now >= next_backup:
                next_backup += timedelta(days=1)
            
            # Wait until backup time
            wait_seconds = (next_backup - now).total_seconds()
            logger.info(f"Next backup scheduled for: {next_backup}")
            
            await asyncio.sleep(wait_seconds)
            
            if self.running:  # Check if still running after sleep
                logger.info("Starting scheduled backup...")
                result = await self.backup_manager.create_backup()
                
                if result["success"]:
                    logger.info("Scheduled backup completed successfully")
                    # Cleanup old backups
                    self.backup_manager.cleanup_old_backups()
                else:
                    logger.error(f"Scheduled backup failed: {result['message']}")
    
    def stop(self):
        """Stop the backup scheduler"""
        self.running = False
        logger.info("Backup scheduler stopped")

# Add backup endpoints to your FastAPI app
"""
# Add these to your main.py or create backup_routes.py

from fastapi import APIRouter, Depends, HTTPException
from routers.auth import get_current_active_user

backup_router = APIRouter(prefix="/backup", tags=["backup"])
backup_manager = BackupManager(MONGODB_URI)

@backup_router.post("/create")
async def create_backup(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await backup_manager.create_backup()
    return result

@backup_router.get("/list")
async def list_backups(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {"backups": backup_manager.list_backups()}

@backup_router.post("/cleanup")
async def cleanup_backups(keep_days: int = 30, current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = backup_manager.cleanup_old_backups(keep_days)
    return result

# Add to main.py
app.include_router(backup_router)
"""