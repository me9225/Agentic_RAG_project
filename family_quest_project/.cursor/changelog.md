# Database Changelog

## [2024-02-15] - Schema Updates
**Added:**
- Added `reward_icon` string field to the `rewards` table to support UI visuals.
- Added `is_locked` boolean to `users` table to prevent disabled accounts from logging in.

**Removed:**
- Removed `child_age` column from the `users` table due to privacy considerations. Date of birth is no longer tracked.
