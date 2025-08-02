"""Helper functions for queue integration with Streamlit demos."""
import streamlit as st
from typing import Dict, Any, Optional

try:
    from queue_manager import QueueManager, JobType
    QUEUE_AVAILABLE = True
except ImportError:
    QUEUE_AVAILABLE = False


def add_generation_to_queue(
    job_type: str,
    parameters: Dict[str, Any],
    priority: int = 0
) -> Optional[str]:
    """Add a generation job to the queue.
    
    Args:
        job_type: "text-to-image" or "text-to-video"
        parameters: Generation parameters
        priority: Job priority (higher = more priority)
        
    Returns:
        Job ID if successful, None if failed
    """
    if not QUEUE_AVAILABLE:
        st.error("❌ Queue system not available")
        return None
    
    try:
        queue_manager = QueueManager()
        
        # Map job type string to enum
        job_type_enum = {
            "text-to-image": JobType.TEXT_TO_IMAGE,
            "text-to-video": JobType.TEXT_TO_VIDEO
        }.get(job_type)
        
        if not job_type_enum:
            st.error(f"❌ Unknown job type: {job_type}")
            return None
        
        # Create job
        job_id = queue_manager.create_job(job_type_enum, parameters, priority)
        
        return job_id
        
    except Exception as e:
        st.error(f"❌ Failed to add job to queue: {str(e)}")
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status dict or None if not found
    """
    if not QUEUE_AVAILABLE:
        return None
    
    try:
        queue_manager = QueueManager()
        job = queue_manager.get_job(job_id)
        
        if not job:
            return None
        
        return {
            "id": job.id,
            "type": job.type.value,
            "status": job.status.value,
            "progress": job.progress,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }
        
    except Exception as e:
        st.error(f"❌ Failed to get job status: {str(e)}")
        return None


def render_queue_submission_ui(job_type: str, parameters: Dict[str, Any]) -> bool:
    """Render UI for submitting jobs to queue vs running immediately.
    
    Args:
        job_type: "text-to-image" or "text-to-video"
        parameters: Generation parameters
        
    Returns:
        True if submitted to queue, False if should run immediately
    """
    if not QUEUE_AVAILABLE:
        return False
    
    st.subheader("🎯 Execution Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"🚀 Generate Now", type="primary", use_container_width=True):
            return False  # Run immediately
    
    with col2:
        if st.button(f"⏳ Add to Queue", use_container_width=True):
            # Add to queue
            with st.spinner("Adding to queue..."):
                job_id = add_generation_to_queue(job_type, parameters)
                
                if job_id:
                    st.success(f"✅ Added to queue! Job ID: `{job_id[:8]}...`")
                    st.info("💡 Check the **Queue Status** page to monitor progress")
                    
                    # Show link to queue page
                    st.markdown(f"[📋 View in Queue Dashboard](?page=Queue+Status)")
                    
            return True  # Added to queue
    
    return None  # No action taken


def render_job_status_widget(job_id: str):
    """Render a widget showing job status.
    
    Args:
        job_id: Job identifier
    """
    if not QUEUE_AVAILABLE or not job_id:
        return
    
    status = get_job_status(job_id)
    if not status:
        st.warning(f"⚠️ Job {job_id[:8]}... not found")
        return
    
    # Status display
    status_colors = {
        "queued": "🟡",
        "processing": "🔵",
        "completed": "🟢",
        "failed": "🔴",
        "cancelled": "⚫"
    }
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.write(f"{status_colors.get(status['status'], '⚪')} **Status**: {status['status'].title()}")
    
    with col2:
        if status['status'] == 'processing':
            st.progress(status['progress'] / 100)
            st.caption(f"{status['progress']}%")
        elif status['status'] == 'completed':
            st.progress(1.0)
            st.caption("100%")
    
    with col3:
        if status['status'] in ['queued', 'processing']:
            if st.button("⏸️ Cancel", key=f"cancel_{job_id}"):
                try:
                    queue_manager = QueueManager()
                    if queue_manager.cancel_job(job_id):
                        st.success("Cancelled!")
                        st.rerun()
                    else:
                        st.error("Failed to cancel")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Show result if completed
    if status['status'] == 'completed' and status['result']:
        st.success("✅ Generation completed!")
        with st.expander("📄 View Result", expanded=True):
            # Display result based on type
            result = status['result']
            if 'output' in result:
                output = result['output']
                
                # Handle images
                if 'images' in output and output['images']:
                    for i, img in enumerate(output['images']):
                        if img.get('type') == 'base64' and img.get('data'):
                            try:
                                import base64
                                import io
                                from PIL import Image
                                
                                img_bytes = base64.b64decode(img['data'])
                                pil_img = Image.open(io.BytesIO(img_bytes))
                                st.image(pil_img, caption=f"Generated Image {i+1}")
                            except Exception as e:
                                st.error(f"Failed to display image: {str(e)}")
                
                # Handle videos
                if 'videos' in output and output['videos']:
                    for i, video in enumerate(output['videos']):
                        if video.get('data'):
                            st.video(video['data'])
            
            # Show raw result
            with st.expander("🔍 Raw Result Data"):
                st.json(result)
    
    elif status['status'] == 'failed':
        st.error(f"❌ Generation failed: {status.get('error', 'Unknown error')}")


def get_queue_stats() -> Optional[Dict[str, Any]]:
    """Get queue statistics.
    
    Returns:
        Queue stats dict or None if not available
    """
    if not QUEUE_AVAILABLE:
        return None
    
    try:
        queue_manager = QueueManager()
        return queue_manager.get_queue_stats()
    except Exception:
        return None