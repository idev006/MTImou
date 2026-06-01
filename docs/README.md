# MTImou - Document-Driven Architecture Pack

This repository uses a document-driven approach before implementation.

Current operator-facing entrypoints:

- [../README.md](../README.md)
- [multi-camera-runbook.md](./multi-camera-runbook.md)

## Document Index

1. [00-executive-summary.md](./00-executive-summary.md)
2. [01-product-requirements-prd.md](./01-product-requirements-prd.md)
3. [02-system-architecture.md](./02-system-architecture.md)
4. [03-risk-register.md](./03-risk-register.md)
5. [04-delivery-plan.md](./04-delivery-plan.md)
6. [05-operational-runbook.md](./05-operational-runbook.md)
7. [06-uml-diagrams.md](./06-uml-diagrams.md)
8. [07-spike-run-guide.md](./07-spike-run-guide.md)
9. [08-openapi-migration-plan.md](./08-openapi-migration-plan.md)
10. [09-remote-free-dhp2p-status.md](./09-remote-free-dhp2p-status.md)
11. [10-product-test-report-2026-05-31.md](./10-product-test-report-2026-05-31.md)
12. [11-ddns-and-scaleout-plan.md](./11-ddns-and-scaleout-plan.md)
13. [12-production-hardening-plan.md](./12-production-hardening-plan.md)
14. [13-incident-runbook.md](./13-incident-runbook.md)
15. [14-final-acceptance-checklist.md](./14-final-acceptance-checklist.md)
16. [15-cam3-cam4-rollout-template.md](./15-cam3-cam4-rollout-template.md)
17. [16-ui-control-panel-plan.md](./16-ui-control-panel-plan.md)
18. [17-n-camera-secret-model.md](./17-n-camera-secret-model.md)
19. [18-clean-runtime-rewrite-plan.md](./18-clean-runtime-rewrite-plan.md)
20. [19-actors-usecases-sequences.md](./19-actors-usecases-sequences.md)
21. [20-ui-mvvm-ssot-architecture.md](./20-ui-mvvm-ssot-architecture.md)
22. [21-robustness-process-engineering.md](./21-robustness-process-engineering.md)
23. [multi-camera-runbook.md](./multi-camera-runbook.md)
24. [adr/ADR-001-p2p-unofficial-wrapper.md](./adr/ADR-001-p2p-unofficial-wrapper.md)

## Working Model

- Define and approve requirements first.
- Lock architecture decisions in ADRs.
- Deliver incrementally by milestones with entry/exit criteria.
- Operate via SLOs, observability, and incident playbooks.

## Legacy Note

Historical relay-era and spike tools have been moved under [`../legacy`](../legacy).
Some older historical documents may still describe those archived paths because
they document earlier project phases rather than the current production runtime.
