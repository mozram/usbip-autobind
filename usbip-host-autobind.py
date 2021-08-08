#!/usr/bin/env python3

from pyudev import Context, Monitor, MonitorObserver
import time
import subprocess
import socket, asyncio

SOCKET_HOST = '0.0.0.0'
SOCKET_PORT = 65432

# Create dictionary whether device already bind or not
deviceBindList = []

# Socket user
socketClient = None

context = Context()
monitor = Monitor.from_netlink(context)
monitor.filter_by(subsystem='usb')

def bind_device(device):
    subprocess.run(["usbip", "bind", "-b", device])
    # Play buzzer
    try:
        global socketClient
        socketClient.write(f"Device {device} binded\n".encode())
        # socketClient.drain()
    except:
        pass

def print_device_event(device):
    print('>>> background event {0.action}: {0.device_path}'.format(device))
    devicePath = device.device_path
    # parse into device on
    # First, ignore path with colon
    if ':' in devicePath:
        # Get a deviceBusId out of it.
        deviceBusId = devicePath.split('/')[-2]
        deviceOperation = device.action
        if not any(deviceBusId in s for s in deviceBindList):
            if deviceOperation == 'bind':
                print("Binding device ", deviceBusId)
                deviceBindList.append(deviceBusId)
                # Bind to USBIP
                # Known issue: when bind with usbip, device will unbind first, then bind again. This cause error since this command will need to run again
                # Fix: Bind with colon, unbind without
                bind_device(deviceBusId)
    else:
        # Get a deviceBusId out of it.
        deviceBusId = devicePath.split('/')[-1]
        deviceOperation = device.action
        if any(deviceBusId in s for s in deviceBindList):
            if deviceOperation == 'remove':
                print("Unbinding device ", deviceBusId)
                deviceBindList.remove(deviceBusId)
                global socketClient
                socketClient.write(f"Device {deviceBusId} unbinded\n".encode())
        
    # for x in deviceBindList:
    #     print(x)

observer = MonitorObserver(monitor, callback=print_device_event, name='monitor-observer')
observer.daemon
observer.start()

## Socket notification part
async def handle_client(reader, writer):
    print("Client callback!")
    global socketClient
    socketClient = writer
    while True:
        data = await reader.read(100)  # Max number of bytes to read
        if not data:
            break
        print(data)
        #socketClient = writer
        writer.write(data)
        await writer.drain()  # Flow control, see later
    writer.close()

async def run_server():
    server = await asyncio.start_server(handle_client, SOCKET_HOST, SOCKET_PORT)
    print("Starting socket server...")
    async with server:
        await server.serve_forever()

asyncio.run(run_server())

while True:
    time.sleep(1)
    pass
