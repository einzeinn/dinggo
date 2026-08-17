---
trigger: always_on
---

# Dinggo Development Rules

## 1. General Principles

- Read the existing repository before making changes.
- Understand the current architecture before implementing anything.
- Do not redesign existing architecture unless explicitly requested.
- Do not introduce unrelated features.
- Do not modify files unrelated to the current task.
- Preserve existing behavior unless the requirement explicitly changes it.

## 2. Implementation Workflow

Every task MUST follow:

1. Inspect repository
2. Identify affected components
3. Explain implementation plan
4. Implement the requested change
5. Run relevant tests
6. Inspect the final diff
7. Report changed files and test results

Do not skip steps.

## 3. Scope Control

Only implement the current task.

If a problem is discovered outside the current task:

- Do not fix it automatically.
- Report it separately.
- Continue only if it blocks the current task.

## 4. Architecture

Dinggo follows a modular architecture.

Before creating a new component:

- Check whether an existing component already provides the required functionality.
- Prefer extending existing abstractions over creating duplicate systems.
- Keep provider-specific logic isolated behind adapters.
- Keep orchestration logic independent from providers.

## 5. Provider System

Providers MUST NOT be hardcoded into the core execution logic.

Use:

Provider Registry
→ Provider Resolver
→ Provider Adapter
→ Provider

Supported providers may include:

- Codex
- Claude
- Gemini
- Ollama
- OpenAI-compatible providers
- Custom providers

Adding a provider must not require rewriting the core engine.

## 6. Configuration

Do not require users to manually edit `.env` for normal provider setup.

Provider configuration should be handled through Dinggo Settings / Setup Wizard.

Environment variables are primarily for:

- secrets
- environment-specific configuration
- explicit overrides

## 7. CLI Interface

Interactive CLI entry point:

    dinggo interface

Main sections:

- Wizard
- Execute
- Settings
- Output
- Review
- Exit

Do not introduce alternative navigation patterns unless explicitly requested.

## 8. Review Engine

Review Engine MUST be provider-agnostic.

Architecture:

Review Engine
→ Provider Resolver
→ Provider Adapter
→ Reviewer

Codex is NOT a required dependency.

Do not hardcode Codex into Review Engine.

## 9. Workflow

The core Dinggo workflow is:

SPEC
↓
PLAN
↓
APPROVAL
↓
IMPLEMENT
↓
TEST
↓
VALIDATION
↓
BUILD
↓
FINAL APPROVAL
↓
EXPORT
↓
REVIEW

Review revision loop:

REVIEW
↓
FINDINGS
↓
REPAIR
↓
TEST
↓
VALIDATION
↓
REVIEW

## 10. State

Dinggo must maintain persistent project state.

The system should be able to determine:

- current phase
- current task
- execution status
- test status
- validation status
- build status
- review status

Interrupted workflows should be resumable.

## 11. Safety

Never:

- delete project files without explicit instruction
- overwrite configuration blindly
- remove existing functionality to make tests pass
- bypass failing tests
- silently change public interfaces
- fabricate test results

## 12. Testing

After implementation:

- Run relevant tests.
- Add tests for new functionality where appropriate.
- Never claim success without actually running validation.
- Report failures honestly.

## 13. Git / Changes

Before modifying code:

- inspect git status
- understand existing uncommitted changes

Do not overwrite unrelated user changes.

After implementation:

- inspect git diff
- summarize changed files
- identify unexpected modifications

## 14. Completion Criteria

A task is NOT complete merely because the code was written.

A task is complete only when:

- implementation exists
- relevant tests pass
- behavior matches requirements
- no unrelated changes were introduced
- final diff has been inspected

## 15. Communication

Before implementation:

- state what will be changed
- state which files/components are expected to change

After implementation:

- summarize changes
- report tests
- report remaining issues

Do not claim that a feature is implemented if only part of the requirement has been completed.

## CRITICAL RULE

Do not assume.

If the requirement is ambiguous, inspect the existing architecture and infer only
from established project conventions.

If ambiguity materially affects implementation, stop and report the ambiguity
instead of inventing a new architecture.

## NO UNREQUESTED REFACTORING

Do not refactor, rename, reorganize, migrate, or redesign existing components
unless the current task explicitly requires it.

A cleaner architecture is not a sufficient reason to modify unrelated code.