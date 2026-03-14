import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

from llama_index.llms.cohere import Cohere
from llama_index.core.llms import ChatMessage, MessageRole

# ==========================================
# 1. הגדרת סכמת הנתונים
# ==========================================
class SourceInfo(BaseModel):
    tool: str
    file: str

class DecisionItem(BaseModel):
    id: str = "dec-unknown"
    title: str = ""
    summary: str = ""
    tags: List[str] = []
    source: SourceInfo

class RuleItem(BaseModel):
    id: str = "rule-unknown"
    rule: str = ""
    scope: str = ""
    source: SourceInfo

class WarningItem(BaseModel):
    id: str = "warn-unknown"
    area: str = ""
    message: str = ""
    severity: str = "medium"
    source: SourceInfo

class ExtractedData(BaseModel):
    decisions: List[DecisionItem] = Field(default_factory=list)
    rules: List[RuleItem] = Field(default_factory=list)
    warnings: List[WarningItem] = Field(default_factory=list)

# ==========================================
# 2. אתחול והגדרות בסיס
# ==========================================
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")

llm = Cohere(model="command-r-plus-08-2024", api_key=cohere_key)
PROJECT_DIR = "./family_quest_project"

# ==========================================
# 3. פונקציית החילוץ המרכזית
# ==========================================
async def extract_data_from_files():
    print("🚀 מתחיל תהליך חילוץ נתונים מובנים (Data Extraction)...")
    
    all_decisions = []
    all_rules = []
    all_warnings = []
    
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in ["venv", ".venv", "node_modules", ".git"]]
        
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                
                tool = "unknown"
                if ".cursor" in file_path: tool = "cursor"
                elif ".claude" in file_path: tool = "claude_code"
                elif ".copilot" in file_path: tool = "copilot"
                
                print(f"\n📄 קורא את הקובץ: {file_path}")
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # הוספנו דוגמה מפורשת ומוחלטת לכל המערכים!
                prompt_text = f"""
                אתה מנתח מערכות. קרא את קובץ התיעוד וחלץ: 1. החלטות, 2. חוקים, 3. אזהרות.
                
                חובה עליך להחזיר אך ורק אובייקט JSON חוקי במבנה הבא:
                {{
                  "decisions": [
                    {{"id": "dec-01", "title": "...", "summary": "...", "tags": ["..."], "source": {{"tool": "{tool}", "file": "{file_path}"}}}}
                  ],
                  "rules": [
                    {{"id": "rule-01", "rule": "...", "scope": "...", "source": {{"tool": "{tool}", "file": "{file_path}"}}}}
                  ],
                  "warnings": [
                    {{"id": "warn-01", "area": "...", "message": "...", "severity": "...", "source": {{"tool": "{tool}", "file": "{file_path}"}}}}
                  ]
                }}
                
                תוכן הקובץ:
                ---------------------
                {content}
                ---------------------
                """
                
                try:
                    messages = [ChatMessage(role=MessageRole.USER, content=prompt_text)]
                    response = await llm.achat(messages)
                    raw_text = response.message.content.strip()
                    
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    elif raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                        
                    raw_text = raw_text.strip()
                    
                    data_dict = json.loads(raw_text)
                    extracted = ExtractedData(**data_dict)
                    
                    # התיקון של Pydantic: שימוש ב-model_dump() במקום dict()
                    all_decisions.extend([item.model_dump() for item in extracted.decisions])
                    all_rules.extend([item.model_dump() for item in extracted.rules])
                    all_warnings.extend([item.model_dump() for item in extracted.warnings])
                    
                    print(f"   ✅ חולצו בהצלחה: {len(extracted.decisions)} החלטות, {len(extracted.rules)} חוקים, {len(extracted.warnings)} אזהרות.")
                
                except json.JSONDecodeError:
                    print(f"   ❌ שגיאה: המודל לא החזיר JSON תקין.")
                except Exception as e:
                    print(f"   ❌ שגיאה כללית בחילוץ: {e}")
                
                print("   ⏳ ממתין 13 שניות למניעת חסימת Rate Limit...")
                await asyncio.sleep(13)

    # ==========================================
    # 4. שמירת הנתונים ל-JSON
    # ==========================================
    final_output = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "items": {
            "decisions": all_decisions,
            "rules": all_rules,
            "warnings": all_warnings
        }
    }
    
    output_file = "system_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 התהליך הושלם! הנתונים נשמרו בהצלחה בקובץ '{output_file}'")

if __name__ == "__main__":
    asyncio.run(extract_data_from_files())
    