# Hyperledger Fabric network (Windows)

This project targets **Hyperledger Fabric test-network**.

## Recommendation (best for this project): WSL2 + Docker Desktop

For a Windows laptop/PC, the most stable way to run Fabric is:

- Windows 10/11
- **WSL2 (Ubuntu)**
- **Docker Desktop** (using the WSL2 backend)

Why this is best (matches your prompt requirements):

- Fabric tooling and scripts are Linux-first.
- The official `fabric-samples/test-network` scripts run cleanly in bash.
- You avoid Windows-native path/permission issues.
- Your Python services + UI can still run on Windows; only Fabric runs inside WSL2.

## Option A: WSL2 bring-up (recommended)

### A1) Install prerequisites (Windows)

1. Install **WSL2** and Ubuntu:

```powershell
wsl --install -d Ubuntu
```

2. Install **Docker Desktop**:

- Enable: "Use the WSL 2 based engine"
- Enable integration for your Ubuntu distro.

3. Reboot if asked.

### A2) Prepare Ubuntu (inside WSL2)

Open **Ubuntu** terminal and run:

```bash
sudo apt-get update
sudo apt-get install -y \
  git curl jq \
  ca-certificates \
  build-essential \
  docker.io docker-compose-plugin
```

Confirm docker works in WSL2:

```bash
docker ps
```

If you get permissions errors, run:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### A3) Clone fabric-samples (inside WSL2)

Inside WSL2, choose a folder (recommended: your WSL home directory):

```bash
cd ~
git clone https://github.com/hyperledger/fabric-samples.git
cd fabric-samples
```

### A4) Download Fabric binaries and images (inside WSL2)

```bash
curl -sSL https://bit.ly/2ysbOFE | bash -s
```

This downloads:

- Fabric peer/orderer binaries
- Fabric CA binaries
- Docker images

### A5) Start the test-network (inside WSL2)

```bash
cd ~/fabric-samples/test-network
./network.sh down
./network.sh up createChannel -c mychannel -ca
```

### A6) Deploy chaincode (inside WSL2)

Later, after we add chaincode in this repo under `chaincode/`, we will package/deploy it from WSL2.

General pattern:

```bash
./network.sh deployCC -c mychannel -ccn healthcare -ccp <PATH_TO_CHAINCODE> -ccl <language>
```

Where:

- `-ccn` is chaincode name
- `-ccp` is chaincode path
- `-ccl` is `go` or `javascript`/`typescript`

### A7) Making Windows repo visible in WSL2 (important)

If your project lives on Windows at:

`C:\Users\prems\Desktop\BTP_project`

You can access it from WSL2 as:

`/mnt/c/Users/prems/Desktop/BTP_project`

So chaincode path may look like:

```bash
/mnt/c/Users/prems/Desktop/BTP_project/chaincode/healthcare
```

## Option B: “Native Windows” bring-up (not recommended)

Fabric test-network relies heavily on bash scripts and Linux tooling.
Running it natively on Windows is possible only through heavy workarounds (Git Bash/MSYS2) and frequently breaks due to:

- path differences (`C:\...` vs `/...`)
- file permissions
- Docker volume mount edge cases

If you *must* do native, the practical route is still:

- Docker Desktop + Git Bash

But expect to debug environment issues that do not exist in WSL2.

## Next integration step for this repo

Once the network is up:

- We will add `chaincode/` implementing:
  - `createRecord`
  - `getLatestRecord`
  - `updateRecord`
- Then implement a Python Fabric Gateway adapter so `TrustedAuthorityCore` can switch from `MockFabricAdapter` to `FabricGatewayAdapter` with the same API.
