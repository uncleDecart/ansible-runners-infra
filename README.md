# Ansible playbook to deploy self-hosted GitHub runners 

## What this repo is about?

This playbook connects to remote node, installs all needed packages,
deploys 4 VMs, and registers each of them as a self-hosted runner for specified
organisation using GitHub Access token

## How to do it?

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

#### Define your .env file

```sh
LINGUINI_IP=%YOUR-DEVICE-REMOTE-IP%
LINGUINI_USER=%YOUR-REMOTE-DECIVE_USER%

GH_REPO=%REPO-WHERE-YOU-WANT-YOUR-RUNNERS%
GH_TAC=%GITHUB-ACCESS-TOKEN%
```

#### Run your playbook

```sh
 run export $(grep -v '^#' .env | xargs) && ansible-playbook -i inventory.yml playbook.yml
```

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
