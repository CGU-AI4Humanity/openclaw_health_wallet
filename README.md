# OpenClaw Health Wallet (CGU-AI4Humanity)

Research prototypes for a **personal health wallet** that combines local AI agents, FHIR interoperability, and privacy-preserving health data—aligned with the [MyWellWallet](https://mcp-fhir-server.com/) mobile app and the [FHIR MCP Server](https://mcp-fhir-server.com/) gateway.

**Course:** IST 362 — Advances in AI and Quantum Computing  
**Institution:** Claremont Graduate University (Doctor of Technology program)

## Team

| Researcher | Focus area (this repo) |
| --- | --- |
| **Santanu Ray** | [Zero_Claw-Retina_Health-Assistant](./Zero_Claw-Retina_Health-Assistant/) — retinal screening via ZeroClaw, Ollama, and custom MCP |
| **Mahesh Balan** | [Openclaw_Health_Assistant](./Openclaw_Health_Assistant/) — MyWellWallet-style FHIR wallet on desktop via OpenClaw, local SQLite MCP, remote FHIR MCP, MedGemma |
| **Brandon Medina** | *(contributions in class repo / branches as added)* |
| **Leonard Bryant** | *(contributions in class repo / branches as added)* |

## Subprojects

### Zero_Claw-Retina_Health-Assistant

Local retinal-health assistant (ZeroClaw + Qwen + RETFound). See [README_Retina_AI_Assistant.md](./Zero_Claw-Retina_Health-Assistant/README_Retina_AI_Assistant.md).

### Openclaw_Health_Assistant

Desktop personal health wallet concept using **OpenClaw**, **Ollama (MedGemma)**, a **local SQLite MCP server** (MyWellWallet-compatible FHIR JSON schema), the **hosted FHIR MCP** at `https://mcp-fhir-server.com/`, and **Apple Health** integration on macOS. See [Openclaw_Health_Assistant/README.md](./Openclaw_Health_Assistant/README.md).

## Related work

- MyWellWallet iOS app (FHIR + local SQLite + MCP) — sibling implementation in the Balkeum Labs R&D line
- [FHIR MCP Server](https://mcp-fhir-server.com/) — shared backend gateway for FHIR tools and document RAG

## License

Academic / research use unless otherwise noted in subproject directories. Do not commit API keys, PHI, or production credentials.
