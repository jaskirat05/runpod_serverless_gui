"""Text-to-Image demo page for Streamlit app."""
import streamlit as st
import io
import base64
from PIL import Image
from dotenv import load_dotenv
from workflows.text_to_image import TextToImageWorkflow
from config import get_default_config
import time

# Load environment variables
load_dotenv()


def decode_base64_image(base64_string: str) -> Image.Image:
    """Decode base64 string to PIL Image."""
    if base64_string.startswith('data:image/'):
        base64_string = base64_string.split(',', 1)[1]
    
    image_bytes = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_bytes))


def render_text_to_image_demo():
    """Render the text-to-image demo interface."""
    st.header("🎨 Text-to-Image Generator")
    st.write("Generate stunning images from text descriptions using AI models on RunPod.")
    
    # Configuration section
    with st.expander("⚙️ RunPod Configuration", expanded=False):
        st.write("**Setup Instructions:**")
        st.write("1. Get your RunPod API key from [RunPod Console](https://www.runpod.io/console)")
        st.write("2. Deploy a text-to-image serverless endpoint")
        st.write("3. Enter your credentials below or set environment variables")
        
        col1, col2 = st.columns(2)
        
        with col1:
            api_key = st.text_input(
                "RunPod API Key:",
                type="password",
                placeholder="Enter your RunPod API key",
                help="Your RunPod API key from the console"
            )
        
        with col2:
            endpoint_id = st.text_input(
                "Text-to-Image Endpoint ID:",
                placeholder="Enter your endpoint ID",
                help="The endpoint ID for your text-to-image deployment"
            )
        
        # Try to load from environment if not provided
        if not api_key or not endpoint_id:
            config = get_default_config()
            if config:
                if not api_key:
                    api_key = config.api_key
                    st.success("✅ API key loaded from environment")
                if not endpoint_id:
                    endpoint_id = config.text_to_image_endpoint
                    st.success("✅ Endpoint ID loaded from environment")
    
    # Main interface
    if not api_key or not endpoint_id:
        st.warning("⚠️ Please configure your RunPod credentials above to use the text-to-image generator.")
        st.info("💡 You can also set environment variables: `RUNPOD_API_KEY` and `RUNPOD_TEXT_TO_IMAGE_ENDPOINT`")
        return
    
    # Input section
    st.subheader("📝 Generation Parameters")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        prompt = st.text_area(
            "Prompt:",
            placeholder="Describe the image you want to generate...",
            help="Detailed description of the image you want to create",
            height=100
        )
        
        negative_prompt = st.text_area(
            "Negative Prompt (Optional):",
            placeholder="What to avoid in the image...",
            help="Describe what you don't want in the image",
            height=60
        )
    
    with col2:
        st.write("**Image Settings**")
        
        col_w, col_h = st.columns(2)
        with col_w:
            width = st.selectbox("Width:", [512, 768, 1024], index=0)
        with col_h:
            height = st.selectbox("Height:", [512, 768, 1024], index=0)
        
        steps = st.slider("Steps:", 10, 50, 20, help="More steps = higher quality but slower")
        guidance_scale = st.slider("Guidance Scale:", 1.0, 20.0, 7.5, 0.5, help="How closely to follow the prompt")
        
        num_images = st.selectbox("Number of Images:", [1, 2, 3, 4], index=0)
        
        # Advanced settings
        with st.expander("🔧 Advanced Settings"):
            seed = st.number_input("Seed (Optional):", min_value=0, value=None, help="For reproducible results")
            model = st.selectbox(
                "Model:",
                ["stable-diffusion-xl", "stable-diffusion-2.1", "stable-diffusion-1.5"],
                index=0
            )
            scheduler = st.selectbox(
                "Scheduler:",
                ["DPMSolverMultistepScheduler", "EulerAncestralDiscreteScheduler", "EulerDiscreteScheduler"],
                index=0
            )
    
    # Generation button
    generate_col1, generate_col2, generate_col3 = st.columns([1, 1, 1])
    
    with generate_col2:
        generate_button = st.button(
            "🎨 Generate Images",
            type="primary",
            use_container_width=True,
            disabled=not prompt.strip()
        )
    
    # Results section
    if generate_button and prompt.strip():
        # Initialize workflow
        workflow = TextToImageWorkflow(endpoint_id, api_key)
        
        # Prepare parameters
        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "num_images": num_images,
            "model": model,
            "scheduler": scheduler
        }
        
        if seed is not None:
            params["seed"] = int(seed)
        
        # Show generation progress
        with st.spinner("🎨 Generating your images..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Simulate progress updates (in real implementation, you could poll job status)
                for i in range(10):
                    progress_bar.progress((i + 1) * 10)
                    status_text.text(f"Generation progress: {(i + 1) * 10}%")
                    time.sleep(0.5)  # Simulate work
                
                # Run the workflow
                status_text.text("Running AI model...")
                result = workflow.run_sync(**params)
                
                progress_bar.progress(100)
                status_text.text("Complete!")
                
            except Exception as e:
                st.error(f"❌ Generation failed: {str(e)}")
                return
        
        # Display results
        if result.status.value == "COMPLETED" and result.output:
            st.success(f"✅ Generated {len(result.output['images'])} image(s) in {result.execution_time:.2f} seconds!")
            
            # Display images
            st.subheader("🖼️ Generated Images")
            
            images = result.output['images']
            if len(images) == 1:
                # Single image - full width
                img_data = images[0]['data']
                try:
                    image = decode_base64_image(img_data)
                    st.image(image, caption=f"Generated Image - {width}x{height}", use_column_width=True)
                    
                    # Download button
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    st.download_button(
                        label="📥 Download Image",
                        data=img_bytes.getvalue(),
                        file_name="generated_image.png",
                        mime="image/png"
                    )
                    
                except Exception as e:
                    st.error(f"Failed to decode image: {str(e)}")
            else:
                # Multiple images - grid layout
                cols = st.columns(min(len(images), 2))
                
                for i, img_info in enumerate(images):
                    with cols[i % 2]:
                        img_data = img_info['data']
                        try:
                            image = decode_base64_image(img_data)
                            st.image(image, caption=f"Image {i+1}", use_column_width=True)
                            
                            # Individual download button
                            img_bytes = io.BytesIO()
                            image.save(img_bytes, format='PNG')
                            img_bytes.seek(0)
                            
                            st.download_button(
                                label=f"📥 Download Image {i+1}",
                                data=img_bytes.getvalue(),
                                file_name=f"generated_image_{i+1}.png",
                                mime="image/png",
                                key=f"download_{i}"
                            )
                            
                        except Exception as e:
                            st.error(f"Failed to decode image {i+1}: {str(e)}")
            
            # Display metadata
            with st.expander("📊 Generation Details"):
                metadata = result.output['metadata']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Generation Info:**")
                    st.write(f"- Execution Time: {result.execution_time:.2f}s")
                    st.write(f"- Job ID: {result.id}")
                    st.write(f"- Model: {metadata.get('model', 'N/A')}")
                    st.write(f"- Scheduler: {metadata.get('scheduler', 'N/A')}")
                
                with col2:
                    st.write("**Image Settings:**")
                    st.write(f"- Dimensions: {metadata.get('width', 'N/A')}x{metadata.get('height', 'N/A')}")
                    st.write(f"- Steps: {metadata.get('steps', 'N/A')}")
                    st.write(f"- Guidance Scale: {metadata.get('guidance_scale', 'N/A')}")
                    st.write(f"- Seed: {metadata.get('seed', 'Random')}")
                
                with col3:
                    st.write("**Prompts:**")
                    st.write(f"**Prompt:** {metadata.get('prompt', 'N/A')}")
                    if metadata.get('negative_prompt'):
                        st.write(f"**Negative:** {metadata.get('negative_prompt')}")
        
        elif result.status.value == "FAILED":
            st.error(f"❌ Generation failed: {result.error}")
            
        else:
            st.warning(f"⚠️ Generation status: {result.status.value}")
            if result.error:
                st.error(f"Error: {result.error}")


if __name__ == "__main__":
    # For testing the demo independently
    st.set_page_config(page_title="Text-to-Image Demo", page_icon="🎨", layout="wide")
    render_text_to_image_demo()
