import os
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
# 1. אתחול והגדרות
# ==========================================
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
PERSIST_DIR = "./storage"

llm = Cohere(model="command-r-plus-08-2024", api_key=cohere_key)
embed_model = CohereEmbedding(
    model_name="embed-multilingual-v3.0",
    input_type="search_document",
    api_key=cohere_key
)

storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
index = load_index_from_storage(storage_context, embed_model=embed_model)
retriever = index.as_retriever(similarity_top_k=3)

# ==========================================
# 2. הגדרת אירועים (Events)
# ==========================================
class ValidQueryEvent(Event):
    """אירוע שנפלט רק אם השאלה עברה בדיקות תקינות"""
    query: str

class RetrieverEvent(Event):
    """אירוע שמכיל את המסמכים שנמצאו"""
    nodes: list
    query: str

# ==========================================
# 3. בניית ה-Workflow עם ולידציות
# ==========================================
class AgenticDocsRAG(Workflow):
    
    # תחנה 1: ולידציה של הקלט (בדיקת תקינות)
    @step
    async def validate_input(self, ev: StartEvent) -> ValidQueryEvent | StopEvent:
        query = ev.get("query", "").strip()
        print(f"🛡️ [שלב 1: ולידציה] בודק את הקלט: '{query}'")
        
        # ולידציה 1: קלט ריק
        if not query:
            return StopEvent(result="❌ שגיאה: אנא הכנס שאלה חוקית.")
            
        # ולידציה 2: קלט קצר מדי או "שטויות"
        if len(query) < 5:
            return StopEvent(result="❌ שגיאה: השאלה קצרה מדי. אנא שאל שאלה מפורטת יותר על המערכת.")
            
        print("✅ [שלב 1] הקלט תקין.")
        return ValidQueryEvent(query=query)
        
    # תחנה 2: שליפת מסמכים
    @step
    async def retrieve(self, ev: ValidQueryEvent) -> RetrieverEvent | StopEvent:
        print(f"🔍 [שלב 2: שליפה] מחפש במסמכים...")
        nodes = await retriever.aretrieve(ev.query)
        
        # ולידציה 3: חוסר תוצאות / רלוונטיות נמוכה
        if not nodes:
            return StopEvent(result="⚠️ מצטער, לא מצאתי מידע רלוונטי במסמכי המערכת לגבי השאלה שלך.")
            
        print(f"✅ [שלב 2] נמצאו {len(nodes)} מקטעים רלוונטיים.")
        return RetrieverEvent(nodes=nodes, query=ev.query)
    
    # תחנה 3: הרכבת תשובה
    @step
    async def synthesize(self, ev: RetrieverEvent) -> StopEvent:
        print("🧠 [שלב 3: סינתוז] מרכיב תשובה בעזרת מודל השפה...")
        
        context_str = "\n\n".join([n.node.get_content() for n in ev.nodes])
        sources = set([n.node.metadata.get("file_name", "Unknown") for n in ev.nodes])
        sources_str = ", ".join(sources)
        
        qa_prompt_tmpl = PromptTemplate(
            "אתה מנתח מערכות AI מומחה.\n"
            "השתמש במידע הבא מתוך תיעוד המערכת כדי לענות על השאלה בצורה מקצועית.\n"
            "אם התשובה לא נמצאת במידע, אמור 'על פי התיעוד הקיים, איני יודע את התשובה'.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "שאלה: {query_str}\n"
            "תשובה:"
        )
        prompt = qa_prompt_tmpl.format(context_str=context_str, query_str=ev.query)
        
        messages = [ChatMessage(role=MessageRole.USER, content=prompt)]
        response = await llm.achat(messages)
        
        final_answer = f"{response.message.content}\n\n---\n📁 **מקורות:** {sources_str}"
        print("✅ [שלב 3] התשובה מוכנה!")
        
        return StopEvent(result=final_answer)

# ==========================================
# 4. ממשק המשתמש (Gradio)
# ==========================================
workflow = AgenticDocsRAG(timeout=60.0, verbose=False)

async def predict_workflow(message, history):
    result = await workflow.run(query=message)
    return result

print("🚀 מפעיל את הממשק מבוסס ה-Workflow...")
demo = gr.ChatInterface(
    fn=predict_workflow,
    title="⚙️ Event-Driven RAG (Phase 2 - Validated)",
    description="מערכת RAG מפורקת לאירועים הכוללת ולידציות חכמות. שאלי שאלות על המערכת!"
)

if __name__ == "__main__":
    demo.launch()