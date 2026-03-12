from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Family Quest API")

class RewardRequest(BaseModel):
    user_id: int
    reward_id: int

@app.post("/api/redeem")
def redeem_reward(req: RewardRequest):
    """
    Highly sensitive function for purchasing a reward.
    Check .copilot/warnings.md for transaction handling rules.
    """
    user_balance = 50 # Mock balance
    reward_cost = 20 # Mock cost
    
    if user_balance < reward_cost:
        raise HTTPException(status_code=400, detail="Not enough coins")
    
    return {"status": "success", "new_balance": user_balance - reward_cost}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    """
    Note: We only perform soft deletes! 
    See .cursor/rules.md
    """
    return {"status": "task deactivated"}
