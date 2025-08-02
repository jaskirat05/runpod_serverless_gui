#!/usr/bin/env python3
"""Test script for RunPod workflows."""

import asyncio
import sys
import os
from workflows import TextToImageWorkflow, WorkflowStatus
from config import get_default_config


async def test_text_to_image():
    """Test the text-to-image workflow."""
    print("🧪 Testing Text-to-Image Workflow")
    print("=" * 40)
    
    # Try to get configuration
    config = get_default_config()
    if not config:
        print("❌ No configuration found. Please set environment variables:")
        print("   export RUNPOD_API_KEY='your_api_key'")
        print("   export RUNPOD_TEXT_TO_IMAGE_ENDPOINT='your_endpoint_id'")
        return False
    
    print(f"✅ Configuration loaded")
    print(f"   API Key: {config.api_key[:8]}...")
    print(f"   Endpoint: {config.text_to_image_endpoint}")
    
    # Initialize workflow
    workflow = TextToImageWorkflow(
        config.text_to_image_endpoint,
        config.api_key
    )
    
    # Test parameters
    test_params = {
        "prompt": "A beautiful sunset over mountains, digital art",
        "negative_prompt": "blurry, low quality",
        "width": 512,
        "height": 512,
        "steps": 20,
        "guidance_scale": 7.5,
        "num_images": 1
    }
    
    print(f"\n📝 Test Parameters:")
    for key, value in test_params.items():
        print(f"   {key}: {value}")
    
    # Validate input
    print(f"\n🔍 Validating input...")
    if not workflow.validate_input(**test_params):
        print("❌ Input validation failed")
        return False
    print("✅ Input validation passed")
    
    # Run workflow
    print(f"\n🚀 Running workflow...")
    try:
        result = await workflow.run_async(**test_params)
        
        print(f"\n📊 Results:")
        print(f"   Status: {result.status.value}")
        print(f"   Job ID: {result.id}")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        
        if result.status == WorkflowStatus.COMPLETED:
            print(f"   Generated Images: {len(result.output['images'])}")
            print("✅ Workflow completed successfully!")
            return True
        else:
            print(f"   Error: {result.error}")
            print("❌ Workflow failed")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return False


def test_workflow_info():
    """Test workflow information retrieval."""
    print("\n📋 Workflow Information")
    print("=" * 40)
    
    workflow = TextToImageWorkflow("test", "test")
    info = workflow.get_image_info()
    
    print(f"Name: {info['name']}")
    print(f"Description: {info['description']}")
    print(f"Supported Models: {len(info['supported_models'])}")
    print(f"Supported Schedulers: {len(info['supported_schedulers'])}")
    print(f"Parameters: {len(info['parameters'])}")
    
    return True


async def main():
    """Main test function."""
    print("🧪 RunPod Workflow Test Suite")
    print("=" * 50)
    
    # Test 1: Workflow information
    test1_result = test_workflow_info()
    
    # Test 2: Text-to-image workflow (only if environment is configured)
    test2_result = await test_text_to_image()
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 40)
    print(f"Workflow Info Test: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Text-to-Image Test: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test2_result:
        print(f"\n🎉 All tests passed! The RunPod integration is working correctly.")
    elif not test2_result and get_default_config() is None:
        print(f"\n⚠️  RunPod not configured. Set environment variables to test full integration.")
    else:
        print(f"\n❌ Some tests failed. Check your RunPod configuration and network connection.")


if __name__ == "__main__":
    asyncio.run(main())
