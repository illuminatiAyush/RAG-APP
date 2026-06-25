import time #time measurement nd performance checks
import logging #logging stuff for production
from llama_index.readers.file import PDFReader #to read & parse pdf files
from llama_index.core.node_parser import SentenceSplitter #splitter to chunk text
from dotenv import load_dotenv #load env vars
from fastembed import TextEmbedding #local embedding generator

load_dotenv() #load environment config

logger = logging.getLogger("rag_app") #logger obj for this module

# Initialize local FastEmbed model
embedding_model = TextEmbedding() #downloads and loads model locally

# BAAI/bge-small-en-v1.5 has 384 dimensions
EMBED_MODEL = "BAAI/bge-small-en-v1.5" #model name
EMBED_DIM = 384 #vector dimensions

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200) #split text into 1000 token blocks with 200 overlap

def load_and_chunk_pdf(path: str) -> list[str]: #pdf parser nd splitter
    start_load = time.perf_counter() #timer for pdf reading
    docs = PDFReader().load_data(file=path) #read pdf from disk
    load_time = time.perf_counter() - start_load #measure read speed
    
    start_chunk = time.perf_counter() #timer for splitting
    texts = [d.text for d in docs if getattr(d, "text", None)] #extract text chunks
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t)) #chunk text via sentence splitter
    chunk_time = time.perf_counter() - start_chunk #measure splitting speed
    
    logger.info(f"PDF Load Time: {load_time:.4f}s | Chunking Time: {chunk_time:.4f}s | Total Chunks: {len(chunks)}") #log metrics
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]: #convert chunks to vectors
    start_embed = time.perf_counter() #timer for embeddings
    embeddings = list(embedding_model.embed(texts)) #generate local embeddings on CPU
    embed_time = time.perf_counter() - start_embed #measure embedding speed
    logger.info(f"Embedding Generation Time: {embed_time:.4f}s for {len(texts)} chunks") #log performance
    return [list(map(float, emb)) for emb in embeddings] #list of float lists