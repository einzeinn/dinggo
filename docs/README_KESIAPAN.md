# System Readiness & Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)

## Overview
This system is designed to orchestrate specification-driven AI pipelines. Powered by multi-model orchestration, it delivers high accuracy, automated validation, and local execution efficiency.

## Key Features
### CLI Commands
- `dinggo init`: Initialize a new project specification template.
- `dinggo plan`: Generate and inspect the Directed Acyclic Task Graph.
- `dinggo build`: Execute the full product factory lifecycle.
- `dinggo test`: Run automated unit tests and closed-loop repairs.
- `dinggo review`: Run independent code audit and review reports.
- `dinggo status`: Inspect current project execution state.

### Interactive Views
- `dinggo interface`: Main TUI Product Factory Dashboard.
- `dinggo wizard`: Interactive product specification generator.

## Quick Start
1. **Installation**:
   - Create and activate virtual environment: `python -m venv .venv && .venv\Scripts\activate`.
   - Install dependencies: `pip install -e .`.

2. **Initialize Project**:
   - Generate default specification templates: `dinggo init`.

3. **Run Pipeline**:
   - Build product end-to-end: `dinggo build`.

4. **Verify State**:
   - Check current state and task completion: `dinggo status`.