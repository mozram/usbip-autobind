# USB Support for WSL2
Ever since WSL/WSL2 introduced, there is no proper USB support for it due to technical limitation. This page will describe a workaround to get USB working in WSL2 only.

# Preface
This method utilize Raspberry Pi 3/4 as USB host, which will bind the USB device so client can attach to it an treat it as normal USB device.
Two scripts is provided to enable seamless discovery, binding and attaching the USB device.

# Pre-requisite
1. Raspberry Pi 3/4 (tested). In theory, other SBC/computer should work too. Windows device as host is possible, but due to some technical limitation, it will not be discussed here.
2. WSL2 Kernel with support for USB device and USBIP stack

# Steps
## 1. Setting up our USB host (Raspberry Pi OS)
1. Install usbip:
    `sudo apt install usbip`
2. Load usbip module and autoload it during startup:
    ```bash
    sudo modprobe usbip_host
    echo 'usbip_host' >> /etc/modules
    ```
3. Start usbip host daemon and create `systemd` entry for it:
    ```bash
    sudo nano /lib/systemd/system/usbipd.service
    ```
    Copy and paste the following service definition:
    ```bash
    [Unit]
    Description=usbip host daemon
    After=network.target

    [Service]
    Type=forking
    ExecStart=/usr/sbin/usbipd -D

    [Install]
    WantedBy=multi-user.target
    ```
    Save it, and enable it:
    ```bash
    # reload systemd, enable, then start the service
    sudo systemctl --system daemon-reload
    sudo systemctl enable usbipd.service
    sudo systemctl start usbipd.service
    ```
4. Run `usbip-host-autobind.py` to automatically detect and bind USB device to USBIP. Optionally, create `systemd` service to run this script automatically at startup:
    ```bash
    sudo nano /lib/systemd/system/usbip-autobind.service
    ```
    Copy and paste the following service definition:
    ```bash
    [Unit]
    Description=usbip host daemon
    After=network.target

    [Service]
    Type=simple
    ExecStart=usbip-host-autobind.py

    [Install]
    WantedBy=multi-user.target
    ```
    Save it, and enable it:
    ```bash
    # reload systemd, enable, then start the service
    sudo systemctl --system daemon-reload
    sudo systemctl enable usbip-autobind.service
    sudo systemctl start usbip-autobind.service
    ```

## 2. Rebuilding WSL2 Kernel
By default, Microsoft exclude USB device and USBIP support from its kernel. We must enable this manually by rebuilding the kernel in order to take advantage of it.

Assuming the WSL2 running on Ubuntu.

1. Install necessary build tools:
    ```bash
    # Install the needed packages
    # Source: https://github.com/microsoft/WSL2-Linux-Kernel/blob/7015d6023d60b29c3be4c6a398bed923b48b4341/README-Microsoft.WSL2
    sudo apt install -y build-essential flex bison libssl-dev libelf-dev
    ```
2. Get kernel from Microsoft at https://github.com/microsoft/WSL2-Linux-Kernel:
    ```bash
    wget https://github.com/microsoft/WSL2-Linux-Kernel/archive/refs/tags/linux-msft-wsl-5.10.43.3.zip
    unzip https://github.com/microsoft/WSL2-Linux-Kernel/archive/refs/tags/linux-msft-wsl-5.10.43.3.zip
    cd WSL2-Linux-Kernel-linux-msft-wsl-5.10.43.3
    ```
    Get WSL2 optimized kernel config:
    ```bash
    cp Microsoft/config-wsl .config
    ```
    There is no restriction which kernel version to use. We can even use from upstream kernel at https://www.kernel.org/. The most important step is to use default WSL2 kernel config before we do our own modification.
3. Run menuconfig to select necessary kernel modules:
    ```bash
    make menuconfig
    ```
    Navigate in menuconfig to select the USB kernel modules. These suited my needs, but add more or less as you see fit:
    ```
    Device Drivers->USB support[*]
    Device Drivers->USB support->Support for Host-side USB[M]
    Device Drivers->USB support->Enable USB persist by default[*]
    Device Drivers->USB support->USB Modem (CDC ACM) support[M]
    Device Drivers->USB support->USB Mass Storage support[M]
    Device Drivers->USB support->USB/IP support[M]
    Device Drivers->USB support->VHCI hcd[M]
    Device Drivers->USB support->VHCI hcd->Number of ports per USB/IP virtual host controller(8)
    Device Drivers->USB support->Number of USB/IP virtual host controllers(1)
    Device Drivers->USB support->USB Serial Converter support[M]
    Device Drivers->USB support->USB Serial Converter support->USB FTDI Single Port Serial Driver[M]
    Device Drivers->USB support->USB Physical Layer drivers->NOP USB Transceiver Driver[M]
    Device Drivers->Network device support->USB Network Adapters[M]
    Device Drivers->Network device support->USB Network Adapters->[Deselect everything you don't care about]
    Device Drivers->Network device support->USB Network Adapters->Multi-purpose USB Networking Framework[M]
    Device Drivers->Network device support->USB Network Adapters->CDC Ethernet support (smart devices such as cable modems)[M]
    Device Drivers->Network device support->USB Network Adapters->Multi-purpose USB Networking Framework->Host for RNDIS and ActiveSync devices[M]
    ```
4. Build the kernel:
    ```bash
    # Do not use all core to compile, else you may stumble an error. I recommend using half of the total thread your computer have. For example mine has 12cores, and I use -j 6
    make -j 6
    ```
    Once finished, copy out the kernel outside WSL so we can replace the kernel later.
5. Build kernel modules:
    ```bash
    sudo make modules_install -j 6
    sudo make install -j 6
    ```
    You should get something looks like this:
    ```
    INSTALL drivers/hid/hid-generic.ko
    INSTALL drivers/hid/hid.ko
    INSTALL drivers/hid/usbhid/usbhid.ko
    INSTALL drivers/net/mii.ko
    INSTALL drivers/net/usb/cdc_ether.ko
    INSTALL drivers/net/usb/rndis_host.ko
    INSTALL drivers/net/usb/usbnet.ko
    INSTALL drivers/usb/class/cdc-acm.ko
    INSTALL drivers/usb/common/usb-common.ko
    INSTALL drivers/usb/core/usbcore.ko
    INSTALL drivers/usb/serial/ftdi_sio.ko
    INSTALL drivers/usb/phy/phy-generic.ko
    INSTALL drivers/usb/serial/usbserial.ko
    INSTALL drivers/usb/storage/usb-storage.ko
    INSTALL drivers/usb/usbip/vhci-hcd.ko
    DEPMOD  5.10.43.3-microsoft-standard
    ```
6. Build USBIP tools:
    ```bash
    cd tools/usb/usbip
    sudo ./autogen.sh
    sudo ./configure
    sudo make install -j 6
    ```
    Copy USBIP tools library to location that USBIP tools can get to them:
    ```bash
    sudo cp libsrc/.libs/libusbip.so.0 /lib/libusbip.so.0
    ```
7. Load the modules. Create a script to do all at once call `startusb.sh`:
    ```bash
    #!/bin/bash
    sudo modprobe usbcore
    sudo modprobe usb-common
    sudo modprobe hid-generic
    sudo modprobe hid
    sudo modprobe usbnet
    sudo modprobe cdc_ether
    sudo modprobe rndis_host
    sudo modprobe usbserial
    sudo modprobe usb-storage
    sudo modprobe cdc-acm
    sudo modprobe ftdi_sio
    sudo modprobe usbip-core
    sudo modprobe vhci-hcd
    echo $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
    ```
    Mark it as executable:
    ```bash
    sudo chmod +x startusb.sh
    ```
8. Replace the kernel via WSL2 config. This can be done by creating .wslconfig under your user profile folder. For example if the user is Jamal, the config should be `C:\Users\Jamal\.wslconfig`. Add the following the file, assuming the folder of the kernel is `C:\Users\Jamal\.kernel\`:
    ```
    [wsl2]
    kernel=c:\\Users\\soul\\.kernel\\kernel
    ```
    Make sure the kernel name match with the path above.

9. Restart WSL via CMD:
    ```bash
    C:\Users\mzramli>wsl --shutdown
    ```
10. Run the `startusb.sh` script. Finally, run `usbip-client-autoattach.py` to automatically detect and attach USB device to USBIP in WSL2.

# USBIP Auto Bind
USBIP Host: Run `usbip-host-autobind.py`
USBIP Client: Run `usbip-client-autoattach.py`

## Reference
https://derushadigital.com/other%20projects/2019/02/19/RPi-USBIP-ZWave.html

https://gist.github.com/cerebrate/d40c89d3fa89594e1b1538b2ce9d2720

https://falco.org/blog/falco-wsl2-custom-kernel/

https://github.com/rpasek/usbip-wsl2-instructions
