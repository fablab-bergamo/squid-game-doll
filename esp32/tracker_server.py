import asyncio
from constants import SERVER_HOST, SERVER_PORT

class TrackerServer:
    def __init__(self, head_controller, eyes_controller, laser_controller, test_manager):
        self.head = head_controller
        self.eyes = eyes_controller
        self.laser = laser_controller
        self.test_manager = test_manager
        self.shutdown_event = asyncio.Event()
        
    async def handle_client(self, reader, writer):
        """Handle client requests and send responses"""
        print("Client connected")
        await self.test_manager.on_client_connect()
        
        try:
            while True:
                await asyncio.sleep_ms(5)
                try:
                    data = await asyncio.wait_for(reader.read(128), timeout=0.5)
                    if not data:
                        print("Client disconnected (EOF received)")
                        break
                    request = data.decode("utf8").strip()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error reading request: {e}")
                    await asyncio.sleep(0.1)
                    continue

                if not request:
                    continue

                print(f"<-- {request}")
                response = await self._process_request(request)
                print(f"--> {response}")
                
                try:
                    writer.write(str(response).encode("utf8"))
                    await writer.drain()
                    if request == "quit":
                        break
                except Exception as e:
                    print(f"Error while responding: {e}")
                    break
                    
        except Exception as ex:
            print(f"Unhandled error in client handler: {ex}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"Error closing connection: {e}")
            print("Client handler terminating")
            await self.test_manager.on_client_disconnect()
            self.shutdown_event.set()
            
    async def _process_request(self, request):
        """Process individual client requests"""
        try:
            if request.startswith("("):
                # Parse coordinate tuple (e.g., "(120.5, 90.0)")
                try:
                    target_coord = eval(request)
                    await self.laser.set_target(*target_coord)
                    return "1"
                except Exception as e:
                    print(f"Error parsing coordinates '{request}': {e}")
                    return "0"
            elif request == "angles":
                return await self.laser.get_angles()
            elif request == "limits":
                return await self.laser.get_limits()
            elif request == "test":
                await self.laser.start_test_mode()
                return "1"
            elif request == "stop":
                await self.laser.stop_test_mode()
                return "1"
            elif request == "off":
                await self.laser.laser_off()
                return "1"
            elif request == "on":
                await self.laser.laser_on()
                return "1"
            elif request == "h0":
                await self.head.get_position_0()
                return "1"
            elif request == "h1":
                await self.head.get_position_1()
                return "1"
            elif request == "e0":
                await self.eyes.turn_off()
                return "1"
            elif request == "e1":
                await self.eyes.turn_on()
                return "1"
            elif request == "quit":
                return "1"
            else:
                return "0"
        except Exception as e:
            print(f"Error processing request '{request}': {e}")
            return "0"

    async def run_server(self):
        """Run the TCP server with automatic restart"""
        print("Starting server...")
        while True:
            self.shutdown_event.clear()
            try:
                server = await asyncio.start_server(self.handle_client, SERVER_HOST, SERVER_PORT)
                print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
                async with server:
                    await self.shutdown_event.wait()
            except Exception as e:
                print(f"Server error: {e}")
            print("Restarting server...")
            await asyncio.sleep(2)