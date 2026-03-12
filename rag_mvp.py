import os
from dotenv import load_dotenv
import gradio as gr
from llama_index.core import (
    SimpleDirectoryReader, 
    VectorStoreIndex, 
    StorageContext, 
    load_index_from_storage
)
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.llms.cohere import Cohere
from llama_index.embeddings.cohere import CohereEmbedding

# ==========================================
# 1. טעינת מפתחות
# ==========================================
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")

if not cohere_key:
    raise ValueError("❌ שגיאה: חסר מפתח COHERE_API_KEY בקובץ ה-.env")

PROJECT_DIR = "./family_quest_project"
PERSIST_DIR = "./storage" # התיקייה שבה יישמרו הוקטורים מקומית

# ==========================================
# 2. אתחול מודלים (Cohere)
# ==========================================
llm = Cohere(model="command-r-plus-08-2024", api_key=cohere_key)
embed_model = CohereEmbedding(
    model_name="embed-multilingual-v3.0",
    input_type="search_document",
    api_key=cohere_key
)

# ==========================================
# 3. בניית אינדקס (או טעינה מקיים)
# ==========================================
# נבדוק אם כבר יצרנו את האינדקס בעבר ושמרנו אותו
if not os.path.exists(PERSIST_DIR):
    print("לא נמצא אינדקס מקומי. קורא מסמכים ומייצר וקטורים...")
    
    def extract_metadata(filename: str) -> dict:
        tool = "unknown"
        if ".cursor" in filename: tool = "Cursor"
        elif ".claude" in filename: tool = "Claude Code"
        elif ".copilot" in filename: tool = "Copilot"
        return {"tool": tool, "file_name": os.path.basename(filename), "file_path": filename}

    documents = SimpleDirectoryReader(
        input_dir=PROJECT_DIR,
        required_exts=[".md"],
        recursive=True,
        exclude_hidden=False, 
        file_metadata=extract_metadata
    ).load_data()

    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_documents(documents)
    print(f"נוצרו {len(nodes)} מקטעים. מתחיל יצירת Embeddings (Cohere)...")
    
    # יצירת האינדקס בזיכרון
    index = VectorStoreIndex(nodes, embed_model=embed_model, show_progress=True)
    
    # שמירה לדיסק המקומי כדי שלא נצטרך לייצר מחדש בכל הרצה!
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    print(f"הנתונים נשמרו בהצלחה בתיקיית {PERSIST_DIR}")
else:
    print(f"טוען אינדקס קיים מתיקיית {PERSIST_DIR}...")
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context, embed_model=embed_model)

# ==========================================
# 4. הגדרת מנוע השאילתות ו-Gradio
# ==========================================
query_engine = index.as_query_engine(
    llm=llm,
    similarity_top_k=3, 
)

def predict(message, history):
    response = query_engine.query(message)
    sources = set([node.metadata.get("file_name") for node in response.source_nodes])
    sources_str = ", ".join(sources) if sources else "לא נמצאו מקורות"
    return f"{str(response)}\n\n---\n📁 **מקורות:** {sources_str}"

print("מפעיל את ממשק המשתמש (Gradio)...")
demo = gr.ChatInterface(
    fn=predict,
    title="🤖 Agentic Docs RAG (MVP)",
    description="שאלי אותי על החלטות הפיתוח של המערכת"
)

if __name__ == "__main__":
    demo.launch()