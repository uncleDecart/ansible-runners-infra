from abc import ABC, abstractmethod
import subprocess
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel
import json
import os
import time 

class VmManager(ABC):
    @abstractmethod
    def deploy(self, vm: str):
        pass

    @abstractmethod
    def destroy(self, vm: str):
        pass

class Instance(BaseModel):
    name: str
    cpu: str
    cpu_count: int
    ram: int

class VMsConfig(BaseModel):
    disk_folder: str
    cloud_init_dir: str
    instances: List[Instance]

def get_vm_state(vm_name):
    """Return the state of the VM using virsh dominfo."""
    try:
        result = subprocess.run(
            ["virsh", "dominfo", vm_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("State:"):
                return line.split(":", 1)[1].strip().lower()
    except subprocess.CalledProcessError as e:
        print(f"Failed to get VM state: {e.stderr}")
        return None

def wait_for_shutdown(vm_name, check_interval=30):
    """Wait until the VM is shut off."""
    print(f"Waiting for VM '{vm_name}' to shut off...")
    while True:
        state = get_vm_state(vm_name)
        if state is None:
            return False
        if state == "shut off":
            print(f"VM '{vm_name}' is shut off.")
            return True
        print(f"VM '{vm_name}' is still {state}. Checking again in {check_interval} seconds...")
        time.sleep(check_interval)

def start_vm(vm_name):
    """Start the VM using virsh start."""
    try:
        subprocess.run(
            ["virsh", "start", vm_name],
            check=True,
            text=True
        )
        print(f"VM '{vm_name}' has been started.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to start VM: {e.stderr}")
        return False

class VirshVmManager(VmManager):
    def __init__(self, password: str, config: Path):
        with open(config, "r") as f:
            data = json.load(f)

        vms_config = VMsConfig.parse_obj(data)

        self.vms = {obj.name: obj for obj in vms_config.instances}
        self.cloud_init_dir = vms_config.cloud_init_dir
        self.disk_folder = vms_config.disk_folder
        self.password = password

    
    def deploy(self, vm: str):
        disk_path = os.path.join(self.disk_folder, vm)
        user_data = os.path.join(self.cloud_init_dir, vm, "user-data")
        meta_data = os.path.join(self.cloud_init_dir, vm, "meta-data")

        cmd = [
            "sudo",
            "qemu-img",
            "create",
            "-f", "qcow2",
            "-b", f"{self.disk_folder}/ubuntu-base.qcow2",
            "-F", "qcow2",
            disk_path
        ]

        print(f"running {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        cmd = [
            "virt-install",
            "--name", vm,
            "--ram", str(self.vms[vm].ram),
            "--vcpus", f"{self.vms[vm].cpu_count},cpuset={self.vms[vm].cpu}",
            "--disk", f"path={disk_path},format=qcow2",
            "--os-variant", "ubuntu22.04",
            "--graphics", "none",
            "--cpu", "host-passthrough,+invtsc",
            "--noautoconsole",
            "--boot", "hd",
            "--network", "default",
            "--cloud-init",
            f"user-data={user_data},meta-data={meta_data}",
            "--import"
        ]

        print(f"Deploying {vm}...")
        print(' '.join(cmd))
        subprocess.run(cmd, check=True)

        # Cloud init shuts the VM off once everything is installed and ready to
        # be used
        if wait_for_shutdown(vm):
            start_vm(vm)

        print(f"Enabling autostart for {vm}...")
        subprocess.run(["virsh", "autostart", vm], check=True)

    def destroy(self, vm: str):
        cmd = [
            "virsh",
            "destroy",
            vm
        ]
        print(f"Destroying {vm}...")
        subprocess.run(cmd, check=False)

        cmd = [
            "virsh",
            "undefine",
            vm,
            "--nvram",
            "--remove-all-storage"
        ]
        print(f"Undefining {vm}...")
        subprocess.run(cmd, check=True)

