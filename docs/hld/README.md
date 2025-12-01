# High-Level Designs

This directory contains High-Level Design (HLD) documents for complex features in the Matching Service.

## HLD Index

| Feature | Version | Status | Date |
|---------|---------|--------|------|
| [Resonance v2 Matching Evolution](resonance-v2-matching-evolution-v1.0.md) | v1.0 | Implemented | 2025-12-01 |
| [Phase 4: Cross-Encoder Reranking](phase4-cross-encoder-reranking-v1.0.md) | v1.0 | Implemented | 2025-12-01 |

---

## About HLDs

HLDs provide detailed design documentation for complex features before implementation. Each HLD should include:

- **Executive Summary**: Brief overview
- **Goals and Non-Goals**: Clear scope definition
- **Architecture**: System context, components, data model, API design
- **Implementation Plan**: Phases and dependencies
- **Testing Strategy**: Test approach and coverage requirements
- **Risks and Mitigations**: Identified risks with mitigation strategies

## Creating a New HLD

Use the template in `docs/templates/hld-template.md` to create a new HLD.

HLDs follow the naming convention:
`{feature-name}-v{X.Y}.md`
