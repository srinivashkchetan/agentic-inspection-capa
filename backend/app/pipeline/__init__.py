"""Orchestration & context-engineering layer (PRD §5).

Stages, in order:
    ingest -> classify -> [trigger on FAIL/PENDING] -> retrieve (RDBMS ‖ RAG)
    -> assemble -> generate -> guardrails

Structured facts (RDBMS) and retrieved knowledge (RAG) are kept in distinct
channels; the model only reasons over the assembled context.
"""
