import asyncio
import websockets
import logging


# настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def send_audio_chunks(client_id):
    uri = "ws://localhost:8000"
    async with websockets.connect(uri) as websocket:
        audio_chunks = [
            b"\x00",
            b"\x00\x01",
            b"\x00\x01\x02"
        ]

        for chunk in audio_chunks:
            await websocket.send(chunk)
            logger.info(f"Client {client_id}: Sent audio chunk of size {len(chunk)} bytes")

            response = await websocket.recv()
            logger.info(f"Client {client_id}: Received: {response}")


async def main():
    # запуск 3 параллельных клиентов
    clients = [send_audio_chunks(i) for i in range(3)]
    await asyncio.gather(*clients)


if __name__ == "__main__":
    asyncio.run(main())