"""Text-to-Video workflow implementation for RunPod ComfyUI using Wan 2.2."""
import base64
import json
import os
from typing import Dict, Any
from .base import Workflow


class TextToVideoWorkflow(Workflow):
    """Text-to-Video workflow using RunPod ComfyUI serverless with Wan 2.2 models."""
    
    def __init__(self, endpoint_id: str, api_key: str):
        """Initialize Text-to-Video workflow.
        
        Args:
            endpoint_id: RunPod serverless endpoint ID for ComfyUI with Wan 2.2
            api_key: RunPod API key
        """
        super().__init__(endpoint_id, api_key)
        self.workflow_name = "text-to-video"
        self.workflow_template = self._load_workflow_template()
    
    def _load_workflow_template(self) -> Dict[str, Any]:
        """Load the ComfyUI workflow JSON template for Wan 2.2 text-to-video."""
        workflow_path = os.path.join(os.path.dirname(__file__), "t2vwan.json")
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise ValueError(f"Workflow template not found at {workflow_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in workflow template at {workflow_path}") from exc
    
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters for text-to-video generation.
        
        Required parameters:
        - positive_prompt: str - Text description of desired video
        
        Optional parameters:
        - negative_prompt: str - What to avoid in the video
        - width: int - Video width in pixels (default: 1280)
        - height: int - Video height in pixels (default: 704)
        - steps: int - Number of inference steps (default: 20)
        - guidance_scale: float - How closely to follow prompt (default: 3.5)
        - seed: int - Random seed for reproducibility (default: -1 for random)
        - fps: int - Frame rate (default: 16)
        - codec: str - Video codec (default: "h264")
        """
        positive_prompt = kwargs.get('positive_prompt')
        if not positive_prompt or not isinstance(positive_prompt, str) or len(positive_prompt.strip()) == 0:
            return False
        
        # Validate optional parameters
        width = kwargs.get('width', 1280)
        height = kwargs.get('height', 704)
        steps = kwargs.get('steps', 20)
        guidance_scale = kwargs.get('guidance_scale', 3.5)
        fps = kwargs.get('fps', 16)
        
        if not isinstance(width, int) or width < 64 or width > 2048:
            return False
        if not isinstance(height, int) or height < 64 or height > 2048:
            return False
        if not isinstance(steps, int) or steps < 1 or steps > 50:
            return False
        if not isinstance(guidance_scale, (int, float)) or guidance_scale < 1.0 or guidance_scale > 20.0:
            return False
        if not isinstance(fps, int) or fps < 8 or fps > 30:
            return False
        
        return True
    
    def prepare_input(self, **kwargs) -> Dict[str, Any]:
        """Prepare input data for RunPod ComfyUI endpoint with Wan 2.2.
        
        Args:
            **kwargs: Text-to-video parameters
            
        Returns:
            Dict containing prepared input for RunPod
        """
        # Clone the workflow template (already in API format)
        workflow = json.loads(json.dumps(self.workflow_template))
        
        # Extract parameters
        positive_prompt = kwargs['positive_prompt'].strip()
        negative_prompt = kwargs.get('negative_prompt', '').strip()
        width = kwargs.get('width', 1280)
        height = kwargs.get('height', 704)
        steps = kwargs.get('steps', 20)
        guidance_scale = kwargs.get('guidance_scale', 3.5)
        seed = kwargs.get('seed', -1)
        fps = kwargs.get('fps', 16)
        codec = kwargs.get('codec', 'auto')
        
        # Generate random seed if -1
        if seed == -1:
            import random
            seed = random.randint(0, 2147483647)
        
        # Update specific nodes with user parameters
        # Node 6: Positive prompt
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt
            
        # Node 7: Negative prompt  
        if "7" in workflow:
            workflow["7"]["inputs"]["text"] = negative_prompt
            
        # Node 57: First KSamplerAdvanced (high noise)
        if "57" in workflow:
            workflow["57"]["inputs"]["noise_seed"] = seed
            workflow["57"]["inputs"]["steps"] = steps
            workflow["57"]["inputs"]["cfg"] = guidance_scale
            
        # Node 58: Second KSamplerAdvanced (low noise)
        if "58" in workflow:
            workflow["58"]["inputs"]["noise_seed"] = seed
            workflow["58"]["inputs"]["steps"] = steps
            workflow["58"]["inputs"]["cfg"] = guidance_scale
            
        # Node 59: EmptyHunyuanLatentVideo (dimensions)
        if "59" in workflow:
            workflow["59"]["inputs"]["width"] = width
            workflow["59"]["inputs"]["height"] = height
            # Keep default length from template or allow override
            length = kwargs.get('length', workflow["59"]["inputs"].get("length", 81))
            workflow["59"]["inputs"]["length"] = length
            
        # Node 60: CreateVideo (FPS)
        if "60" in workflow:
            workflow["60"]["inputs"]["fps"] = fps
            
        # Node 61: SaveVideo (codec and format)
        if "61" in workflow:
            # Map codec to valid values
            if codec in ["h264", "h265", "libvpx-vp9"]:
                workflow["61"]["inputs"]["codec"] = codec
            else:
                workflow["61"]["inputs"]["codec"] = "auto"
                
            # Format should be "auto" or "mp4" based on the error message
            workflow["61"]["inputs"]["format"] = "auto"
        
        return {
            "workflow": workflow
        }
    
    def process_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw output from RunPod ComfyUI endpoint.
        
        Args:
            raw_output: Raw response from RunPod ComfyUI worker
            
        Returns:
            Processed output with videos and metadata
        """
        processed_output = {
            "images": [],  # ComfyUI sometimes returns videos as "images"
            "videos": [],
            "metadata": {},
            "raw_response": raw_output
        }
        
        # Extract videos from ComfyUI worker output format
        # Videos might be returned as "images" or "videos" depending on the node
        for key in ["videos", "images"]:
            items = raw_output.get(key, [])
            if isinstance(items, list):
                for i, item_info in enumerate(items):
                    if isinstance(item_info, dict):
                        processed_item = {
                            "index": i,
                            "filename": item_info.get("filename", f"video_{i}.mp4"),
                            "type": item_info.get("type", "base64"),
                            "data": item_info.get("data", "")
                        }
                        
                        # Add to appropriate list based on file extension or type
                        filename = processed_item["filename"].lower()
                        if any(ext in filename for ext in ['.mp4', '.avi', '.mov', '.webm']):
                            processed_output["videos"].append(processed_item)
                        else:
                            processed_output["images"].append(processed_item)
        
        # Extract metadata
        processed_output["metadata"] = {
            "execution_time": raw_output.get("executionTime"),
            "worker_id": raw_output.get("id"),
            "model": "wan-2.2",
            "workflow_type": "text-to-video"
        }
        
        return processed_output
    
    def decode_base64_video(self, base64_string: str) -> bytes:
        """Decode base64 video string to bytes.
        
        Args:
            base64_string: Base64 encoded video
            
        Returns:
            Video bytes
        """
        # Remove data URL prefix if present
        if base64_string.startswith('data:video/'):
            base64_string = base64_string.split(',', 1)[1]
        
        return base64.b64decode(base64_string)
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about this workflow.
        
        Returns:
            Dict containing workflow information
        """
        return {
            "name": "Text-to-Video",
            "description": "Generate videos from text descriptions using Wan 2.2 models",
            "model": "wan-2.2",
            "supported_codecs": ["h264", "h265", "libvpx-vp9"],
            "parameters": {
                "positive_prompt": {
                    "type": "string",
                    "required": True,
                    "description": "Text description of the desired video"
                },
                "negative_prompt": {
                    "type": "string",
                    "required": False,
                    "description": "Text describing what to avoid in the video"
                },
                "width": {
                    "type": "integer",
                    "required": False,
                    "default": 1280,
                    "options": [1280, 1024, 960, 896, 832, 768, 704, 640],
                    "description": "Video width in pixels"
                },
                "height": {
                    "type": "integer",
                    "required": False,
                    "default": 704,
                    "options": [704, 576, 512, 448, 384, 320],
                    "description": "Video height in pixels"
                },
                "steps": {
                    "type": "integer",
                    "required": False,
                    "default": 20,
                    "min": 1,
                    "max": 50,
                    "description": "Number of denoising steps"
                },
                "guidance_scale": {
                    "type": "float",
                    "required": False,
                    "default": 3.5,
                    "min": 1.0,
                    "max": 20.0,
                    "description": "CFG guidance scale"
                },
                "seed": {
                    "type": "integer",
                    "required": False,
                    "default": -1,
                    "description": "Random seed (-1 for random)"
                },
                "fps": {
                    "type": "integer",
                    "required": False,
                    "default": 16,
                    "options": [8, 12, 16, 24, 30],
                    "description": "Video frame rate"
                },
                "codec": {
                    "type": "string",
                    "required": False,
                    "default": "h264",
                    "options": ["h264", "h265", "libvpx-vp9"],
                    "description": "Video encoding codec"
                }
            }
        }