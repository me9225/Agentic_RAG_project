# System Warnings & Security Notes

## Highly Sensitive Components
**Component:** `redeem_reward` function (Transaction Engine)
**Severity:** CRITICAL
**Details:** This component was defined as highly problematic and sensitive. There is a risk of race conditions where a child might click "buy" twice and get two rewards for the price of one. 
**Action:** Any change to this function requires code review. You MUST use strict database transactions (`BEGIN TRANSACTION`) and verify the user's coin balance inside the lock.

## Authentication
**Warning:** Do not modify the JWT authentication hook (`verify_token` middleware) without running the full security test suite.

## Known Technical Limitations
**Constraint:** As noted in other documents, SQLite locks the entire database on writes. This technical limitation appears in multiple documents and forces us to keep write transactions as brief as possible.
