import json
import asyncio
import logging
import websockets
from multiprocessing import Queue, Process


# настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# очереди для межпроцессного взаимодействия
audio_queue = Queue()
result_queue = Queue()


# словарь для хранения подключений клиентов
connected_clients = {}


# идентификаторы клиентов
client_id_counter = 0
client_id_lock = asyncio.Lock()


async def register_client(websocket):
    global client_id_counter
    async with client_id_lock:
        client_id = client_id_counter
        client_id_counter += 1
    connected_clients[client_id] = websocket
    logger.info(f"Client {client_id} connected.")
    return client_id


async def unregister_client(client_id):
    connected_clients.pop(client_id, None)
    logger.info(f"Client {client_id} disconnected.")


async def send_results():
    while True:
        client_id, transcript = await asyncio.to_thread(result_queue.get)
        websocket = connected_clients.get(client_id)
        if websocket:
            msg = json.dumps({"transcript": transcript})
            try:
                await websocket.send(msg)
                logger.info(f"Sent transcript to client {client_id}.")
            except Exception as e:
                logger.error(f"Cant send to client {client_id}: {e}")
                await unregister_client(client_id)


async def consumer_handler(websocket, client_id):
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                await asyncio.to_thread(audio_queue.put, (client_id, message))
                logger.info(f"Received audio chunk from client {client_id}, size {len(message)} bytes.")
            else:
                err_msg = json.dumps({"error": "Only binary messages are accepted"})
                await websocket.send(err_msg)
                logger.warning(f"Sent error message to client {client_id} (non-binary message).")
    except websockets.ConnectionClosed:
        logger.info(f"Connection closed by client {client_id}.")


async def handler(websocket):
    client_id = await register_client(websocket)
    try:
        await consumer_handler(websocket, client_id)
    finally:
        await unregister_client(client_id)


def audio_processor(audio_q: Queue, result_q: Queue):
    while True:
        try:
            client_id, audio_chunk = audio_q.get()
            transcript = f"Mock transcript for audio chunk with size {len(audio_chunk)} bytes"
            result_q.put((client_id, transcript))
            logger.info(f"Processed audio chunk from client {client_id}, generated transcript.")
        except Exception as e:
            logger.error(f"Error in audio_processor: {e}")


async def main():
    processor = Process(target=audio_processor, args=(audio_queue, result_queue), daemon=True)
    processor.start()

    asyncio.create_task(send_results())

    async with websockets.serve(handler, "localhost", 8000):
        logger.info("WebSocket server started at ws://localhost:8000")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())