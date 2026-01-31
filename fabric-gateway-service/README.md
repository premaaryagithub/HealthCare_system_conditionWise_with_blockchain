# Fabric Gateway Service (WSL2)

This service runs **inside WSL2** and exposes a small REST API that your Python Trusted Authority can call.

It uses the official **Node Fabric Gateway** client to talk to the Fabric test-network.

## Prerequisites

- Fabric test-network up (see `fabric-network/README.md`)
- Chaincode deployed with name `healthcare` on channel `mychannel`

## Install

Inside WSL2:

```bash
cd /mnt/c/Users/prems/Desktop/BTP_project/fabric-gateway-service
npm install
```

## Run

Inside WSL2 (adjust paths if your fabric-samples location differs):

```bash
export PORT=8800
export FABRIC_CHANNEL=mychannel
export FABRIC_CHAINCODE=healthcare
export FABRIC_MSP_ID=Org1MSP
export FABRIC_PEER_ENDPOINT=localhost:7051
export FABRIC_CRYPTO_PATH=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com
export FABRIC_TLS_CERT_PATH=~/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt

node index.js
```

## REST API

- `GET /health`
- `POST /records` (createRecord)
- `PUT /records/:patientId` (updateRecord)
- `GET /records/:patientId/latest` (getLatestRecord)
- `GET /records/:patientId/history` (getHistory)
- `POST /records/:patientId/audit` (appendAuditLog)
