"""Base workflow class for RunPod integrations."""
import asyncio
import httpx
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    id: str
    status: WorkflowStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: Optional[str] = None


class Workflow(ABC):
    """Abstract base class for RunPod workflows."""
    
    def __init__(self, endpoint_id: str, api_key: str):
        """Initialize workflow with RunPod credentials.
        
        Args:
            endpoint_id: RunPod serverless endpoint ID
            api_key: RunPod API key
        """
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    @abstractmethod
    def prepare_input(self, **kwargs) -> Dict[str, Any]:
        """Prepare input data for the workflow.
        
        Args:
            **kwargs: Workflow-specific parameters
            
        Returns:
            Dict containing the prepared input for RunPod
        """
        pass
    
    @abstractmethod
    def process_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw output from RunPod.
        
        Args:
            raw_output: Raw response from RunPod
            
        Returns:
            Processed output data
        """
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters.
        
        Args:
            **kwargs: Input parameters to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        pass
    
    async def submit_job(self, **kwargs) -> WorkflowResult:
        """Submit job to RunPod queue (async, non-blocking).
        
        Args:
            **kwargs: Workflow-specific parameters
            
        Returns:
            WorkflowResult with job ID and status
        """
        try:
            # Validate input
            if not self.validate_input(**kwargs):
                return WorkflowResult(
                    id="",
                    status=WorkflowStatus.FAILED,
                    error="Invalid input parameters"
                )
            
            # Prepare input
            input_data = self.prepare_input(**kwargs)
            
            # Submit job to /run endpoint (async)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/run",
                    headers=self.headers,
                    json={"input": input_data}
                )
                response.raise_for_status()
                
                result_data = response.json()
                
                # Return job submission result
                return WorkflowResult(
                    id=result_data.get("id", ""),
                    status=WorkflowStatus.PENDING,
                    created_at=result_data.get("created_at")
                )
                
        except httpx.HTTPStatusError as e:
            return WorkflowResult(
                id="",
                status=WorkflowStatus.FAILED,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return WorkflowResult(
                id="",
                status=WorkflowStatus.FAILED,
                error=f"Unexpected error: {str(e)}"
            )

    async def run_async(self, **kwargs) -> WorkflowResult:
        """Run the workflow asynchronously.
        
        Args:
            **kwargs: Workflow-specific parameters
            
        Returns:
            WorkflowResult with execution details
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(**kwargs):
                return WorkflowResult(
                    id="",
                    status=WorkflowStatus.FAILED,
                    error="Invalid input parameters"
                )
            
            # Prepare input
            input_data = self.prepare_input(**kwargs)
            
            # Submit job to /runsync endpoint
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/runsync",
                    headers=self.headers,
                    json={"input": input_data}
                )
                response.raise_for_status()
                
                result_data = response.json()
                
                # For /runsync, we get the result directly
                if result_data.get("status") == "COMPLETED":
                    output = result_data.get("output")
                    if output:
                        processed_output = self.process_output(output)
                        return WorkflowResult(
                            id=result_data.get("id", "sync-request"),
                            status=WorkflowStatus.COMPLETED,
                            output=processed_output,
                            execution_time=time.time() - start_time
                        )
                    else:
                        return WorkflowResult(
                            id=result_data.get("id", "sync-request"),
                            status=WorkflowStatus.FAILED,
                            error="No output received from RunPod",
                            execution_time=time.time() - start_time
                        )
                else:
                    return WorkflowResult(
                        id=result_data.get("id", "sync-request"),
                        status=WorkflowStatus.FAILED,
                        error=result_data.get("error", "Unknown error"),
                        execution_time=time.time() - start_time
                    )
                
        except httpx.HTTPStatusError as e:
            return WorkflowResult(
                id="",
                status=WorkflowStatus.FAILED,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return WorkflowResult(
                id="",
                status=WorkflowStatus.FAILED,
                error=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def run_sync(self, **kwargs) -> WorkflowResult:
        """Run the workflow synchronously.
        
        Args:
            **kwargs: Workflow-specific parameters
            
        Returns:
            WorkflowResult with execution details
        """
        return asyncio.run(self.run_async(**kwargs))
    
    async def _poll_job_status(self, job_id: str, max_wait_time: int = 300, poll_interval: int = 2) -> WorkflowResult:
        """Poll job status until completion or timeout.
        
        Args:
            job_id: RunPod job ID
            max_wait_time: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            WorkflowResult with final status
        """
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() - start_time < max_wait_time:
                try:
                    response = await client.get(
                        f"{self.base_url}/status/{job_id}",
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    status_data = response.json()
                    status = status_data.get("status", "UNKNOWN")
                    
                    if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                        if status == "COMPLETED":
                            output = status_data.get("output")
                            if output:
                                processed_output = self.process_output(output)
                                return WorkflowResult(
                                    id=job_id,
                                    status=WorkflowStatus.COMPLETED,
                                    output=processed_output,
                                    created_at=status_data.get("created_at")
                                )
                            else:
                                return WorkflowResult(
                                    id=job_id,
                                    status=WorkflowStatus.FAILED,
                                    error="No output received from RunPod"
                                )
                        else:
                            return WorkflowResult(
                                id=job_id,
                                status=WorkflowStatus(status),
                                error=status_data.get("error", f"Job {status.lower()}")
                            )
                    
                    # Job still running, wait before next poll
                    await asyncio.sleep(poll_interval)
                    
                except httpx.HTTPStatusError as e:
                    return WorkflowResult(
                        id=job_id,
                        status=WorkflowStatus.FAILED,
                        error=f"Status check failed: {e.response.status_code}"
                    )
        
        # Timeout reached
        return WorkflowResult(
            id=job_id,
            status=WorkflowStatus.FAILED,
            error=f"Job timed out after {max_wait_time} seconds"
        )
    
    async def get_job_status(self, job_id: str) -> WorkflowResult:
        """Get current status of a job.
        
        Args:
            job_id: RunPod job ID
            
        Returns:
            Current WorkflowResult
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                status_data = response.json()
                status = WorkflowStatus(status_data.get("status", "PENDING"))
                
                result = WorkflowResult(
                    id=job_id,
                    status=status,
                    created_at=status_data.get("created_at")
                )
                
                if status == WorkflowStatus.COMPLETED:
                    output = status_data.get("output")
                    if output:
                        result.output = self.process_output(output)
                elif status == WorkflowStatus.FAILED:
                    result.error = status_data.get("error", "Job failed")
                
                return result
                
        except Exception as e:
            return WorkflowResult(
                id=job_id,
                status=WorkflowStatus.FAILED,
                error=f"Failed to get job status: {str(e)}"
            )
