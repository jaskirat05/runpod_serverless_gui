"""Queue management system for AI content generation using Upstash Redis."""
import redis
import json
import uuid
import time
import os
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


class JobStatus(Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Job type enumeration."""
    TEXT_TO_IMAGE = "text_to_image"
    TEXT_TO_VIDEO = "text_to_video"


@dataclass
class GenerationJob:
    """Generation job data structure."""
    id: str
    type: JobType
    parameters: Dict[str, Any]
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    worker_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class QueueManager:
    """Upstash Redis-based queue manager for generation jobs."""
    
    def __init__(self, redis_url=None, redis_token=None):
        """Initialize queue manager with Upstash Redis connection.
        
        Args:
            redis_url: Upstash Redis URL (or from UPSTASH_REDIS_REST_URL env var)
            redis_token: Upstash Redis token (or from UPSTASH_REDIS_REST_TOKEN env var)
        """
        # Get Upstash credentials from environment or parameters
        redis_url = redis_url or os.getenv('UPSTASH_REDIS_REST_URL')
        redis_token = redis_token or os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if not redis_url or not redis_token:
            raise ValueError(
                "Upstash Redis credentials required. Set UPSTASH_REDIS_REST_URL and "
                "UPSTASH_REDIS_REST_TOKEN environment variables or pass them as parameters."
            )
        
        # Parse URL to get connection details
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        
        # Initialize Redis client for Upstash
        self.redis_client = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=redis_token,
            ssl=True,  # Upstash uses SSL
            ssl_cert_reqs=None,
            decode_responses=True,
            socket_connect_timeout=30,
            socket_timeout=30
        )
        
        self.job_queue_key = "generation_jobs:queue"
        self.job_data_key = "generation_jobs:data"
        self.job_status_key = "generation_jobs:status"
        self.worker_heartbeat_key = "generation_jobs:workers"
        
        # Test connection
        try:
            self.redis_client.ping()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Upstash Redis: {str(e)}")
        
    def create_job(self, job_type: JobType, parameters: Dict[str, Any], priority: int = 0) -> str:
        """Create a new generation job and add it to the queue.
        
        Args:
            job_type: Type of generation job
            parameters: Generation parameters
            priority: Job priority (higher = more priority)
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = GenerationJob(
            id=job_id,
            type=job_type,
            parameters=parameters
        )
        
        # Store job data
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        # Add to priority queue (higher score = higher priority)
        self.redis_client.zadd(
            self.job_queue_key,
            {job_id: priority}
        )
        
        return job_id
    
    def get_next_job(self, worker_id: str) -> Optional[GenerationJob]:
        """Get the next job from the queue for processing.
        
        Args:
            worker_id: Unique worker identifier
            
        Returns:
            Next job to process or None if queue is empty
        """
        # Get highest priority job
        job_data = self.redis_client.zpopmax(self.job_queue_key)
        if not job_data:
            return None
            
        job_id = job_data[0][0]
        
        # Get job details
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return None
            
        job_dict = json.loads(job_json)
        job = GenerationJob(**job_dict)
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = time.time()
        job.worker_id = worker_id
        
        # Save updated job
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        # Update worker heartbeat
        self.redis_client.hset(
            self.worker_heartbeat_key,
            worker_id,
            time.time()
        )
        
        return job
    
    def update_job_progress(self, job_id: str, progress: int, worker_id: str) -> bool:
        """Update job progress.
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            worker_id: Worker identifier
            
        Returns:
            True if update successful
        """
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return False
            
        job_dict = json.loads(job_json)
        job = GenerationJob(**job_dict)
        
        if job.worker_id != worker_id:
            return False
            
        job.progress = max(0, min(100, progress))
        
        # Save updated job
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        # Update worker heartbeat
        self.redis_client.hset(
            self.worker_heartbeat_key,
            worker_id,
            time.time()
        )
        
        return True
    
    def complete_job(self, job_id: str, result: Dict[str, Any], worker_id: str) -> bool:
        """Mark job as completed with result.
        
        Args:
            job_id: Job identifier
            result: Generation result
            worker_id: Worker identifier
            
        Returns:
            True if update successful
        """
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return False
            
        job_dict = json.loads(job_json)
        job = GenerationJob(**job_dict)
        
        if job.worker_id != worker_id:
            return False
            
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.result = result
        job.completed_at = time.time()
        
        # Save updated job
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        return True
    
    def fail_job(self, job_id: str, error: str, worker_id: str) -> bool:
        """Mark job as failed with error.
        
        Args:
            job_id: Job identifier  
            error: Error message
            worker_id: Worker identifier
            
        Returns:
            True if update successful
        """
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return False
            
        job_dict = json.loads(job_json)
        job = GenerationJob(**job_dict)
        
        if job.worker_id != worker_id:
            return False
            
        job.status = JobStatus.FAILED
        job.error = error
        job.completed_at = time.time()
        
        # Save updated job
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancellation successful
        """
        # Remove from queue if still queued
        self.redis_client.zrem(self.job_queue_key, job_id)
        
        # Update job status
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return False
            
        job_dict = json.loads(job_json)
        job = GenerationJob(**job_dict)
        
        job.status = JobStatus.CANCELLED
        job.completed_at = time.time()
        
        # Save updated job
        self.redis_client.hset(
            self.job_data_key,
            job_id,
            json.dumps(asdict(job))
        )
        
        return True
    
    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get job details by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job details or None if not found
        """
        job_json = self.redis_client.hget(self.job_data_key, job_id)
        if not job_json:
            return None
            
        job_dict = json.loads(job_json)
        return GenerationJob(**job_dict)
    
    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[GenerationJob]:
        """List jobs with optional status filter.
        
        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs
        """
        # Get all job data
        all_jobs = self.redis_client.hgetall(self.job_data_key)
        jobs = []
        
        for job_json in all_jobs.values():
            job_dict = json.loads(job_json)
            job = GenerationJob(**job_dict)
            
            if status is None or job.status == status:
                jobs.append(job)
                
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return jobs[:limit]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        all_jobs = self.redis_client.hgetall(self.job_data_key)
        
        stats = {
            "total": len(all_jobs),
            "queued": 0,
            "processing": 0, 
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "queue_length": self.redis_client.zcard(self.job_queue_key),
            "active_workers": self._get_active_workers_count()
        }
        
        for job_json in all_jobs.values():
            job_dict = json.loads(job_json)
            job = GenerationJob(**job_dict)
            stats[job.status.value] += 1
            
        return stats
    
    def _get_active_workers_count(self) -> int:
        """Get count of active workers (heartbeat within 60 seconds)."""
        current_time = time.time()
        heartbeats = self.redis_client.hgetall(self.worker_heartbeat_key)
        
        active_count = 0
        for worker_id, last_heartbeat in heartbeats.items():
            if current_time - float(last_heartbeat) < 60:  # 60 seconds timeout
                active_count += 1
                
        return active_count
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        all_jobs = self.redis_client.hgetall(self.job_data_key)
        
        cleaned_count = 0
        for job_id, job_json in all_jobs.items():
            job_dict = json.loads(job_json)
            job = GenerationJob(**job_dict)
            
            # Clean up old completed/failed/cancelled jobs
            if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                job.completed_at and job.completed_at < cutoff_time):
                
                self.redis_client.hdel(self.job_data_key, job_id)
                cleaned_count += 1
                
        return cleaned_count