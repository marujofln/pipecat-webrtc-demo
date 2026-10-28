from app.rag import KnowledgeBase
from app.tools.crm import LIST_SLOTS, SCHEDULE
from app.tools.registry import Tool, ToolRegistry


def build_registry(kb: KnowledgeBase) -> ToolRegistry:
    async def search_knowledge(args: dict) -> dict:
        chunks = kb.search(args["query"])
        return {"results": [{"title": c.heading, "text": c.text} for c in chunks]}

    search = Tool(
        name="search_knowledge",
        description="Searches the knowledge base (opening hours, prices, rules, address, procedures).",
        properties={"query": {"type": "string", "description": "Question or keywords, in the language of the call"}},
        required=["query"],
        handler=search_knowledge,
    )
    return ToolRegistry([search, LIST_SLOTS, SCHEDULE])
