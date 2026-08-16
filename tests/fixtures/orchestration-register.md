> index

# Orchestration Register

The Orchestration Registry provides a trusted, shared view of who is involved in a specific supply chain context.

The three core components; the Association Registry, the Orchestration Registry, and the BDI Connector together form a layered model.

Association Registry issues a BDI Verifiable Association Data (BVAD) token. Orchestration Registry issues a BDI Verifiable Orchestration Data (BVOD) token. The BDI Connector validates the received BVAD and BVOD tokens.

| Element | Responsibility |
| Association Register | Membership management |
| Orchestrations Register | Registration of supply chain context |
| BDI Connector | Validation and enforcement |

Data owners remain in control: Each data custodian (terminal, carrier, logistics service provider) implements its own Local Policy Engine and determines what data is shared.

To enable a low-threshold implementation for a data provider, it is possible to configure the BDI Connector as a standalone Policy Engine; the Connector functions as both a Policy Decision Point (PDP) and a Policy Enforcement Point (PEP). The Association Registry and the Orchestration Registry jointly act as Policy Information Points (PIPs).

A possible implementation is a multi-tenant Orchestration Registry, where each transport orchestrator manages only its own transport dossiers. The Orchestration Registry acts as a Policy Information Point.

---

# Agent Instructions
