import streamlit as st
import boto3
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from text_to_image_demo import render_text_to_image_demo
from text_to_video_demo import render_text_to_video_demo
try:
    from queue_manager import QueueManager, JobStatus, JobType
    QUEUE_AVAILABLE = True
except ImportError:
    QUEUE_AVAILABLE = False

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="AI Content Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #2c3e50;
        border-bottom: 2px solid #e74c3c;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .thumbnail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        padding: 20px 0;
    }
    .thumbnail-item {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .queue-item {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize S3 client
def get_s3_client():
    """Initialize S3 client with credentials from environment."""
    try:
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
    except Exception as e:
        st.error(f"Failed to initialize S3 client: {str(e)}")
        return None

def list_s3_objects(bucket_name, prefix=""):
    """List objects in S3 bucket with thumbnails."""
    s3_client = get_s3_client()
    if not s3_client:
        return []
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=100
        )
        return response.get('Contents', [])
    except Exception as e:
        st.error(f"Failed to list S3 objects: {str(e)}")
        return []

def generate_presigned_url(bucket_name, object_key, expiration=3600):
    """Generate presigned URL for S3 object."""
    s3_client = get_s3_client()
    if not s3_client:
        return None
    
    try:
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
    except Exception as e:
        st.error(f"Failed to generate presigned URL: {str(e)}")
        return None

def render_s3_dashboard():
    """Render S3 storage dashboard with thumbnails."""
    st.markdown('<h2 class="section-header">📁 S3 Storage Dashboard</h2>', unsafe_allow_html=True)
    
    # S3 Configuration
    bucket_name = st.text_input(
        "S3 Bucket Name:", 
        value=os.getenv('S3_BUCKET_NAME', ''),
        help="Enter your S3 bucket name"
    )
    
    if not bucket_name:
        st.warning("⚠️ Please configure your S3 bucket name")
        st.info("💡 Set S3_BUCKET_NAME environment variable or enter it above")
        return
    
    # Filter options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        prefix_filter = st.text_input("Filter by prefix:", placeholder="folder/subfolder/")
    
    with col2:
        file_type = st.selectbox("File type:", ["All", "Images", "Videos", "Other"])
    
    with col3:
        if st.button("🔄 Refresh", type="primary"):
            st.rerun()
    
    # List S3 objects
    with st.spinner("Loading S3 objects..."):
        objects = list_s3_objects(bucket_name, prefix_filter)
    
    if not objects:
        st.info("📂 No objects found in the specified bucket/prefix")
        return
    
    # Filter by file type
    if file_type != "All":
        if file_type == "Images":
            objects = [obj for obj in objects if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))]
        elif file_type == "Videos":
            objects = [obj for obj in objects if obj['Key'].lower().endswith(('.mp4', '.avi', '.mov', '.webm'))]
        else:  # Other
            objects = [obj for obj in objects if not obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.avi', '.mov', '.webm'))]
    
    # Display statistics
    total_size = sum(obj.get('Size', 0) for obj in objects)
    st.metric("Total Objects", len(objects))
    st.metric("Total Size", f"{total_size / (1024*1024):.2f} MB")
    
    # Display objects in grid
    if objects:
        cols = st.columns(4)
        for i, obj in enumerate(objects):
            with cols[i % 4]:
                object_key = obj['Key']
                file_size = obj.get('Size', 0)
                last_modified = obj.get('LastModified', datetime.now())
                
                # Generate presigned URL
                url = generate_presigned_url(bucket_name, object_key)
                
                # Display thumbnail or file info
                if object_key.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    if url:
                        st.image(url, caption=os.path.basename(object_key), use_column_width=True)
                    else:
                        st.write(f"🖼️ {os.path.basename(object_key)}")
                elif object_key.lower().endswith(('.mp4', '.avi', '.mov', '.webm')):
                    if url:
                        st.video(url)
                        st.caption(os.path.basename(object_key))
                    else:
                        st.write(f"🎥 {os.path.basename(object_key)}")
                else:
                    st.write(f"📄 {os.path.basename(object_key)}")
                
                # File details
                st.caption(f"Size: {file_size / 1024:.1f} KB")
                st.caption(f"Modified: {last_modified.strftime('%Y-%m-%d %H:%M')}")
                
                # Download button
                if url:
                    st.link_button("📥 Download", url)

def render_queue_dashboard():
    """Render generation queue dashboard."""
    st.markdown('<h2 class="section-header">⏳ Generation Queue</h2>', unsafe_allow_html=True)
    
    if not QUEUE_AVAILABLE:
        st.error("❌ Queue system not available")
        st.info("To enable queue functionality:")
        st.code("""
# Install Python Redis client
pip install redis

# Set up Upstash Redis environment variables:
export UPSTASH_REDIS_REST_URL="your_upstash_redis_url"
export UPSTASH_REDIS_REST_TOKEN="your_upstash_redis_token"
        """)
        return
    
    try:
        # Initialize queue manager
        queue_manager = QueueManager()
        
        # Auto-refresh toggle
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=True)
        with col2:
            if st.button("🔄 Refresh Now", type="primary"):
                st.rerun()
        with col3:
            if st.button("🧹 Cleanup Old Jobs"):
                cleaned = queue_manager.cleanup_old_jobs()
                st.success(f"Cleaned up {cleaned} old jobs")
        
        # Get queue statistics
        stats = queue_manager.get_queue_stats()
        
        # Display statistics
        st.subheader("📊 Queue Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Jobs", stats["total"])
        with col2:
            st.metric("Queued", stats["queued"], f"Queue: {stats['queue_length']}")
        with col3:
            st.metric("Processing", stats["processing"])
        with col4:
            st.metric("Completed", stats["completed"])
        with col5:
            st.metric("Active Workers", stats["active_workers"])
        
        # Additional stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Failed", stats["failed"])
        with col2:
            st.metric("Cancelled", stats["cancelled"])
        
        # Get recent jobs
        jobs = queue_manager.list_jobs(limit=50)
        
        if not jobs:
            st.info("📂 No jobs found")
            return
        
        # Filter options
        st.subheader("🔍 Filters")
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            status_filter = st.selectbox(
                "Filter by status:",
                ["All"] + [status.value.title() for status in JobStatus]
            )
        
        with filter_col2:
            type_filter = st.selectbox(
                "Filter by type:",
                ["All", "Text-to-Image", "Text-to-Video"]
            )
        
        # Apply filters
        filtered_jobs = jobs
        if status_filter != "All":
            filtered_jobs = [job for job in filtered_jobs if job.status.value == status_filter.lower()]
        
        if type_filter != "All":
            type_mapping = {
                "Text-to-Image": JobType.TEXT_TO_IMAGE,
                "Text-to-Video": JobType.TEXT_TO_VIDEO
            }
            filtered_jobs = [job for job in filtered_jobs if job.type == type_mapping[type_filter]]
        
        # Display jobs
        st.subheader(f"📋 Recent Jobs ({len(filtered_jobs)})")
        
        for job in filtered_jobs:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    job_type_display = "Text-to-Image" if job.type == JobType.TEXT_TO_IMAGE else "Text-to-Video"
                    st.write(f"**{job_type_display}** - `{job.id[:8]}...`")
                    
                    # Show prompt if available
                    prompt = job.parameters.get('prompt') or job.parameters.get('positive_prompt', 'No prompt')
                    st.caption(prompt[:80] + "..." if len(prompt) > 80 else prompt)
                
                with col2:
                    status_colors = {
                        JobStatus.QUEUED: "🟡",
                        JobStatus.PROCESSING: "🔵",
                        JobStatus.COMPLETED: "🟢", 
                        JobStatus.FAILED: "🔴",
                        JobStatus.CANCELLED: "⚫"
                    }
                    st.write(f"{status_colors.get(job.status, '⚪')} {job.status.value.title()}")
                
                with col3:
                    if job.status == JobStatus.PROCESSING:
                        st.progress(job.progress / 100)
                        st.caption(f"{job.progress}%")
                    elif job.status == JobStatus.COMPLETED:
                        st.progress(1.0)
                        st.caption("100%")
                    else:
                        st.caption("—")
                
                with col4:
                    created_time = datetime.fromtimestamp(job.created_at)
                    st.caption(f"Created: {created_time.strftime('%H:%M:%S')}")
                    
                    if job.completed_at:
                        completed_time = datetime.fromtimestamp(job.completed_at)
                        duration = job.completed_at - job.created_at
                        st.caption(f"Duration: {duration:.1f}s")
                
                with col5:
                    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
                        if st.button("⏸️ Cancel", key=f"cancel_{job.id}"):
                            if queue_manager.cancel_job(job.id):
                                st.success(f"Cancelled job {job.id[:8]}")
                                st.rerun()
                            else:
                                st.error("Failed to cancel job")
                    
                    elif job.status == JobStatus.COMPLETED:
                        with st.expander("📄 Result", expanded=False):
                            if job.result:
                                st.json(job.result)
                    
                    elif job.status == JobStatus.FAILED:
                        if job.error:
                            st.error(f"Error: {job.error[:50]}...")
                
                st.divider()
        
        # Auto-refresh
        if auto_refresh:
            time.sleep(5)
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Queue system error: {str(e)}")
        st.info("Check your Upstash Redis credentials and connection.")

# Main app
st.markdown('<h1 class="main-header">🎨 AI Content Generator</h1>', unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.header("🎛️ Navigation")
    
    page = st.selectbox(
        "Choose a page:",
        ["S3 Dashboard", "Text-to-Image", "Text-to-Video", "Queue Status"]
    )
    
    st.subheader("⚙️ Settings")
    
    # Environment status
    st.write("**Environment Status:**")
    env_vars = [
        'RUNPOD_API_KEY', 
        'AWS_ACCESS_KEY_ID', 
        'AWS_SECRET_ACCESS_KEY', 
        'S3_BUCKET_NAME',
        'UPSTASH_REDIS_REST_URL',
        'UPSTASH_REDIS_REST_TOKEN'
    ]
    for var in env_vars:
        if os.getenv(var):
            st.success(f"✅ {var}")
        else:
            st.error(f"❌ {var}")
    
    st.subheader("📊 Quick Stats")
    st.metric("Uptime", "99.9%")
    st.metric("Total Generations", "1,234")

# Page routing
if page == "S3 Dashboard":
    render_s3_dashboard()
elif page == "Text-to-Image":
    render_text_to_image_demo()
elif page == "Text-to-Video":
    render_text_to_video_demo()
elif page == "Queue Status":
    render_queue_dashboard()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #7f8c8d; padding: 1rem;'>
        <p>Built with ❤️ using Streamlit | AI Content Generator v1.0</p>
    </div>
    """,
    unsafe_allow_html=True
)