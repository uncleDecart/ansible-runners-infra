#!/usr/bin/env python3

# Eventual rollout of GitHub self-hosted runners.
# 
# Downtime is painful, in case you want to re-deploy
# existing runners with changed environment, plainly
# stopping everything would generate ranting, this script
# helps you avoid that. In a nutshell it does following things
#
# 1) It deploys all new VMs that you specified, which are not
#    registered runners under `repo` you specified
#
# 2) For each registered runner that you want to re-deploy it will
#   2a) Wait for the first available runner (i.e. in idle state)
#   2b) Delete that runner from GitHub (so it can't be used)
#   2c) Delete Virtual Machine of the runner
#   2d) Deploy new one and register the machine
#
# This way you will just have 1 machines less at the given time.
#
# Current assumptions of this script is that we use virsh to manage VMs
# and that all of them come with cloud-init scirpt, which is shared across
# VMs as bootable iso
# NOTE: This script is expected to be invoked by ansible,
# hence json output in this specific format
#
# NOT IMPLEMENTED
# One hyperparameter is the number of machines K you allow to be down at
# the same time (i.e. two new runners are deployed simultaneously). 
#

# https://github.com/PyGithub/PyGithub package
from github import Github, Auth
from typing import Dict, Set
import argparse
import json
import sys

from vmm import VirshVmManager, VmManager

# Typing hint assumes runner name and its busy status
def get_runners(ghc: Github, org_name: str) -> Dict[str, bool]:
    runners = ghc.get_organization(org_name).get_self_hosted_runners()
    return {runner.name: runner.busy for runner in runners}

def rollout(ghc: Github, vms: Set[str], org_name: str, vmm: VmManager) -> str:
    # Deploy runners which are not registered
    runners = get_runners(ghc, org_name)
    new_runners = [vm for vm in vms if vm not in runners]
    if new_runners:
        vmm.deploy(new_runners)
        vms -= set(new_runners)

    # Recycle idle VMs
    while vms:
        runners = get_runners(ghc, org_name)

        for vm in list(vms):
            if vm not in runners:
                print(f"WARN: runner is not registered to GitHub: {vm}")
                vms.remove(vm)
                break
            elif not runners[vm]:  # If runner is not busy
                org = ghc.get_organization(org_name)
                org.delete_self_hosted_runner(vm)
                vmm.destroy(vm)
                vmm.deploy(vm)
                vms.remove(vm)
                break
    return "Rollout completed successfully."

def main():
    parser = argparse.ArgumentParser(description="Eventual rollout of GitHub Self-Hosted VMs")
    parser.add_argument("--vms", required=True, help="Comma-separated list of VM names to (re)deploy")
    parser.add_argument("--config", required=True, help="Path to VmManager config")
    parser.add_argument("--token", required=True, help="GitHub PAT token")
    parser.add_argument("--org", required=True, help="GitHub organization name")

    args = parser.parse_args()

    try:
        auth = Auth.Token(args.token)
        client = Github(auth=auth)
        vm_names = set(args.vms.split(","))
        vmm = VirshVmManager(Path(args.cloud_init))  # Replace with your actual implementation

        result = rollout(client, vm_names, args.org, vmm)
        print(json.dumps({"changed": True, "msg": result}))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"failed": True, "msg": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
