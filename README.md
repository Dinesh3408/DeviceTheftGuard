---
title: Device Theft Guard Openenv Environment Server
emoji: "\U0001F6E1"
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# Device Theft Guard Openenv Environment

A risk-aware environment for laptop theft prevention, with action-based responses (`noop`, `alert`, `lock`, `wipe`) and a built-in web UI for interactive testing.

## Quick Start

The simplest way to use the Device Theft Guard Openenv environment is through the `LaptopSecurityOpenenvEnv` class:

```python
from laptop_security_openenv import LaptopSecurityOpenenvAction, LaptopSecurityOpenenvEnv

try:
    # Create environment from Docker image
    laptop_security_openenvenv = LaptopSecurityOpenenvEnv.from_docker_image("laptop_security_openenv-env:latest")

    # Reset
    result = laptop_security_openenvenv.reset()
    print(f"Reset: {result.observation.echoed_message}")

    # Send multiple messages
    messages = ["Hello, World!", "Testing echo", "Final message"]

    for msg in messages:
        result = laptop_security_openenvenv.step(LaptopSecurityOpenenvAction(message=msg))
        print(f"Sent: '{msg}'")
        print(f"  â†’ Echoed: '{result.observation.echoed_message}'")
        print(f"  â†’ Length: {result.observation.message_length}")
        print(f"  â†’ Reward: {result.reward}")

finally:
    # Always clean up
    laptop_security_openenvenv.close()
```

That's it! The `LaptopSecurityOpenenvEnv.from_docker_image()` method handles:
- Starting the Docker container
- Waiting for the server to be ready
- Connecting to the environment
- Container cleanup when you call `close()`

## Building the Docker Image

Before using the environment, you need to build the Docker image:

```bash
# From project root
docker build -t laptop_security_openenv-env:latest -f server/Dockerfile .
```

## Deploying to Hugging Face Spaces

You can easily deploy your OpenEnv environment to Hugging Face Spaces using the `openenv push` command:

```bash
# From the environment directory (where openenv.yaml is located)
openenv push

# Or specify options
openenv push --namespace my-org --private
```

The `openenv push` command will:
1. Validate that the directory is an OpenEnv environment (checks for `openenv.yaml`)
2. Prepare a custom build for Hugging Face Docker space (enables web interface)
3. Upload to Hugging Face (ensuring you're logged in)

### Prerequisites

- Authenticate with Hugging Face: The command will prompt for login if not already authenticated

### Options

- `--directory`, `-d`: Directory containing the OpenEnv environment (defaults to current directory)
- `--repo-id`, `-r`: Repository ID in format 'username/repo-name' (defaults to 'username/env-name' from openenv.yaml)
- `--base-image`, `-b`: Base Docker image to use (overrides Dockerfile FROM)
- `--private`: Deploy the space as private (default: public)

### Examples

```bash
# Push to your personal namespace (defaults to username/env-name from openenv.yaml)
openenv push

# Push to a specific repository
openenv push --repo-id my-org/my-env

# Push with a custom base image
openenv push --base-image ghcr.io/meta-pytorch/openenv-base:latest

# Push as a private space
openenv push --private

# Combine options
openenv push --repo-id my-org/my-env --base-image custom-base:latest --private
```

After deployment, your space will be available at:
`https://huggingface.co/spaces/<repo-id>`

The deployed space includes:
- **Web Interface** at `/web` - Interactive UI for exploring the environment
- **API Documentation** at `/docs` - Full OpenAPI/Swagger interface
- **Health Check** at `/health` - Container health monitoring
- **WebSocket** at `/ws` - Persistent session endpoint for low-latency interactions

## Environment Details

### Action
**LaptopSecurityOpenenvAction**: Contains a single field
- `message` (str) - The message to echo back

### Observation
**LaptopSecurityOpenenvObservation**: Contains the echo response and metadata
- `echoed_message` (str) - The message echoed back
- `message_length` (int) - Length of the message
- `reward` (float) - Reward based on message length (length Ã— 0.1)
- `done` (bool) - Always False for echo environment
- `metadata` (dict) - Additional info like step count

### Reward
The reward is calculated as: `message_length Ã— 0.1`
- "Hi" â†’ reward: 0.2
- "Hello, World!" â†’ reward: 1.3
- Empty message â†’ reward: 0.0

## Advanced Usage

### Connecting to an Existing Server

If you already have a Device Theft Guard Openenv environment server running, you can connect directly:

```python
from laptop_security_openenv import LaptopSecurityOpenenvEnv

# Connect to existing server
laptop_security_openenvenv = LaptopSecurityOpenenvEnv(base_url="<ENV_HTTP_URL_HERE>")

# Use as normal
result = laptop_security_openenvenv.reset()
result = laptop_security_openenvenv.step(LaptopSecurityOpenenvAction(message="Hello!"))
```

Note: When connecting to an existing server, `laptop_security_openenvenv.close()` will NOT stop the server.

### Using the Context Manager

The client supports context manager usage for automatic connection management:

```python
from laptop_security_openenv import LaptopSecurityOpenenvAction, LaptopSecurityOpenenvEnv

# Connect with context manager (auto-connects and closes)
with LaptopSecurityOpenenvEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(f"Reset: {result.observation.echoed_message}")
    # Multiple steps with low latency
    for msg in ["Hello", "World", "!"]:
        result = env.step(LaptopSecurityOpenenvAction(message=msg))
        print(f"Echoed: {result.observation.echoed_message}")
```

The client uses WebSocket connections for:
- **Lower latency**: No HTTP connection overhead per request
- **Persistent session**: Server maintains your environment state
- **Efficient for episodes**: Better for many sequential steps

### Concurrent WebSocket Sessions

The server supports multiple concurrent WebSocket connections. To enable this,
modify `server/app.py` to use factory mode:

```python
# In server/app.py - use factory mode for concurrent sessions
app = create_app(
    LaptopSecurityOpenenvEnvironment,  # Pass class, not instance
    LaptopSecurityOpenenvAction,
    LaptopSecurityOpenenvObservation,
    max_concurrent_envs=4,  # Allow 4 concurrent sessions
)
```

Then multiple clients can connect simultaneously:

```python
from laptop_security_openenv import LaptopSecurityOpenenvAction, LaptopSecurityOpenenvEnv
from concurrent.futures import ThreadPoolExecutor

def run_episode(client_id: int):
    with LaptopSecurityOpenenvEnv(base_url="http://localhost:8000") as env:
        result = env.reset()
        for i in range(10):
            result = env.step(LaptopSecurityOpenenvAction(message=f"Client {client_id}, step {i}"))
        return client_id, result.observation.message_length

# Run 4 episodes concurrently
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_episode, range(4)))
```

## Development & Testing

### Direct Environment Testing

Test the environment logic directly without starting the HTTP server:

```bash
# From the server directory
python3 server/laptop_security_openenv_environment.py
```

This verifies that:
- Environment resets correctly
- Step executes actions properly
- State tracking works
- Rewards are calculated correctly

### Running Locally

Run the server locally for development:

```bash
uvicorn server.app:app --reload
```

## Project Structure

```
laptop_security_openenv/
â”œâ”€â”€ .dockerignore         # Docker build exclusions
â”œâ”€â”€ __init__.py            # Module exports
â”œâ”€â”€ README.md              # This file
â”œâ”€â”€ openenv.yaml           # OpenEnv manifest
â”œâ”€â”€ pyproject.toml         # Project metadata and dependencies
â”œâ”€â”€ uv.lock                # Locked dependencies (generated)
â”œâ”€â”€ client.py              # LaptopSecurityOpenenvEnv client
â”œâ”€â”€ models.py              # Action and Observation models
â””â”€â”€ server/
    â”œâ”€â”€ __init__.py        # Server module exports
    â”œâ”€â”€ laptop_security_openenv_environment.py  # Core environment logic
    â”œâ”€â”€ app.py             # FastAPI application (HTTP + WebSocket endpoints)
    â””â”€â”€ Dockerfile         # Container image definition
```

