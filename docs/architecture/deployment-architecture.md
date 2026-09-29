# Deployment architecture

Status: planned application topology. No installer or runtime is implemented.

```mermaid
flowchart LR
    subgraph W[Approved local workstation]
        U[Visual builder] --> D[Pipeline definitions]
        D --> E[Execution engine]
        K[Credential provider] -.-> E
        E --> R[Local artifacts and run metadata]
    end
    S[Approved files / SQL / REST] --> E
    R --> C[Authorized analytics / ML consumers]
```

The UI/engine process boundary, loopback binding, packaging and storage locations are undecided. If an API is introduced, evaluate authentication, origin checks and least-privilege access even on loopback. See [environment and rollout plan](../deployment/deployment-plan.md).
