#!/usr/bin/env python3
'''
1. Event driven. Host will notify client whether a device is connected or not.
2. Check whether device is already attached or not by checking usbip port and have a list of it
3. Attach if device is available to attach. Play buzzer when attached
'''


import asyncio
import subprocess

SOCKET_HOST = '192.168.10.1'
SOCKET_PORT = 65432

class EchoClient(asyncio.Protocol):
    message = 'Client Echo'

    def connection_made(self, transport):
        transport.write(self.message.encode())
        print('data sent: {}'.format(self.message))

    def data_received(self, data):
        print('data received: {}'.format(data.decode()))
        if 'binded' in data.decode():
            deviceId = data.decode().split(' ')[-2]
            print(deviceId)
            # Check device is valid or not
            result = subprocess.run(["usbip", "list", "-r", SOCKET_HOST], capture_output=True)
            if deviceId in result.stdout.decode():
                print(result.stdout.decode())
                # attach device
                result = subprocess.run(["usbip", "attach", "-r", SOCKET_HOST, "-b", deviceId], capture_output=True)
                print(result.stdout.decode())
                print(result.stderr.decode())

    def connection_lost(self, exc):
        print('server closed the connection')
        asyncio.get_event_loop().stop()

loop = asyncio.get_event_loop()
coro = loop.create_connection(EchoClient, SOCKET_HOST, 65432)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()