"""Text-to-Video demo page for Streamlit app."""
import streamlit as st
from workflows.text_to_video import TextToVideoWorkflow
from config import get_default_config


def render_text_to_video_demo():
    """Render the text-to-video generation demo page."""
    st.title("🎬 Text-to-Video Generation")
    st.markdown("Generate videos from text descriptions using Wan 2.2 models")
    
    # Create two columns for input and parameters
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Prompts")
        
        # Main prompt input
        prompt = st.text_area(
            "Prompt",
            value="A close-up of a young woman smiling gently in the rain, raindrops glistening on her face and eyelashes. The video captures the delicate details of her expression and the water droplets, with soft light reflecting off her skin in the rainy atmosphere.",
            height=100,
            help="Describe the video you want to generate"
        )
        
        # Negative prompt
        negative_prompt = st.text_area(
            "Negative Prompt (Optional)",
            value="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
            height=80,
            help="Describe what you want to avoid in the video"
        )
        
        # Video dimensions
        st.subheader("📐 Video Dimensions")
        width = st.selectbox(
            "Width",
            options=[1280, 1024, 960, 896, 832, 768, 704, 640],
            index=0,
            help="Video width in pixels"
        )
        
        height = st.selectbox(
            "Height", 
            options=[704, 576, 512, 448, 384, 320],
            index=0,
            help="Video height in pixels"
        )
        
    with col2:
        st.subheader("⚙️ Generation Parameters")
        
        # Generation parameters
        steps = st.slider(
            "Steps",
            min_value=1,
            max_value=50,
            value=20,
            help="Number of denoising steps"
        )
        
        guidance_scale = st.slider(
            "Guidance Scale",
            min_value=1.0,
            max_value=20.0,
            value=3.5,
            step=0.5,
            help="CFG guidance scale"
        )
        
        seed = st.number_input(
            "Seed",
            min_value=-1,
            max_value=2147483647,
            value=-1,
            help="Random seed (-1 for random)"
        )
        
        # Video output parameters
        st.subheader("🎥 Video Output")
        fps = st.selectbox(
            "Frame Rate (FPS)",
            options=[8, 12, 16, 24, 30],
            index=2,
            help="Video frame rate"
        )
        
        codec = st.selectbox(
            "Video Codec",
            options=["h264", "h265", "libvpx-vp9"],
            index=0,
            help="Video encoding codec"
        )
    
    # Generate button
    st.markdown("---")
    generate_button = st.button(
        "🎬 Generate Video",
        type="primary",
        use_container_width=True,
        help="Start video generation with current settings"
    )
    
    if generate_button:
        if not prompt.strip():
            st.error("❌ Please enter a prompt")
            return
            
        with st.spinner("🎬 Generating video..."):
            # Show generation info
            st.info(f"""
            **Generation Settings:**
            - Dimensions: {width}x{height}
            - Steps: {steps}
            - Guidance Scale: {guidance_scale}
            - Seed: {'Random' if seed == -1 else seed}
            - FPS: {fps}
            - Codec: {codec}
            """)
            
            try:
                # Initialize workflow
                config = get_default_config()
                if not config:
                    st.error("❌ RunPod configuration not found. Please check your environment variables.")
                    return
                    
                workflow = TextToVideoWorkflow(
                    endpoint_id=config.text_to_image_endpoint,  # Using same endpoint for now
                    api_key=config.api_key
                )
                
                # Generate video with all parameters
                result = workflow.run_sync(
                    positive_prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    guidance_scale=guidance_scale,
                    seed=seed,
                    fps=fps,
                    codec=codec
                )
                
                if result.status.value == "COMPLETED" and result.output:
                    st.success("✅ Video generated successfully!")
                    
                    # Display video if available  
                    if 'images' in result.output and result.output['images']:
                        # Videos are sometimes returned as "images" in ComfyUI
                        video_data = result.output['images'][0]['data']
                        if result.output['images'][0]['type'] == 'base64':
                            # For now, show as JSON since Streamlit needs video file/URL
                            st.info("🎬 Video generated successfully! (Base64 format)")
                            with st.expander("📄 Raw Video Data"):
                                st.json(result.output)
                        else:
                            # S3 URL or other format
                            st.video(video_data)
                            st.markdown(f"[📥 Download Video]({video_data})")
                    elif 'videos' in result.output and result.output['videos']:
                        # Direct video output
                        video_data = result.output['videos'][0]['data']
                        if result.output['videos'][0]['type'] == 'base64':
                            st.info("🎬 Video generated successfully! (Base64 format)")
                            with st.expander("📄 Raw Video Data"):
                                st.json(result.output)
                        else:
                            st.video(video_data)
                            st.markdown(f"[📥 Download Video]({video_data})")
                    else:
                        # Show raw output for debugging
                        st.warning("⚠️ Video generated but format not recognized")
                        with st.expander("📄 Raw Output"):
                            st.json(result.output)
                            
                elif result.status.value == "FAILED":
                    st.error(f"❌ Video generation failed: {result.error}")
                    
                else:
                    st.warning(f"⚠️ Generation status: {result.status.value}")
                    if result.error:
                        st.error(f"Error: {result.error}")
                            
            except Exception as e:
                st.error(f"❌ Video generation failed: {str(e)}")
                import traceback
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())