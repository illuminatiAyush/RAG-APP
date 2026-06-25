import time
import logging
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()

logger = logging.getLogger("rag_app")

# Initialize local FastEmbed model
embedding_model = TextEmbedding()

# BAAI/bge-small-en-v1.5 has 384 dimensions
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str) -> list[str]:
    start_load = time.perf_counter()
    docs = PDFReader().load_data(file=path)
    load_time = time.perf_counter() - start_load
    
    start_chunk = time.perf_counter()
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    chunk_time = time.perf_counter() - start_chunk
    
    logger.info(f"PDF Load Time: {load_time:.4f}s | Chunking Time: {chunk_time:.4f}s | Total Chunks: {len(chunks)}")
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    start_embed = time.perf_counter()
    embeddings = list(embedding_model.embed(texts))
    embed_time = time.perf_counter() - start_embed
    logger.info(f"Embedding Generation Time: {embed_time:.4f}s for {len(texts)} chunks")
    return [list(map(float, emb)) for emb in embeddings]