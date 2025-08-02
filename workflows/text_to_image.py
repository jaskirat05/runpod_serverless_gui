"""Text-to-Image workflow implementation for RunPod ComfyUI."""
import base64
import json
import os
from typing import Dict, Any
from .base import Workflow


class TextToImageWorkflow(Workflow):
    """Text-to-Image workflow using RunPod ComfyUI serverless."""
    
    def __init__(self, endpoint_id: str, api_key: str):
        """Initialize Text-to-Image workflow.
        
        Args:
            endpoint_id: RunPod serverless endpoint ID for ComfyUI
            api_key: RunPod API key
        """
        super().__init__(endpoint_id, api_key)
        self.workflow_name = "text-to-image"
        self.workflow_template = self._load_workflow_template()
    
    def _load_workflow_template(self) -> Dict[str, Any]:
        """Load the ComfyUI workflow JSON template."""
        workflow_path = os.path.join(os.path.dirname(__file__), "workflow_api.json")
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise ValueError(f"Workflow template not found at {workflow_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in workflow template at {workflow_path}") from exc
    
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters for text-to-image generation.
        
        Required parameters:
        - prompt: str - Text description of desired image
        
        Optional parameters:
        - negative_prompt: str - What to avoid in the image
        - steps: int - Number of inference steps (default: 20)
        - guidance_scale: float - How closely to follow prompt (default: 8.0)
        - seed: int - Random seed for reproducibility
        """
        prompt = kwargs.get('prompt')
        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) == 0:
            return False
        
        # Validate optional parameters
        steps = kwargs.get('steps', 20)
        guidance_scale = kwargs.get('guidance_scale', 8.0)
        
        if not isinstance(steps, int) or steps < 1 or steps > 100:
            return False
        if not isinstance(guidance_scale, (int, float)) or guidance_scale < 0 or guidance_scale > 20:
            return False
        
        return True
    
    def prepare_input(self, **kwargs) -> Dict[str, Any]:
        """Prepare input data for RunPod ComfyUI endpoint.
        
        Args:
            **kwargs: Text-to-image parameters
            
        Returns:
            Dict containing prepared input for RunPod
        """
        # Clone the workflow template
        workflow = json.loads(json.dumps(self.workflow_template))
        
        # Extract parameters
        prompt = kwargs['prompt'].strip()
        negative_prompt = kwargs.get('negative_prompt', '')
        steps = kwargs.get('steps', 20)
        guidance_scale = kwargs.get('guidance_scale', 8.0)
        seed = kwargs.get('seed', 0)
        
        # Convert to ComfyUI API format - just update the nodes directly
        api_workflow = {}
        
        for node in workflow["nodes"]:
            node_id = str(node["id"])
            api_workflow[node_id] = {
                "class_type": node["type"],
                "inputs": {}
            }
            
            # Update specific nodes with user parameters
            if node["type"] == "CLIPTextEncode":
                if node["id"] == 6:  # Positive prompt
                    api_workflow[node_id]["inputs"]["text"] = prompt
                elif node["id"] == 10:  # Negative prompt  
                    api_workflow[node_id]["inputs"]["text"] = negative_prompt
                    
                # Add CLIP connection
                for input_conn in node.get("inputs", []):
                    if input_conn["name"] == "clip":
                        # Find the source node from links
                        link_id = input_conn["link"]
                        for link in workflow["links"]:
                            if link[0] == link_id:
                                api_workflow[node_id]["inputs"]["clip"] = [str(link[1]), link[2]]
                                break
                                
            elif node["type"] == "KSampler" and node["id"] == 8:
                # Update KSampler with user parameters
                api_workflow[node_id]["inputs"] = {
                    "seed": seed,
                    "control_after_generate": "fixed" if seed > 0 else "randomize", 
                    "steps": steps,
                    "cfg": guidance_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal", 
                    "denoise": 1.0
                }
                
                # Add connections from links
                for input_conn in node.get("inputs", []):
                    link_id = input_conn["link"]
                    if link_id:
                        for link in workflow["links"]:
                            if link[0] == link_id:
                                api_workflow[node_id]["inputs"][input_conn["name"]] = [str(link[1]), link[2]]
                                break
            
            else:
                # For other nodes, just copy widget values and add connections
                if "widgets_values" in node:
                    # Map widgets to inputs based on node type
                    if node["type"] == "UNETLoader":
                        api_workflow[node_id]["inputs"]["unet_name"] = node["widgets_values"][0]
                        api_workflow[node_id]["inputs"]["weight_dtype"] = node["widgets_values"][1]
                    elif node["type"] == "DualCLIPLoader":
                        api_workflow[node_id]["inputs"]["clip_name1"] = node["widgets_values"][0] 
                        api_workflow[node_id]["inputs"]["clip_name2"] = node["widgets_values"][1]
                        api_workflow[node_id]["inputs"]["type"] = node["widgets_values"][2]
                    elif node["type"] == "VAELoader":
                        api_workflow[node_id]["inputs"]["vae_name"] = node["widgets_values"][0]
                
                # Add input connections
                for input_conn in node.get("inputs", []):
                    link_id = input_conn["link"]
                    if link_id:
                        for link in workflow["links"]:
                            if link[0] == link_id:
                                api_workflow[node_id]["inputs"][input_conn["name"]] = [str(link[1]), link[2]]
                                break
        
        return {
            "workflow": api_workflow
        }
    
    def process_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw output from RunPod ComfyUI endpoint.
        
        Args:
            raw_output: Raw response from RunPod ComfyUI worker
            
        Returns:
            Processed output with images and metadata
        """
        processed_output = {
            "images": [],
            "metadata": {},
            "raw_response": raw_output
        }
        
        # Extract images from ComfyUI worker output format
        images = raw_output.get('images', [])
        if isinstance(images, list):
            for i, image_info in enumerate(images):
                if isinstance(image_info, dict):
                    processed_output["images"].append({
                        "index": i,
                        "filename": image_info.get("filename", f"image_{i}.png"),
                        "type": image_info.get("type", "base64"),
                        "data": image_info.get("data", "")
                    })
        
        # Extract any metadata
        processed_output["metadata"] = {
            "execution_time": raw_output.get("executionTime"),
            "worker_id": raw_output.get("id")
        }
        
        return processed_output
    
    def decode_base64_image(self, base64_string: str) -> bytes:
        """Decode base64 image string to bytes.
        
        Args:
            base64_string: Base64 encoded image
            
        Returns:
            Image bytes
        """
        # Remove data URL prefix if present
        if base64_string.startswith('data:image/'):
            base64_string = base64_string.split(',', 1)[1]
        
        return base64.b64decode(base64_string)
    
    def get_image_info(self) -> Dict[str, Any]:
        """Get information about this workflow.
        
        Returns:
            Dict containing workflow information
        """
        return {
            "name": "Text-to-Image",
            "description": "Generate images from text descriptions using AI models",
            "supported_models": [
                "stable-diffusion-xl",
                "stable-diffusion-2.1",
                "stable-diffusion-1.5",
                "midjourney-style",
                "realistic-vision"
            ],
            "supported_schedulers": [
                "DPMSolverMultistepScheduler",
                "EulerAncestralDiscreteScheduler",
                "EulerDiscreteScheduler",
                "HeunDiscreteScheduler",
                "KDPM2DiscreteScheduler",
                "LMSDiscreteScheduler",
                "PNDMScheduler"
            ],
            "parameters": {
                "prompt": {
                    "type": "string",
                    "required": True,
                    "description": "Text description of the desired image"
                },
                "negative_prompt": {
                    "type": "string",
                    "required": False,
                    "description": "Text describing what to avoid in the image"
                },
                "width": {
                    "type": "integer",
                    "required": False,
                    "default": 512,
                    "min": 64,
                    "max": 2048,
                    "description": "Image width in pixels"
                },
                "height": {
                    "type": "integer",
                    "required": False,
                    "default": 512,
                    "min": 64,
                    "max": 2048,
                    "description": "Image height in pixels"
                },
                "steps": {
                    "type": "integer",
                    "required": False,
                    "default": 20,
                    "min": 1,
                    "max": 100,
                    "description": "Number of denoising steps"
                },
                "guidance_scale": {
                    "type": "float",
                    "required": False,
                    "default": 7.5,
                    "min": 0.0,
                    "max": 20.0,
                    "description": "How closely to follow the prompt"
                },
                "seed": {
                    "type": "integer",
                    "required": False,
                    "description": "Random seed for reproducible generation"
                },
                "num_images": {
                    "type": "integer",
                    "required": False,
                    "default": 1,
                    "min": 1,
                    "max": 4,
                    "description": "Number of images to generate"
                }
            }
        }
