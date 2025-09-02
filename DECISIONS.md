# 🧭 SuperManUS Architecture Decisions Log

## Purpose
This document records all significant technical decisions made during the SuperManUS project development. Each decision includes context, alternatives considered, and rationale for the chosen approach.

---

## Decision Records

### ADR-001: Session State Management System
**Date:** 2025-09-02  
**Status:** Accepted  
**Session:** INIT_001  

**Context:**  
LLM assistants often lose context between sessions, leading to repeated work, inconsistent implementations, and developer frustration.

**Decision:**  
Implement a JSON-based session state file (SESSION_STATE.json) that persists all critical context between development sessions.

**Alternatives Considered:**
1. SQLite database - Too heavy for simple state tracking
2. Plain text notes - Lacks structure and parseability
3. Git commit messages only - Insufficient detail for complex state

**Consequences:**
- ✅ Easy to read and parse by both humans and LLMs
- ✅ Version controlled with Git
- ✅ Lightweight and portable
- ⚠️ Requires discipline to update consistently

---

### ADR-002: Modular Architecture with MCP Server
**Date:** 2025-09-02  
**Status:** Accepted  
**Session:** INIT_001  

**Context:**  
Need a system that can grow and adapt without requiring changes to core application code.

**Decision:**  
Use a Master Control Program (MCP) server as a central orchestrator with independent, self-registering modules.

**Alternatives Considered:**
1. Monolithic application - Poor scalability and maintainability
2. Microservices with service mesh - Overly complex for initial version
3. Plugin system with dynamic loading - Security concerns and complexity

**Consequences:**
- ✅ Modules can be developed independently
- ✅ Hot-swapping capabilities
- ✅ Clear separation of concerns
- ⚠️ Additional complexity in communication protocol
- ⚠️ Potential latency from inter-module communication

---

### ADR-003: AMD ROCm Stack for GPU Acceleration
**Date:** 2025-09-02  
**Status:** Accepted  
**Session:** INIT_001  

**Context:**  
Project targets AMD Instinct MI50 GPUs with 32GB VRAM. Need open-source GPU acceleration.

**Decision:**  
Use ROCm 5.7+ with vLLM/TGI for model serving.

**Alternatives Considered:**
1. CUDA/NVIDIA - Not compatible with AMD hardware
2. CPU-only - Insufficient performance for real-time requirements
3. OpenCL - Less mature ML ecosystem

**Consequences:**
- ✅ Full AMD GPU utilization
- ✅ Open-source stack
- ✅ Cost-effective hardware
- ⚠️ Smaller ecosystem than CUDA
- ⚠️ Potential compatibility issues with some models

---

### ADR-004: Phase-Based Development Approach
**Date:** 2025-09-02  
**Status:** Accepted  
**Session:** INIT_001  

**Context:**  
Need structured approach to manage complexity and ensure progress visibility.

**Decision:**  
Implement 5-phase development plan with clear milestones and atomic tasks.

**Phases:**
1. Foundation (Days 1-7)
2. Core Modules (Days 8-21)
3. MCP Integration (Days 22-35)
4. Extensible Modules (Days 36-56)
5. Integration & Optimization (Days 57-70)

**Alternatives Considered:**
1. Agile sprints - Too flexible for LLM continuity
2. Waterfall - Too rigid for iterative development
3. Continuous development - Lacks clear checkpoints

**Consequences:**
- ✅ Clear progress tracking
- ✅ Defined success criteria
- ✅ Manageable complexity
- ⚠️ Less flexibility for major pivots

---

### ADR-005: Voice Pipeline Architecture
**Date:** 2025-09-02  
**Status:** Proposed  
**Session:** INIT_001  

**Context:**  
Need real-time voice processing with <500ms end-to-end latency.

**Decision:**  
Use streaming pipeline with Whisper (STT) → Llama-3 (NLP) → Piper (TTS).

**Alternatives Considered:**
1. Cloud-based APIs - Latency and privacy concerns
2. Single end-to-end model - Not mature enough
3. Batch processing - Poor user experience

**Consequences:**
- ✅ Low latency potential
- ✅ Modular components
- ✅ On-premises processing
- ⚠️ Complex synchronization
- ⚠️ High resource usage

---

### ADR-006: Docker-First Development
**Date:** 2025-09-02  
**Status:** Proposed  
**Session:** INIT_001  

**Context:**  
Need consistent development environment across sessions and machines.

**Decision:**  
All components run in Docker containers with docker-compose orchestration.

**Alternatives Considered:**
1. Native installation - Environment inconsistency
2. Virtual machines - Resource overhead
3. Kubernetes from start - Premature optimization

**Consequences:**
- ✅ Reproducible environments
- ✅ Easy deployment
- ✅ Isolation between modules
- ⚠️ Additional complexity
- ⚠️ Potential GPU passthrough issues

---

### ADR-007: WebSocket for Real-Time Communication
**Date:** 2025-09-02  
**Status:** Proposed  
**Session:** INIT_001  

**Context:**  
Need bidirectional, low-latency communication between modules and MCP.

**Decision:**  
Use WebSocket protocol for all inter-module communication.

**Alternatives Considered:**
1. REST APIs - Higher latency, no push capability
2. gRPC - Additional complexity
3. Message queues (RabbitMQ/Kafka) - Overkill for initial version

**Consequences:**
- ✅ Real-time bidirectional communication
- ✅ Lower latency than HTTP
- ✅ Wide language support
- ⚠️ Connection management complexity
- ⚠️ Need fallback for disconnections

---

### ADR-008: Python as Primary Language
**Date:** 2025-09-02  
**Status:** Accepted  
**Session:** INIT_001  

**Context:**  
Need language with strong AI/ML ecosystem and rapid development.

**Decision:**  
Use Python 3.11+ for all core components.

**Alternatives Considered:**
1. Rust - Better performance but slower development
2. Go - Less ML library support
3. JavaScript/TypeScript - Weaker ML ecosystem

**Consequences:**
- ✅ Rich AI/ML libraries
- ✅ Rapid prototyping
- ✅ Large community
- ⚠️ Performance limitations
- ⚠️ GIL constraints (mitigated by async)

---

## Decision Template

### ADR-XXX: [Decision Title]
**Date:** YYYY-MM-DD  
**Status:** [Proposed|Accepted|Deprecated|Superseded]  
**Session:** [Session ID]  

**Context:**  
[What is the issue that we're seeing that is motivating this decision?]

**Decision:**  
[What is the change that we're proposing and/or doing?]

**Alternatives Considered:**
1. [Alternative 1] - [Why not chosen]
2. [Alternative 2] - [Why not chosen]

**Consequences:**
- ✅ [Positive consequence]
- ⚠️ [Neutral/Trade-off]
- ❌ [Negative consequence]

---

## Review Schedule
- Weekly review during active development
- Major decisions require documentation before implementation
- Deprecated decisions archived but not deleted

---

*"With great power comes great architectural responsibility!"* 🦸

**Last Updated:** 2025-09-02  
**Next Review:** 2025-09-09