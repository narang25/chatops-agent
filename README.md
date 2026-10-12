# ChatOps: AI-Powered SRE Agent

An open-source agent that diagnoses deployment failures. An engineer asks
"why did payment-service fail?" and the agent searches runbooks (RAG), pulls live
metrics and container status through MCP tools, and answers with a cited diagnosis.

## Team
- Person A: LLM, RAG, agent, CLI, runbook MCP server
- Person B: sample services, monitoring, failure injection, metrics and status MCP servers, Slack, CI/CD

## Layout
See PERSON_A_BRIEF.md and PERSON_B_BRIEF.md for folder ownership and tasks.
Shared formats live in `contracts/`. Infra docs: `docs/infra.md`. Agent docs: `docs/agent.md`.

## Quick start
(Person A fills this in as the project grows.)
