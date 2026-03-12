# Architectural Decisions

## Database Selection
**Date:** 2024-02-10
**Decision:** Use SQLite.
**Reasoning:** Since this is a local family-management app, we don't need the overhead of PostgreSQL. SQLite is lightweight and requires zero setup.
**Technical Constraint:** SQLite has limitations with concurrent writes. This means we must be careful with database locks, especially during coin transactions.

## Task Management
**Decision:** Tasks are assigned to specific children by parents.
