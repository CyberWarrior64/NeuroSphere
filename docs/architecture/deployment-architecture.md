# NeuroSphere V2 Deployment Architecture

## Current deployment

The project is at /mnt/neurosphere/NeuroSphere/ai-engine on Ubuntu. Its Python environment runs FastAPI on loopback port 8000. There is no Compose deployment, Java/React service, MySQL, RabbitMQ, TLS proxy, or hosted security boundary in the workspace. Use SSH tunneling for development; do not bind AI publicly.

## Target topology

    Browser --HTTPS--> reverse proxy / ingress
                         |-- React assets
                         |-- Spring Boot platform API
                                |-- MySQL (private network)
                                |-- RabbitMQ (private network)
                                |-- FastAPI AI engine (private network)
                                |-- collectors and lab services

Separate networks: edge (proxy/UI/API), platform (Java and internal calls), data (DB/broker), and isolated lab (twin/Cowrie). Do not publish database, broker, AI, or management ports. Admin access uses SSH/VPN and separate credentials.

## Configuration and hardening

- Keep secrets out of source/images; inject through development environment and an approved deployment secret store.
- Separate demo, development, and production configurations.
- Pin dependencies/base images and record model artifact hashes.
- Use non-root containers, read-only filesystems where practical, dropped Linux capabilities, and explicit CPU/memory limits.
- Packet capture needs narrowly scoped capabilities and an approved interface allow-list; no default privileged host networking.
- Restrict health/metrics endpoints. Add TLS, auth/RBAC, request-size and rate limits before hosted exposure.

## Availability and data

Use readiness checks for required dependencies and model artifacts; keep liveness separate. Back up database/configuration and verify restore. Protect capture files with permissions, checksums, provenance, and retention; avoid PCAP in MySQL. Use structured logs, request IDs, bounded retention, resource monitoring, graceful shutdown, and durable idempotent consumers.

## Development access

For the present loopback API, Windows can forward a local port:

    ssh -L 8000:127.0.0.1:8000 cse-cy-02@100.70.85.104

Then browse to http://127.0.0.1:8000/ and leave the SSH session open. If local 8000 is busy, forward local 8765 to remote 127.0.0.1:8000. Do not publish the service directly to the internet.

## Production gate

Public deployment requires an approved threat model, TLS, authentication/RBAC, migration/backup policy, dependency review, retention decision, operational monitoring, and incident/rollback runbooks.
