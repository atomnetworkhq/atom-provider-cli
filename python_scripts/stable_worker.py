# Worker Node (worker_node.py)

import asyncio
import websockets
import json
import torch
from diffusers import StableDiffusionPipeline
import logging
import traceback
import base64
from io import BytesIO
from PIL import Image
import sys

if len(sys.argv)<2:
    print("Please provide jwt token")
    exit(1)

token=sys.argv[-1]
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if CUDA is available
device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if device == "cuda" else torch.float32

# Load a smaller Stable Diffusion model
model_id = "CompVis/stable-diffusion-v1-4"
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch_dtype)
pipe = pipe.to(device)

# If using CPU, turn off attention slicing to prevent errors
if device == "cpu":
    pipe.enable_attention_slicing()

async def generate_image(prompt):
    try:
        logging.debug(f"Generating image for prompt: {prompt}")
        image = pipe(prompt, num_inference_steps=30, guidance_scale=7.5).images[0]
        
        # Convert image to base64 string
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        logging.debug(f"Generated image. Base64 string length: {len(img_str)}")
        return img_str
    except Exception as e:
        logging.error(f"Error generating image: {str(e)}")
        logging.error(traceback.format_exc())
        return f"Error: {str(e)}"

async def run_worker():
    uri = "ws://atom.atomnetwork.xyz:9000"
    headers = {
        "Authorization": f"Bearer {token}"
        # "Authorization": f"Bearer abcd"
    }
    # uri = "ws://atom.atomnetwork:9000"
    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10,
                extra_headers=headers
            ) as websocket:
                logging.info("Connected to head node for Stable Diffusion")
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=120)
                        data = json.loads(message)
                        logging.info(f"Received task {data['task_id']}, prompt: {data['prompt']}")
                        
                        image_base64 = await generate_image(data['prompt'])
                        
                        response = json.dumps({
                            "task_id": data['task_id'],
                            "image": image_base64
                        })
                        logging.debug(f"Sending response for task {data['task_id']}. Response length: {len(response)}")
                        
                        await asyncio.wait_for(websocket.send(response), timeout=30)
                        logging.info(f"Sent result for task {data['task_id']}")
                        
                    except asyncio.TimeoutError:
                        logging.warning("Timeout occurred while processing or sending. Reconnecting...")
                        break
                    except websockets.exceptions.ConnectionClosedError:
                        logging.warning("Connection to head node closed. Attempting to reconnect...")
                        break
                    except Exception as e:
                        logging.error(f"Unexpected error: {str(e)}")
                        logging.error(traceback.format_exc())
                        break
        except Exception as e:
            logging.error(f"Connection error: {e}. Retrying in 5 seconds...")
            logging.error(traceback.format_exc())
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())