# Upstash Redis Setup Guide

This guide will help you set up Upstash Redis for the AI Content Generator queue system.

## 1. Create Upstash Redis Database

1. Go to [Upstash Console](https://console.upstash.com/)
2. Sign up or log in to your account
3. Click **"Create Database"**
4. Configure your database:
   - **Name**: `ai-content-generator`
   - **Type**: Choose **Global** for best performance
   - **Region**: Select closest to your users
   - **TLS**: Keep enabled (recommended)
5. Click **"Create"**

## 2. Get Connection Details

After creating the database:

1. Click on your database name
2. Go to the **"Details"** tab
3. Copy the following values:
   - **REST URL** (starts with `https://`)
   - **REST TOKEN** (long alphanumeric string)

## 3. Configure Environment Variables

Add these to your `.env` file:

```bash
# Upstash Redis Configuration
UPSTASH_REDIS_REST_URL=https://your-database-url.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_rest_token_here

# Existing variables
RUNPOD_API_KEY=your_runpod_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_bucket_name
```

## 4. Install Dependencies

```bash
pip install redis>=4.0.0 boto3>=1.26.0
```

## 5. Test Connection

You can test the connection by running:

```python
from queue_manager import QueueManager

try:
    queue_manager = QueueManager()
    print("✅ Connected to Upstash Redis successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## 6. Start the System

### Start the Streamlit App:
```bash
streamlit run app.py
```

### Start Background Workers:
```bash
# Terminal 1: Start first worker
python worker.py

# Terminal 2: Start additional worker (optional)
python worker.py --worker-id worker_2
```

## Upstash Benefits

- ✅ **Serverless**: No server management required
- ✅ **Global**: Low latency worldwide
- ✅ **Persistent**: Data survives restarts
- ✅ **Scalable**: Automatic scaling based on usage
- ✅ **Secure**: TLS encryption by default
- ✅ **Cost-effective**: Pay only for what you use

## Pricing

Upstash Redis offers:
- **Free tier**: 10,000 commands per day
- **Pay-as-you-go**: $0.2 per 100k commands
- **No monthly fees** for idle databases

Perfect for development and production use!

## Troubleshooting

### Connection Issues:
1. Verify your REST URL and token are correct
2. Check if TLS is enabled (should be)
3. Ensure no firewall blocking HTTPS connections

### Performance:
- Choose a region close to your workers
- Use Global databases for multi-region deployments
- Monitor command usage in Upstash console

### Security:
- Keep your REST token secure
- Rotate tokens periodically
- Use environment variables, never hardcode credentials