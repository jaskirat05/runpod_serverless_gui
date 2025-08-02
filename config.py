"""Configuration management for RunPod workflows."""
import os
from typing import Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class RunPodConfig:
    """RunPod configuration settings."""
    api_key: str
    text_to_image_endpoint: str
    # Add more endpoints as needed
    # image_to_image_endpoint: Optional[str] = None
    # text_to_video_endpoint: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RunPodConfig':
        """Load configuration from environment variables.
        
        Expected environment variables:
        - RUNPOD_API_KEY: Your RunPod API key
        - RUNPOD_TEXT_TO_IMAGE_ENDPOINT: Endpoint ID for text-to-image
        """
        api_key = os.getenv('RUNPOD_API_KEY')
        if not api_key:
            raise ValueError("RUNPOD_API_KEY environment variable is required")
        
        text_to_image_endpoint = os.getenv('RUNPOD_TEXT_TO_IMAGE_ENDPOINT')
        if not text_to_image_endpoint:
            raise ValueError("RUNPOD_TEXT_TO_IMAGE_ENDPOINT environment variable is required")
        
        return cls(
            api_key=api_key,
            text_to_image_endpoint=text_to_image_endpoint
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, str]) -> 'RunPodConfig':
        """Load configuration from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
        """
        return cls(
            api_key=config_dict['api_key'],
            text_to_image_endpoint=config_dict['text_to_image_endpoint']
        )


# Default configuration - will try to load from environment
def get_default_config() -> Optional[RunPodConfig]:
    """Get default configuration from environment variables.
    
    Returns:
        RunPodConfig if environment variables are set, None otherwise
    """
    try:
        return RunPodConfig.from_env()
    except ValueError:
        return None
