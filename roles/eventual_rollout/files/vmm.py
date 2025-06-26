from abc import ABC, abstractmethod
import subprocess
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel

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
    def __init__(self, config: Path):
        with open(config, "r") as f:
            data = json.load(f)

        vms_config = VMsConfig.parse_obj(data)

        self.vms = {obj.name: obj for obj in vms_config.instances}
        self.disk_path = vms_config.disk_path
        self.user_data = vms_config.user_data
        self.meta_data = vms_config.meta_data
        self.os_variant = vms_config.os_variant
    
    def deploy(self, vm: str):
        disk_path = Path(self.disk_folder) / vm
        user_data = Path(self.cloud_init_dir) / vm / "user-data"
        meta_data = Path(self.cloud_init_dir) / vm / "meta-data"
        cmd = [
            "virt-install",
            "--name", name,
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
        subprocess.run(cmd, check=True)

        print(f"Enabling autostart for {vm}...")
        subprocess.run(["virsh", "autostart", name], check=True)
