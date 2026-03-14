import os
import json
from dotenv import load_dotenv
import gradio as gr

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.cohere import Cohere
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.core.llms import ChatMessage, MessageRole

from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

# ==========================================
# 1. הגדרות, אתחול מודלים וטעינת נתונים
# ==========================================
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")

print("מאתחל מערכות וטוען מאגרי מידע...")
llm = Cohere(model="command-r-plus-08-2024", api_key=cohere_key)
embed_model = CohereEmbedding(
    model_name="embed-multilingual-v3.0",
    input_type="search_document",
    api_key=cohere_key
)

# טעינת מסד הנתונים הוקטורי (Semantic)
PERSIST_DIR = "./storage"
storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
index = load_index_from_storage(storage_context, embed_model=embed_model)
retriever = index.as_retriever(similarity_top_k=3)

# טעינת מסד הנתונים המובנה (Structured JSON)
JSON_PATH = "system_data.json"
if not os.path.exists(JSON_PATH):
    raise FileNotFoundError("❌ חסר קובץ system_data.json. אנא הריצי את extract_data.py")
    
with open(JSON_PATH, "r", encoding="utf-8") as f:
    structured_data = json.load(f)

# ==========================================
# 2. הגדרת סוגי האירועים (Events) של הניתוב
# ==========================================
class ValidQueryEvent(Event):
    query: str

class SemanticRouteEvent(Event):
    """אירוע ניתוב לחיפוש רגיל בקבצים"""
    query: str

class StructuredRouteEvent(Event):
    """אירוע ניתוב לחילוץ מנתוני ה-JSON"""
    query: str

class SynthesizeEvent(Event):
    """האירוע שמאחד את שני המסלולים ומוכן לבניית התשובה"""
    query: str
    context: str
    sources: str
    search_type: str # 'Semantic' או 'Structured'

# ==========================================
# 3. בניית ה-Workflow הסוכני
# ==========================================
class AgenticDocsRAG(Workflow):
    
    # --- תחנה 1: ולידציה ---
    @step
    async def validate_input(self, ev: StartEvent) -> ValidQueryEvent | StopEvent:
        query = ev.get("query", "").strip()
        print(f"\n🛡️ [שלב 1: ולידציה] התקבלה שאלה: '{query}'")
        if len(query) < 5:
            return StopEvent(result="❌ השאלה קצרה מדי. אנא שאל שאלה מפורטת יותר.")
        return ValidQueryEvent(query=query)
        
    # --- תחנה 2: מנגנון הניתוב (Router) ---
    @step
    async def route_query(self, ev: ValidQueryEvent) -> SemanticRouteEvent | StructuredRouteEvent:
        print("🔀 [שלב 2: נתב] מחליט איזה סוג חיפוש לבצע...")
        
        # אנחנו מבקשים מה-LLM להיות "שומר הסף" שמחליט לאן ללכת
        routing_prompt = f"""
        אתה נתב (Router) במערכת RAG. עליך לסווג את שאלת המשתמש לאחת משתי קטגוריות בלבד:
        1. "STRUCTURED" - אם השאלה מבקשת רשימה, או עוסקת ספציפית בהחלטות (decisions), חוקי פיתוח והנחיות (rules), או אזהרות ורגישויות (warnings).
        2. "SEMANTIC" - אם השאלה עוסקת בהסברים כלליים, ארכיטקטורה, עיצוב (UI), איך דברים עובדים, או מידע כללי אחר.
        
        השב רק עם המילה STRUCTURED או SEMANTIC. אל תוסיף אף מילה אחרת.
        
        שאלה: "{ev.query}"
        החלטה:
        """
        messages = [ChatMessage(role=MessageRole.USER, content=routing_prompt)]
        response = await llm.achat(messages)
        decision = response.message.content.strip().upper()
        
        if "STRUCTURED" in decision:
            print("   🎯 הוחלט: חיפוש מובנה (Structured Data)")
            return StructuredRouteEvent(query=ev.query)
        else:
            print("   📚 הוחלט: חיפוש סמנטי (Vector Search)")
            return SemanticRouteEvent(query=ev.query)

    # --- תחנה 3א': חיפוש סמנטי (הקלאסי) ---
    @step
    async def semantic_search(self, ev: SemanticRouteEvent) -> SynthesizeEvent | StopEvent:
        print("🔍 [שלב 3: שליפה] מחפש במסמכים וקטוריים...")
        nodes = await retriever.aretrieve(ev.query)
        
        if not nodes:
            return StopEvent(result="⚠️ מצטער, לא מצאתי מידע רלוונטי במסמכי המערכת לגבי השאלה שלך.")
            
        context_str = "\n\n".join([n.node.get_content() for n in nodes])
        sources = set([n.node.metadata.get("file_name", "Unknown") for n in nodes])
        sources_str = ", ".join(sources)
        
        return SynthesizeEvent(query=ev.query, context=context_str, sources=sources_str, search_type="חיפוש סמנטי בקבצים")

    # --- תחנה 3ב': חיפוש מובנה (מה-JSON) ---
    @step
    async def structured_search(self, ev: StructuredRouteEvent) -> SynthesizeEvent:
        print("📊 [שלב 3: שליפה] שולף נתונים מה-JSON המובנה...")
        
        # שלב א': מבקשים מה-LLM לבנות "שאילתה" ולבחור אילו רשימות מתוך ה-JSON צריך
        query_prompt = f"""
        המשתמש שאל: "{ev.query}".
        יש לנו מסד נתונים עם שלוש קטגוריות: "decisions", "rules", "warnings".
        תחזיר רק את שם הקטגוריה שצריך כדי לענות על השאלה (או כמה קטגוריות מופרדות בפסיק).
        אם אתה לא בטוח, תחזיר: decisions, rules, warnings.
        """
        response = await llm.achat([ChatMessage(role=MessageRole.USER, content=query_prompt)])
        needed_keys = response.message.content.lower()
        
        # שלב ב': ביצוע השליפה (חילוץ הפריטים מה-JSON)
        extracted_context = []
        sources = set()
        
        items = structured_data.get("items", {})
        for key in ["decisions", "rules", "warnings"]:
            if key in needed_keys:
                for item in items.get(key, []):
                    extracted_context.append(json.dumps(item, ensure_ascii=False))
                    sources.add(item.get("source", {}).get("file", "JSON Data"))
        
        context_str = "\n".join(extracted_context)
        sources_str = ", ".join(sources)
        
        # אם משום מה לא מצאנו כלום ב-JSON, נחזיר את הכל ליתר ביטחון
        if not context_str.strip():
            context_str = json.dumps(items, ensure_ascii=False)
            sources_str = "system_data.json"
            
        return SynthesizeEvent(query=ev.query, context=context_str, sources=sources_str, search_type="חיפוש מובנה (JSON)")

    # --- תחנה 4: סינתוז התשובה הסופית ---
    @step
    async def synthesize(self, ev: SynthesizeEvent) -> StopEvent:
        print(f"🧠 [שלב 4: סינתוז] מרכיב תשובה סופית (על בסיס {ev.search_type})...")
        
        qa_prompt = f"""
        אתה מנתח מערכות AI מומחה. ענה על השאלה בצורה מקצועית על סמך המידע הבא בלבד.
        שים לב: המידע עשוי להיות טקסט חופשי או אובייקטי JSON. חלץ ממנו את התשובה והגש אותה למשתמש בעברית ברורה ומסודרת (השתמש בנקודות, רשימות והדגשות במידת הצורך).
        אם התשובה אינה במידע, אמור 'על פי התיעוד הקיים, איני יודע את התשובה'.
        ---------------------
        {ev.context}
        ---------------------
        שאלה: {ev.query}
        תשובה:
        """
        messages = [ChatMessage(role=MessageRole.USER, content=qa_prompt)]
        response = await llm.achat(messages)
        
        final_answer = f"{response.message.content}\n\n---\n🔬 **סוג חיפוש שבוצע:** {ev.search_type}\n📁 **מקורות:** {ev.sources}"
        print("✅ [שלב 4] התשובה מוכנה!")
        
        return StopEvent(result=final_answer)

# ==========================================
# 4. ממשק המשתמש (Gradio)
# ==========================================
workflow = AgenticDocsRAG(timeout=60.0, verbose=False)

async def predict_workflow(message, history):
    result = await workflow.run(query=message)
    return result

print("🚀 מפעיל את ממשק ה-Agentic RAG החכם...")
demo = gr.ChatInterface(
    fn=predict_workflow,
    title="🧠 Agentic Docs RAG (Multi-Router)",
    description="מערכת RAG מתקדמת עם ניתוב אוטומטי בין חיפוש וקטורי לשליפת נתונים מובנים מ-JSON."
)

if __name__ == "__main__":
    demo.launch()