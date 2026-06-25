from vector_db import QdrantStorage #class bnayi, for dependency abstraction
import logging #lib for prod apps
import time #performance monitoring
from fastapi import FastAPI #for apis & endpts
import inngest #lib for all services -> retrieval, observability,, rate limitting, throttling
import inngest.fast_api #for fast api integration with inngest
from inngest.experimental import ai #for ai stuff & workflow integration on dashboard
from dotenv import load_dotenv #lib for env loading
import uuid #for uid generation
import os #lib for os stuff
import datetime #lib for datetime stuff
from app.data_loader import load_and_chunk_pdf, embed_texts  #ingestion layer
from app.custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc #tpye of data to be passed


load_dotenv()  #load env into mem

inngest_client = inngest.Inngest( #app workflow manager thro this object
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"), #inggest logs along with uvicorn ones
    is_production=False,
    serializer=inngest.PydanticSerializer(), #for type safety, with this, inngest automaticaly converts query result into json
)

@inngest_client.create_function( #decorator, pyth fn->inngest workflow->dashboard->retries->monitoring->ratelimits (distributed workflow step)
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle( #entire sys traffic controlled by this
    count=2, #overall 2 fns at a time across all users
    period=datetime.timedelta(minutes=1) #overall 2 fns/min
),rate_limit=inngest.RateLimit( #one user sending req/min
    limit=1,
    period=datetime.timedelta(hours=4),
    key="event.data.source_id", #source id will be diff for each user, so each user gets equal processing
)
)


async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc: #ctx has data like pdf path nd source id (json data), we can call other funcs thro ctx.step.run
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult: #fn for extraction
        chunks = chunks_and_src.chunks #extract data from objects..
        source_id = chunks_and_src.source_id 
        vecs = embed_texts(chunks) #convert to vectors
        
        start_upsert = time.perf_counter() #timer start to measure performance
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))] #every chunk gets a unique id, no duplicate records

        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))] #metadata for each chunk, not only vectors

        QdrantStorage(dim=384).upsert(ids, vecs, payloads)
        upsert_time = time.perf_counter() - start_upsert #measure qdrant upsert time
        
        logging.getLogger("uvicorn").info(f"Vector DB Upsert Time: {upsert_time:.4f}s for {len(chunks)} points") #prints & logs performance
        
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run("load-and-chunks", lambda: _load(ctx), output_type=RAGChunkAndSrc) #runs fn _load, ctx.step.run is like await for workflow steps, data automatically converted to json
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult) #chunks embedding & storing in vector db 

    return ingested.model_dump()

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai") #if event then run this workflow
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    def _search(question: str, top_k: int = 5): #releveant chunks from Qdrant
        query_vec = embed_texts([question])[0] #question -> vector
        store = QdrantStorage(dim=384)
        found = store.search(query_vec, top_k) #semantic search
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)
    
    context_block = "\n\n".join(f"- {c}" for c in found.contexts)

    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )
    
    adapter = ai.openai.Adapter(
        auth_key=os.getenv("GROK_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.1-8b-instant"
    )
    
    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "You answer questions using only the provided context."
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
    )

    answer = res["choices"][0]["message"]["content"].strip()

    return {
        "answer": answer,
        "sources": found.sources,
        "num_contexts": len(found.contexts)
    }

app = FastAPI()

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])



