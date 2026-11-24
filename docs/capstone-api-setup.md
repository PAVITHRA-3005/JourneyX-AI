# Capstone API credentials (Track B)

Per **Track_B_Inference_API_Learner_Guide.docx.pdf** and **VM02_Embeddings_Access/Embedding_API_Quickstart.md**.

## Files (local, not committed)

| File | Purpose |
|------|---------|
| `config/credentials.local.yaml` | Chat + embedding keys and cert paths |
| `.env` | Optional overrides (also gitignored) |
| `certs/vm05-ca.crt` | HTTPS verify for **chat** (group 031–045 → port 1033) |
| `certs/vm02-ca.crt` | HTTPS verify for **embeddings** (port 1035) |

## Setup

```powershell
python scripts/setup_credentials.py
# Edit config/credentials.local.yaml if keys differ
python scripts/test_capstone_api.py

# Data/retrieval closure (production ingest + live baseline + eval refresh):
powershell -ExecutionPolicy Bypass -File scripts/complete_live_baseline.ps1
```

## Group URL mapping (chat)

| Groups | Base URL | CA file |
|--------|----------|---------|
| 001–015 | `https://103.42.50.41:1031/v1` | vm07-ca.crt |
| 016–030 | `https://103.42.50.41:1032/v1` | vm06-ca.crt |
| **031–045** | `https://103.42.50.41:1033/v1` | **vm05-ca.crt** |
| 046–065 | `https://103.42.50.41:1034/v1` | vm04-ca.crt |

Embeddings (all groups): `https://103.42.50.41:1035/v1`, model `bge-small-en-v1.5`, cert `vm02-ca.crt`.

## Network

Hosts at `103.42.50.41` are reachable from **campus / IITKGP VPN** only. Off-network you will see `WinError 10054` or TLS connect errors — run `scripts/complete_live_baseline.ps1` once VPN is up.

## Security

- Never commit `credentials.local.yaml` or `.env`.
- If a key was pasted in chat or email, ask the coordinator for a replacement.