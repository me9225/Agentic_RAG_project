import os

# הגדרת שם תיקיית השורש
PROJECT_ROOT = "family_quest_project"

# מילון המכיל את נתיבי הקבצים והתוכן שלהם
files_to_create = {
    f"{PROJECT_ROOT}/main.py": """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Family Quest API")

class RewardRequest(BaseModel):
    user_id: int
    reward_id: int

@app.post("/api/redeem")
def redeem_reward(req: RewardRequest):
    \"\"\"
    Highly sensitive function for purchasing a reward.
    Check .copilot/warnings.md for transaction handling rules.
    \"\"\"
    user_balance = 50 # Mock balance
    reward_cost = 20 # Mock cost
    
    if user_balance < reward_cost:
        raise HTTPException(status_code=400, detail="Not enough coins")
    
    return {"status": "success", "new_balance": user_balance - reward_cost}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    \"\"\"
    Note: We only perform soft deletes! 
    See .cursor/rules.md
    \"\"\"
    return {"status": "task deactivated"}
""",

    f"{PROJECT_ROOT}/.cursor/decisions.md": """# Architectural Decisions

## Database Selection
**Date:** 2024-02-10
**Decision:** Use SQLite.
**Reasoning:** Since this is a local family-management app, we don't need the overhead of PostgreSQL. SQLite is lightweight and requires zero setup.
**Technical Constraint:** SQLite has limitations with concurrent writes. This means we must be careful with database locks, especially during coin transactions.

## Task Management
**Decision:** Tasks are assigned to specific children by parents.
""",

    f"{PROJECT_ROOT}/.cursor/rules.md": """# Core Development Rules

1. **Soft Deletes Only:** 
   NEVER hard-delete a task or a transaction from the database. We need to preserve history. 
   Always use the `is_active` boolean field and set it to `False` instead of running `DELETE` queries.

2. **Timestamps:**
   Every table must include `created_at` and `updated_at` fields in UTC.
""",

    f"{PROJECT_ROOT}/.cursor/changelog.md": """# Database Changelog

## [2024-02-15] - Schema Updates
**Added:**
- Added `reward_icon` string field to the `rewards` table to support UI visuals.
- Added `is_locked` boolean to `users` table to prevent disabled accounts from logging in.

**Removed:**
- Removed `child_age` column from the `users` table due to privacy considerations. Date of birth is no longer tracked.
""",

    f"{PROJECT_ROOT}/.claude/ui_spec.md": """# UI/UX Specifications

## Visual Identity
- **Primary Color:** The main color chosen for the system design is Light Purple (Hex: `#B39DDB`). 
- **Secondary Color:** Mint Green (`#A5D6A7`) for success actions (like completing a task).

## Localization & RTL
- **RTL Requirement:** The target audience is Israeli. Therefore, there is a strict and consistent rule: every screen in the UI must be RTL (Right-To-Left) formatted.
- **Languages:** 
  - Phase 1: The interface text is fully translated to Hebrew (`he-IL`).
  - Phase 2: We have decided to translate the interface to English (`en-US`) and Arabic (`ar`) in the upcoming Q3 release.

## Layout Rules
- Minimal text, large icons for kids.
- Error messages must be displayed in a friendly tone (e.g., "אופס! חסרים לך מטבעות").
""",

    f"{PROJECT_ROOT}/.claude/frontend_plan.md": """# Frontend Components Plan

- `Dashboard`: Displays current coins and active tasks.
- `RewardStore`: Grid of available rewards. 
- **Note:** Must implement a strict loading spinner during API calls to prevent double-clicks on the "Buy" button.
""",

    f"{PROJECT_ROOT}/.copilot/warnings.md": """# System Warnings & Security Notes

## Highly Sensitive Components
**Component:** `redeem_reward` function (Transaction Engine)
**Severity:** CRITICAL
**Details:** This component was defined as highly problematic and sensitive. There is a risk of race conditions where a child might click "buy" twice and get two rewards for the price of one. 
**Action:** Any change to this function requires code review. You MUST use strict database transactions (`BEGIN TRANSACTION`) and verify the user's coin balance inside the lock.

## Authentication
**Warning:** Do not modify the JWT authentication hook (`verify_token` middleware) without running the full security test suite.

## Known Technical Limitations
**Constraint:** As noted in other documents, SQLite locks the entire database on writes. This technical limitation appears in multiple documents and forces us to keep write transactions as brief as possible.
""",

    f"{PROJECT_ROOT}/.copilot/tasks.md": """# Pending Logic Tasks

- [x] Implement JWT token generation.
- [x] Create API endpoint for completing a task.
- [ ] Add rate limiting to the login endpoint to prevent brute force attacks.
- [ ] Write unit tests for the coin deduction logic.
"""
}

def create_mock_project():
    """יוצר את תיקיות הפרויקט והקבצים עם התוכן המוגדר."""
    print(f"Creating project structure in './{PROJECT_ROOT}'...")
    
    for file_path, content in files_to_create.items():
        # יצירת התיקייה במידה ואינה קיימת
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # כתיבת התוכן לקובץ (בקידוד UTF-8 כדי למנוע בעיות עם עברית)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        
        print(f"Created: {file_path}")
        
    print("\nProject generated successfully!")

if __name__ == "__main__":
    create_mock_project()