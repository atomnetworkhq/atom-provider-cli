# Worker Node (worker_node.py)

import asyncio
import websockets
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
import traceback
import sys
import time


if len(sys.argv)<2:
    print("Please provide jwt token")
    exit(1)

token=sys.argv[-1]
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-1.5B", device_map="auto", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-1.5B", trust_remote_code=True)

async def process_chunk(chunk):
    try:
        logging.debug(f"Processing chunk: {chunk[:50]}...")  # Log first 50 tokens of the chunk
        inputs = torch.tensor([chunk]).to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                inputs, 
                max_new_tokens=200,
                do_sample=True, 
                top_p=0.95,
                temperature=0.7,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id
            )
        result = tokenizer.decode(outputs[0][len(chunk):], skip_special_tokens=True)
        logging.debug(f"Processed chunk. Result length: {len(result)}")
        return result
    except Exception as e:
        logging.error(f"Error processing chunk: {str(e)}")
        logging.error(traceback.format_exc())
        return f"Error: {str(e)}"

async def run_worker():

    uri = "ws://atom.atomnetwork.xyz:8798"
    headers = {
        "Authorization": f"Bearer {token}"
        # "Authorization": f"Bearer abcd"
    }
    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10,
                extra_headers=headers
            ) as websocket:
                logging.info("Connected to head node")
                
                while True:
                    
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=120)
                        data = json.loads(message)
                        logging.info(f"Received chunk for task {data['task_id']}, chunk {data['chunk_id']}")
                        
                        result = await process_chunk(data['chunk'])
                        
                        response = json.dumps({
                            "task_id": data['task_id'],
                            "chunk_id": data['chunk_id'],
                            "result": result,
                            "is_last": data['is_last']
                        })
                        logging.debug(f"Sending response for task {data['task_id']}, chunk {data['chunk_id']}. Response length: {len(response)}")
                        
                        await asyncio.wait_for(websocket.send(response), timeout=30)
                        logging.info(f"Sent result for task {data['task_id']}, chunk {data['chunk_id']}")
                    except asyncio.TimeoutError:
                        logging.warning("Timeout occurred while processing or sending. Reconnecting...")
                        break
                    except websockets.exceptions.ConnectionClosedError as e:
                        logging.warning(f"Connection closed with error: {e}.")
                        # Check if the close code indicates an authorization error
                        if e.code == 1008:
                            logging.error("Connection closed due to authorization error (1008). Not retrying.")
                            sys.exit(1)
                        else:
                            logging.info("Attempting to reconnect...")
                            break
                    except Exception as e:
                        logging.error(f"Unexpected error: {str(e)}")
                        logging.error(traceback.format_exc())
                        break
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 401:
                logging.error("Authorization failed with status 401. Not retrying.")
                sys.exit(1)
            else:
                logging.error(f"Connection failed with status {e.status_code}. Retrying in 5 seconds...")
        except websockets.exceptions.InvalidURI as e:
            logging.error(f"Invalid URI: {e}. Not retrying.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Connection error: {e}. Retrying in 5 seconds...")
            logging.error(traceback.format_exc())
        
        # Wait before retrying
        await asyncio.sleep(5)


    uri = "ws://atom.atomnetwork.xyz:8798"
    headers = {
        "Authorization": f"Bearer "
    }
    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10,
                extra_headers=headers
            ) as websocket:
                logging.info("Connected to head node")
                
                while True:
                    
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=120)
                        data = json.loads(message)
                        logging.info(f"Received chunk for task {data['task_id']}, chunk {data['chunk_id']}")
                        
                        result = await process_chunk(data['chunk'])
                        
                        response = json.dumps({
                            "task_id": data['task_id'],
                            "chunk_id": data['chunk_id'],
                            "result": result,
                            "is_last": data['is_last']
                        })
                        logging.debug(f"Sending response for task {data['task_id']}, chunk {data['chunk_id']}. Response length: {len(response)}")
                        
                        await asyncio.wait_for(websocket.send(response), timeout=30)
                        logging.info(f"Sent result for task {data['task_id']}, chunk {data['chunk_id']}")
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