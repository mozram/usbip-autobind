from pyudev import Context, Monitor, MonitorObserver
import time
import subprocess

# Create dictionary whether device already bind or not
deviceBindList = []

context = Context()
monitor = Monitor.from_netlink(context)
monitor.filter_by(subsystem='usb')

def bind_device(device):
    subprocess.run(["usbip", "bind", "-b", device])

def print_device_event(device):
    print('>>> background event {0.action}: {0.device_path}'.format(device))
    devicePath = device.device_path
    # parse into device on
    # First, ignore path with colon
    if ':' not in devicePath:
        # Get a deviceBusId out of it.
        deviceBusId = devicePath.rpartition('/')[-1]
        deviceOperation = device.action
        if not any(deviceBusId in s for s in deviceBindList):
            if deviceOperation == 'bind':
                print("Binding device ", deviceBusId)
                deviceBindList.append(deviceBusId)
                # Bind to USBIP. Known issue: when bind with usbip, device will unbind first, then bind again. This cause error since this command will need to run again
                bind_device(deviceBusId)
        else:
            if deviceOperation == 'unbind':
                print("Unbinding device ", deviceBusId)
                deviceBindList.remove(deviceBusId)
        
    # for x in deviceBindList:
    #     print(x)


observer = MonitorObserver(monitor, callback=print_device_event, name='monitor-observer')
observer.daemon
observer.start()

while True:
    time.sleep(1)
    pass
