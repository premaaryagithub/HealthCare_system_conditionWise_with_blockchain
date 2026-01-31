'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const grpc = require('@grpc/grpc-js');
const express = require('express');
const {
  connect,
  signers,
} = require('@hyperledger/fabric-gateway');

function mustGetEnv(name) {
  const v = process.env[name];
  if (!v) {
    throw new Error(`${name} not set`);
  }
  return v;
}

function readFirstFile(dir) {
  const files = fs.readdirSync(dir).filter(f => !f.startsWith('.'));
  if (files.length === 0) {
    throw new Error(`no files in ${dir}`);
  }
  return fs.readFileSync(path.join(dir, files[0]));
}

function newGateway() {
  const mspId = mustGetEnv('FABRIC_MSP_ID');
  const cryptoPath = mustGetEnv('FABRIC_CRYPTO_PATH');
  const peerEndpoint = mustGetEnv('FABRIC_PEER_ENDPOINT');
  const tlsCertPath = mustGetEnv('FABRIC_TLS_CERT_PATH');

  const certPath = path.join(cryptoPath, 'users', 'Admin@org1.example.com', 'msp', 'signcerts');
  const keyPath = path.join(cryptoPath, 'users', 'Admin@org1.example.com', 'msp', 'keystore');

  const certificate = readFirstFile(certPath);
  const privateKeyPem = readFirstFile(keyPath);
  const tlsRootCert = fs.readFileSync(tlsCertPath);

  const identity = {
    mspId,
    credentials: certificate,
  };

  const privateKey = crypto.createPrivateKey(privateKeyPem);
  const signer = signers.newPrivateKeySigner(privateKey);

  const tlsCredentials = grpc.credentials.createSsl(tlsRootCert);
  const client = new grpc.Client(peerEndpoint, tlsCredentials, {
    'grpc.ssl_target_name_override': 'peer0.org1.example.com',
  });

  const gateway = connect({
    client,
    identity,
    signer,
  });

  return { gateway, client };
}

function jsonError(res, code, msg) {
  res.status(code).json({ error: msg });
}

function describeError(e) {
  try {
    const parts = [];
    if (e && e.message) parts.push(e.message);
    if (e && e.details) parts.push(String(e.details));
    if (e && e.cause && e.cause.message) parts.push(`cause: ${e.cause.message}`);
    return parts.filter(Boolean).join(' | ') || String(e);
  } catch (_err) {
    return String(e);
  }
}

function safeJsonFromBuffer(buf) {
  // Fabric Gateway returns Uint8Array. Uint8Array.toString() yields "1,2,3" which is not JSON.
  // Always decode as UTF-8 bytes.
  const s = Buffer.from(buf).toString('utf8');
  try {
    return { ok: true, json: JSON.parse(s) };
  } catch (err) {
    return { ok: false, raw: s, parse_error: String(err && err.message ? err.message : err) };
  }
}

function truncate(s, maxLen) {
  if (!s) return '';
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen) + '...<truncated>';
}

async function main() {
  const channelName = mustGetEnv('FABRIC_CHANNEL');
  const chaincodeName = mustGetEnv('FABRIC_CHAINCODE');
  const port = Number(process.env.PORT || '8800');

  const app = express();
  app.use(express.json({ limit: '2mb' }));

  app.get('/health', (req, res) => res.json({ ok: true }));

  app.post('/records', async (req, res) => {
    let gw;
    try {
      gw = newGateway();
      const network = gw.gateway.getNetwork(channelName);
      const contract = network.getContract(chaincodeName);
      await contract.submitTransaction('createRecord', JSON.stringify(req.body));
      res.json({ ok: true });
    } catch (e) {
      console.error(e);
      jsonError(res, 400, describeError(e));
    } finally {
      if (gw) {
        gw.gateway.close();
        gw.client.close();
      }
    }
  });

  app.put('/records/:patientId', async (req, res) => {
    let gw;
    try {
      gw = newGateway();
      const network = gw.gateway.getNetwork(channelName);
      const contract = network.getContract(chaincodeName);
      await contract.submitTransaction('updateRecord', JSON.stringify(req.body));
      res.json({ ok: true });
    } catch (e) {
      console.error(e);
      jsonError(res, 400, describeError(e));
    } finally {
      if (gw) {
        gw.gateway.close();
        gw.client.close();
      }
    }
  });

  app.get('/records/:patientId/latest', async (req, res) => {
    let gw;
    try {
      gw = newGateway();
      const network = gw.gateway.getNetwork(channelName);
      const contract = network.getContract(chaincodeName);
      const out = await contract.evaluateTransaction('getLatestRecord', req.params.patientId);
      const parsed = safeJsonFromBuffer(out);
      if (!parsed.ok) {
        res.status(500).json({
          error: `chaincode returned non-JSON output: ${parsed.parse_error}`,
          raw: truncate(parsed.raw, 2000),
        });
        return;
      }
      res.json(parsed.json);
    } catch (e) {
      console.error(e);
      jsonError(res, 400, describeError(e));
    } finally {
      if (gw) {
        gw.gateway.close();
        gw.client.close();
      }
    }
  });

  app.get('/records/:patientId/history', async (req, res) => {
    let gw;
    try {
      gw = newGateway();
      const network = gw.gateway.getNetwork(channelName);
      const contract = network.getContract(chaincodeName);
      const out = await contract.evaluateTransaction('getHistory', req.params.patientId);
      const parsed = safeJsonFromBuffer(out);
      if (!parsed.ok) {
        res.status(500).json({
          error: `chaincode returned non-JSON output: ${parsed.parse_error}`,
          raw: truncate(parsed.raw, 2000),
        });
        return;
      }
      res.json({ patient_id: req.params.patientId, history: parsed.json });
    } catch (e) {
      console.error(e);
      jsonError(res, 400, describeError(e));
    } finally {
      if (gw) {
        gw.gateway.close();
        gw.client.close();
      }
    }
  });

  app.post('/records/:patientId/audit', async (req, res) => {
    let gw;
    try {
      gw = newGateway();
      const network = gw.gateway.getNetwork(channelName);
      const contract = network.getContract(chaincodeName);
      await contract.submitTransaction('appendAuditLog', req.params.patientId, JSON.stringify(req.body));
      res.json({ ok: true });
    } catch (e) {
      console.error(e);
      jsonError(res, 400, describeError(e));
    } finally {
      if (gw) {
        gw.gateway.close();
        gw.client.close();
      }
    }
  });

  app.listen(port, () => {
    console.log(`fabric-gateway-service listening on :${port}`);
  });
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
