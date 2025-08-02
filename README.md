# Modern Dashboard with RunPod AI Integration

A professional Streamlit application showcasing modern design practices with RunPod serverless AI integration.

## Features

### Dashboard
- **40-60 Split Layout**: Left panel (40%) for controls, right panel (60%) for content
- **Modern Design**: Custom CSS styling with professional color scheme
- **Interactive Components**: 
  - User input forms (text input, sliders, multi-select)
  - Action buttons with feedback
  - Real-time metrics display
- **Data Visualization**: Sample charts and dataframes
- **Organized Content**: Tabbed interface for better organization
- **Responsive Design**: Works well on different screen sizes

### AI Integration (RunPod)
- **Text-to-Image Generation**: Generate images from text descriptions
- **Modular Workflow System**: Extensible architecture for adding more AI workflows
- **Real-time Progress**: Live updates during AI processing
- **Multiple Models**: Support for various AI models (Stable Diffusion, etc.)
- **Advanced Parameters**: Fine-tune generation with steps, guidance scale, seeds
- **Batch Generation**: Generate multiple images at once
- **Download Support**: Save generated images locally

## Project Structure

```
gradioapp/
├── app.py                      # Main Streamlit application
├── text_to_image_demo.py      # Text-to-Image interface
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── workflows/                 # AI workflow implementations
│   ├── __init__.py
│   ├── base.py               # Abstract workflow base class
│   └── text_to_image.py      # Text-to-Image workflow
└── README.md                 # This file
```

## Installation

1. **Clone or download** this project

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up RunPod credentials** (optional for demo):
   ```bash
   cp .env.example .env
   # Edit .env with your RunPod API key and endpoint IDs
   ```

## RunPod Setup

### 1. Get RunPod API Key
1. Sign up at [RunPod.io](https://www.runpod.io)
2. Go to [RunPod Console](https://www.runpod.io/console)
3. Navigate to Settings → API Keys
4. Create a new API key and copy it

### 2. Deploy Text-to-Image Endpoint
1. In RunPod Console, go to Serverless
2. Click "New Endpoint"
3. Choose a text-to-image template (e.g., Stable Diffusion XL)
4. Configure your endpoint settings
5. Deploy and copy the endpoint ID

### 3. Configure Environment
Either set environment variables:
```bash
export RUNPOD_API_KEY="your_api_key_here"
export RUNPOD_TEXT_TO_IMAGE_ENDPOINT="your_endpoint_id_here"
```

Or create a `.env` file with:
```
RUNPOD_API_KEY=your_api_key_here
RUNPOD_TEXT_TO_IMAGE_ENDPOINT=your_endpoint_id_here
```

## Running the App

```bash
streamlit run app.py
```

The app will be available at http://localhost:8501

## Usage

### Dashboard Page
- Explore various Streamlit components and interactions
- Test different chart types and data visualizations
- Experiment with form controls and settings

### Text-to-Image Page
1. **Configure RunPod** (if not set via environment):
   - Enter your API key and endpoint ID in the configuration section
   
2. **Generate Images**:
   - Write a descriptive prompt
   - Optionally add a negative prompt
   - Adjust image dimensions, steps, and guidance scale
   - Click "Generate Images"
   
3. **Download Results**:
   - View generated images
   - Download individual images
   - Check generation metadata

## Workflow Architecture

The application uses a modular workflow system:

### Base Workflow Class
```python
from workflows import Workflow, WorkflowResult

class MyCustomWorkflow(Workflow):
    def validate_input(self, **kwargs) -> bool:
        # Validate input parameters
        pass
    
    def prepare_input(self, **kwargs) -> Dict[str, Any]:
        # Prepare RunPod API payload
        pass
    
    def process_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        # Process RunPod response
        pass
```

### Adding New Workflows
1. Create a new workflow class inheriting from `Workflow`
2. Implement the required abstract methods
3. Add the workflow to `workflows/__init__.py`
4. Create a demo interface similar to `text_to_image_demo.py`
5. Add the new page to the main app navigation

## API Integration Examples

### Synchronous Usage
```python
from workflows import TextToImageWorkflow

workflow = TextToImageWorkflow(endpoint_id, api_key)
result = workflow.run_sync(
    prompt="A beautiful sunset over mountains",
    width=1024,
    height=1024,
    steps=30
)

if result.status == WorkflowStatus.COMPLETED:
    images = result.output['images']
    # Process images...
```

### Asynchronous Usage
```python
import asyncio

async def generate_image():
    workflow = TextToImageWorkflow(endpoint_id, api_key)
    result = await workflow.run_async(
        prompt="A futuristic city at night",
        guidance_scale=8.0
    )
    return result

result = asyncio.run(generate_image())
```

## Supported AI Models

The text-to-image workflow supports various models:
- Stable Diffusion XL
- Stable Diffusion 2.1
- Stable Diffusion 1.5
- Custom fine-tuned models

## Configuration Options

### Text-to-Image Parameters
- **Prompt**: Text description of desired image
- **Negative Prompt**: What to avoid in the image
- **Dimensions**: Width and height (64-2048px)
- **Steps**: Inference steps (1-100)
- **Guidance Scale**: Prompt adherence (0-20)
- **Seed**: For reproducible results
- **Model**: AI model selection
- **Scheduler**: Sampling method

## Troubleshooting

### Common Issues

1. **ImportError**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **RunPod Authentication Error**: Check your API key and endpoint ID

3. **Timeout Errors**: Large images or high step counts may take longer

4. **Memory Errors**: Reduce image dimensions or batch size

### Error Handling
The workflow system includes comprehensive error handling:
- Input validation
- HTTP error handling
- Timeout management
- Status polling
- Detailed error messages

## Development

### Adding New Features
1. Fork or clone the repository
2. Create new workflow classes in `workflows/`
3. Add corresponding demo interfaces
4. Update navigation in `app.py`
5. Test thoroughly

### Code Structure
- **Separation of Concerns**: UI, business logic, and API integration are separated
- **Async Support**: Both sync and async execution modes
- **Error Handling**: Comprehensive error handling and user feedback
- **Extensibility**: Easy to add new workflows and features

## License

This project is for educational and demonstration purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues related to:
- **Streamlit**: Check [Streamlit Documentation](https://docs.streamlit.io)
- **RunPod**: Check [RunPod Documentation](https://docs.runpod.io)
- **This Project**: Create an issue in the repository
