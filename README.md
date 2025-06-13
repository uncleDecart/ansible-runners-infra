# Ansible playbook to deploy self-hosted GitHub runners

## What this repo is about?

This playbook connects to remote node, installs all needed packages,
deploys VMs, and registers each of them as a self-hosted runner for specified
organisation using GitHub Access token

## How to use it?

#### Clone this repository

```sh
git clone git@github.com:uncleDecart/ansible-runners-infra.git
```

#### Install ansible

See [this](https://docs.ansible.com/ansible/latest/installation_guide/index.html) doc for more information

### Install ansible.posix collection

```sh
ansible-galaxy collection install ansible.posix
```

#### Define your .env file and inventory file

Ansible main concepts are invenotry and recipes recepies hold a collection of actions which are applied to
specific elements of inventory. Inventory describes machines and holds device specific configuration.

```yaml
    all:
     x64: # for arm runners define them under arm
      hosts: # ... all your machines should be defined under this section
       # ...
       # cool machine name, optional but highly recommended
       kratos:
         # Define your IP address and user in .env file
         ansible_user: "{{ lookup('env', 'KRATOS_USER') }}"
         ansible_host: "{{ lookup('env', 'KRATOS_IP') }}"

         vms:
           # Applied to host instance
           global:
             disk:
               # additional resize apart from base image; qemu-img format
               size: 100G
               # folder to store images; need to have same permissions
               folder: "/var/lib/libvirt/images"

             # folder where cloud init-related files will be stored
             # including iso image
             cloud_init_server_dir: /srv/cloud-init

             # GitHub runner-related information
             github_runner:
               # %repo-owner or organisation%/%repository%
               # can be different for different runners
               url: "{{ lookup('env', 'GH_URL')}}"
               # %repo-owner or organisation%/%repository%
               token: "{{ lookup('env', 'GH_PAT')}}"
               # URL to download the runner; contains version and architecture
               download_url: "https://github.com/actions/runner/releases/download/v2.323.0/actions-runner-linux-x64-2.323.0.tar.gz"
               # WARN: change this if changing VM user
               user: ubuntu
               # Labelts which runner will be registered
               labels: [ ubuntu-latest ]

             # VM image for runners, should be cloud-init compatible
             image_url: "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"

           # Individual virtual machine instances
           instances:
             # name of the runner, it will be registered
             # under this name and the name of virtual machine will
             # be the same. Should be unique across repositories
             # to which they will be connected to
             - name: kratos-runner-1
               # number of VCPUs, which will be assigned to VM
               cpu_count: 8
               # RAM in megabytes assigned to VM
               ram: 16384
               # cpuset: this will tell VMM which pull of cores
               # this particular VM should use CPUs from
               # used for optimisation, leave empty to give VMM
               # control over it
               cpu: "0-7"
             # ...
```

Then you have to define your .env file or write values directrly in inventory file

```sh
KRATOS_IP=%YOUR-DEVICE-REMOTE-IP%
KRATOS_USER=%YOUR-REMOTE-DECIVE_USER%

GH_REPO=%REPO-WHERE-YOU-WANT-YOUR-RUNNERS%
GH_TAC=%GITHUB-ACCESS-TOKEN%
```

**Important:** checkout [this](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token) doc to know how you can get GitHub token. As for permissions

- For repositories within a personal account: `repo`, `workflow`, `write:actions`, `admin`
- For repositories in an organization: `write:actions`, `admin:org` (for organization-wide runners)

Note that for ARM runners the deployment process is a bit different,
so you need to separate them

host_setup will download VMs, deploy them with cloud-init, install all needed
components and register runner within your organisation/repository.

#### Run playbook with invenotry file
You can run it like this

```sh
export $(grep -v '^#' .env | xargs) && ansible-playbook -i inventory.yml playbook.yml
```

*Note:* export command can be run once per shell session

Once runners are registered in the GitHub repository (or organisation) run post installation recipe

```sh
export $(grep -v '^#' .env | xargs) && ansible-playbook -i inventory.yml postinst.yml
```

This will start the runners and install node_exporter and prometheus on host system
for runners monitoring

### Important information

- PAT token will be stored in VMs as well as on playbook it was ran on (host system of inventory machines, in /tmp directory)
- When you run playbook it will delete _ALL_ previously created VMs on the host system
- For each previously created VM on host system it will also delete runner with the same name for the given github url

#### FAQ

#### Q: Can I use it for org wide runners?

A: Yes, just don't specify repository in GITHUB_URL

#### Q: What if I want to deploy those runners locally?
A: in playbook.yml change hosts:all to hosts:localhost

#### Q: Where can I find my GitHub access token?
A: Checkout [this](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token) doc. See permisssions question below as well

#### Q: Why do you base64-encode cloud init script?
A: Because encoding it is most version-compatible approach: depending on cloud-init version
one should or should not backslash $ symbol. And debugging cloud-init scripts is not trivial

#### Q: What kind of permissions do I need for GitHub token?
A:
- For repositories within a personal account: `repo`, `workflow`, `write:actions`
- For repositories in an organization: `write:actions`, `admin:org` (for organization-wide runners)
