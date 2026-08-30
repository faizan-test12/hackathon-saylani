import re
import logging
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from app import db
from app.models import Document, DocumentChunk

logger = logging.getLogger(__name__)

_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers embedding model: intfloat/multilingual-e5-small")
        _model = SentenceTransformer('intfloat/multilingual-e5-small')
    return _model

def embed_text(text: str, prefix: str = 'query: ') -> list[float]:
    """
    Encodes text using multilingual-e5-small with L2 normalization.
    CRITICAL:
      - Document chunks for storage: prefix with 'passage: '
      - User search queries: prefix with 'query: '
    """
    model = get_model()
    # Normalize embeddings to unit sphere for accurate cosine similarity
    embedding = model.encode([prefix + text], normalize_embeddings=True)[0]
    return embedding.tolist()

def chunk_text(text: str, target_chunk_chars: int = 1400, overlap_chars: int = 200) -> list[str]:
    """
    Sentence-aware chunking targeting ~350-450 tokens (~1400 chars) with ~50 tokens (~200 chars) overlap.
    Splits strictly on sentence and paragraph boundaries to preserve semantic context.
    """
    text = text.strip()
    if not text:
        return []

    # Split on paragraph breaks or sentence terminals followed by whitespace
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n\n+', text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    if not sentences:
        return [text]

    chunks = []
    current_sentences = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if current_length + sentence_len > target_chunk_chars and current_sentences:
            chunk_content = " ".join(current_sentences).strip()
            chunks.append(chunk_content)

            # Calculate overlap from the end of current chunk
            overlap_sentences = []
            accumulated_overlap = 0
            for s in reversed(current_sentences):
                if accumulated_overlap + len(s) > overlap_chars:
                    break
                overlap_sentences.insert(0, s)
                accumulated_overlap += len(s)

            current_sentences = overlap_sentences
            current_length = accumulated_overlap

        current_sentences.append(sentence)
        current_length += sentence_len

    if current_sentences:
        chunks.append(" ".join(current_sentences).strip())

    return chunks

def ingest_document(file_path: str, filename: str) -> Document:
    """
    Ingests PDF, Markdown, or plain text file into Document & DocumentChunk rows.
    Embeds each chunk with the mandatory 'passage: ' prefix.
    """
    if file_path.endswith('.pdf'):
        reader = PdfReader(file_path)
        text = '\n\n'.join(page.extract_text() or '' for page in reader.pages)
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

    doc = Document(filename=filename)
    db.session.add(doc)
    db.session.flush()

    chunks = chunk_text(text)
    logger.info(f"Ingesting '{filename}': generated {len(chunks)} chunks.")

    for chunk in chunks:
        # Passage prefix is REQUIRED for e5 embedding storage
        embedding = embed_text(chunk, prefix='passage: ')
        doc_chunk = DocumentChunk(document_id=doc.id, content=chunk)
        doc_chunk.set_embedding(embedding)
        db.session.add(doc_chunk)

    db.session.commit()
    logger.info(f"Successfully ingested '{filename}' (ID: {doc.id}) with {len(chunks)} chunks.")
    return doc

def retrieve(query: str, top_k: int = 5, score_threshold: float = 0.80) -> list[str]:
    """
    Performs cosine similarity search using 'query: ' prefix.
    Filters and logs all retrieved chunks with similarity scores.
    If top similarity score is below score_threshold (0.80), rejects retrieval to avoid hallucination.
    """
    query_clean = query.strip()
    if not query_clean:
        return []

    # Query prefix is REQUIRED for e5 search
    query_embedding = np.array(embed_text(query_clean, prefix='query: '), dtype=np.float32)

    chunks = DocumentChunk.query.all()
    if not chunks:
        logger.info(f"[RAG Retrieval] Knowledge base is empty for query: '{query_clean}'")
        return []

    scored_chunks = []
    for chunk in chunks:
        chunk_embedding_list = chunk.get_embedding()
        if not chunk_embedding_list:
            continue
        chunk_vec = np.array(chunk_embedding_list, dtype=np.float32)
        # Embeddings are L2 normalized, so cosine similarity is simply the dot product
        sim = float(np.dot(query_embedding, chunk_vec))
        scored_chunks.append((sim, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored_chunks[:top_k]

    logger.info(f"[RAG Retrieval] Query: '{query_clean}' | Total chunks searched: {len(chunks)}")
    for rank, (score, chk) in enumerate(top_matches, 1):
        doc_name = chk.document.filename if chk.document else "unknown"
        logger.info(f"  [Match #{rank}] Score: {score:.4f} | Doc: {doc_name} | Snippet: {chk.content[:90]}...")

    if not top_matches:
        return []

    top_score = top_matches[0][0]
    if top_score < score_threshold:
        logger.warning(
            f"[RAG Retrieval] Top score ({top_score:.4f}) is below threshold ({score_threshold}). "
            f"Rejecting retrieval to avoid hallucinating."
        )
        return []

    # Return chunks meeting threshold
    valid_chunks = [chk.content for score, chk in top_matches if score >= score_threshold]
    return valid_chunks
