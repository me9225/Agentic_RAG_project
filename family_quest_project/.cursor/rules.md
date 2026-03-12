# Core Development Rules

1. **Soft Deletes Only:** 
   NEVER hard-delete a task or a transaction from the database. We need to preserve history. 
   Always use the `is_active` boolean field and set it to `False` instead of running `DELETE` queries.

2. **Timestamps:**
   Every table must include `created_at` and `updated_at` fields in UTC.
