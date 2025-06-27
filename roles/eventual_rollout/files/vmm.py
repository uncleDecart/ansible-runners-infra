from abc import ABC, abstractmethod
import subprocess
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel
import json
import os

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

