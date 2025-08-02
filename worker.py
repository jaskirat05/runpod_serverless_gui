"""Background worker for processing generation jobs."""
import time
import os
import uuid
import logging
from typing import Dict, Any
from queue_manager import QueueManager, JobStatus, JobType
from workflows.text_to_image import TextToImageWorkflow
from workflows.text_to_video import TextToVideoWorkflow
from config import get_default_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GenerationWorker:
    """Background worker for processing generation jobs."""
    
    def __init__(self, worker_id: str = None, redis_url: str = None, redis_token: str = None):
        """Initialize the worker.
        
        Args:
            worker_id: Unique worker identifier
            redis_url: Upstash Redis URL (optional, will use env var)
            redis_token: Upstash Redis token (optional, will use env var)
        """
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.queue_manager = QueueManager(redis_url, redis_token)
        self.running = False
        
        # Initialize RunPod configuration
        self.config = get_default_config()
        if not self.config:
            raise ValueError("RunPod configuration not found. Check environment variables.")
            
        logger.info(f"Worker {self.worker_id} initialized with Upstash Redis")
    
    def start(self):
        """Start the worker loop."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        try:
            while self.running:
                # Get next job from queue
                job = self.queue_manager.get_next_job(self.worker_id)
                
                if job:
                    logger.info(f"Processing job {job.id} of type {job.type.value}")
                    try:
                        self._process_job(job)
                    except Exception as e:
                        logger.error(f"Failed to process job {job.id}: {str(e)}")
                        self.queue_manager.fail_job(job.id, str(e), self.worker_id)
                else:
                    # No jobs available, sleep briefly
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} stopping...")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {str(e)}")
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")
    
    def stop(self):
        """Stop the worker."""
        self.running = False
    
    def _process_job(self, job):
        """Process a generation job.
        
        Args:
            job: GenerationJob to process
        """
        try:
            # Update progress to show job started
            self.queue_manager.update_job_progress(job.id, 10, self.worker_id)
            
            if job.type == JobType.TEXT_TO_IMAGE:
                result = self._process_text_to_image(job)
            elif job.type == JobType.TEXT_TO_VIDEO:
                result = self._process_text_to_video(job)
            else:
                raise ValueError(f"Unknown job type: {job.type}")
            
            # Mark job as completed
            self.queue_manager.complete_job(job.id, result, self.worker_id)
            logger.info(f"Job {job.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job.id} failed: {str(e)}")
            self.queue_manager.fail_job(job.id, str(e), self.worker_id)
    
    async def _process_text_to_image(self, job) -> Dict[str, Any]:
        """Process text-to-image generation job.
        
        Args:
            job: GenerationJob for text-to-image
            
        Returns:
            Generation result
        """
        # Initialize workflow
        workflow = TextToImageWorkflow(
            endpoint_id=self.config.text_to_image_endpoint,
            api_key=self.config.api_key
        )
        
        # Update progress
        self.queue_manager.update_job_progress(job.id, 10, self.worker_id)
        
        # Extract parameters
        params = job.parameters
        
        # Submit job to RunPod (async)
        self.queue_manager.update_job_progress(job.id, 25, self.worker_id)
        runpod_result = await workflow.submit_job(**params)
        
        if runpod_result.status.value == "FAILED":
            raise Exception(f"Failed to submit job: {runpod_result.error}")
        
        runpod_job_id = runpod_result.id
        logger.info(f"Submitted RunPod job {runpod_job_id} for queue job {job.id}")
        
        # Poll for completion
        self.queue_manager.update_job_progress(job.id, 50, self.worker_id)
        final_result = await workflow._poll_job_status(runpod_job_id, max_wait_time=600, poll_interval=5)
        
        # Update progress as we poll
        start_time = time.time()
        max_wait = 600  # 10 minutes
        
        while final_result.status.value in ["PENDING", "RUNNING"]:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise Exception("Job timed out after 10 minutes")
            
            # Update progress based on elapsed time (rough estimate)
            progress = min(90, 50 + int((elapsed / max_wait) * 40))
            self.queue_manager.update_job_progress(job.id, progress, self.worker_id)
            
            await asyncio.sleep(5)
            final_result = await workflow.get_job_status(runpod_job_id)
        
        # Final progress update
        self.queue_manager.update_job_progress(job.id, 95, self.worker_id)
        
        if final_result.status.value == "COMPLETED":
            return {
                "status": "completed",
                "output": final_result.output,
                "execution_time": final_result.execution_time,
                "runpod_job_id": runpod_job_id
            }
        else:
            raise Exception(f"Generation failed: {final_result.error}")
    
    async def _process_text_to_video(self, job) -> Dict[str, Any]:
        """Process text-to-video generation job.
        
        Args:
            job: GenerationJob for text-to-video
            
        Returns:
            Generation result
        """
        # Initialize workflow  
        workflow = TextToVideoWorkflow(
            endpoint_id=self.config.text_to_image_endpoint,  # Using same endpoint for now
            api_key=self.config.api_key
        )
        
        # Update progress
        self.queue_manager.update_job_progress(job.id, 10, self.worker_id)
        
        # Extract parameters
        params = job.parameters
        
        # Submit job to RunPod (async)
        self.queue_manager.update_job_progress(job.id, 25, self.worker_id)
        runpod_result = await workflow.submit_job(**params)
        
        if runpod_result.status.value == "FAILED":
            raise Exception(f"Failed to submit job: {runpod_result.error}")
        
        runpod_job_id = runpod_result.id
        logger.info(f"Submitted RunPod job {runpod_job_id} for queue job {job.id}")
        
        # Poll for completion
        self.queue_manager.update_job_progress(job.id, 50, self.worker_id)
        
        # Update progress as we poll
        start_time = time.time()
        max_wait = 900  # 15 minutes for video (longer than images)
        
        while True:
            final_result = await workflow.get_job_status(runpod_job_id)
            
            if final_result.status.value not in ["PENDING", "RUNNING"]:
                break
                
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise Exception("Job timed out after 15 minutes")
            
            # Update progress based on elapsed time (rough estimate)
            progress = min(90, 50 + int((elapsed / max_wait) * 40))
            self.queue_manager.update_job_progress(job.id, progress, self.worker_id)
            
            await asyncio.sleep(10)  # Poll less frequently for video
        
        # Final progress update
        self.queue_manager.update_job_progress(job.id, 95, self.worker_id)
        
        if final_result.status.value == "COMPLETED":
            return {
                "status": "completed", 
                "output": final_result.output,
                "execution_time": final_result.execution_time,
                "runpod_job_id": runpod_job_id
            }
        else:
            raise Exception(f"Generation failed: {final_result.error}")


def main():
    """Main worker entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generation worker for Upstash Redis")
    parser.add_argument("--worker-id", help="Worker ID")
    parser.add_argument("--redis-url", help="Upstash Redis URL (optional, uses env var)")
    parser.add_argument("--redis-token", help="Upstash Redis token (optional, uses env var)")
    
    args = parser.parse_args()
    
    worker = GenerationWorker(
        worker_id=args.worker_id,
        redis_url=args.redis_url,
        redis_token=args.redis_token
    )
    
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()