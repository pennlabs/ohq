from django.conf import settings
import json
import pinecone
import openai
import time
import tiktoken
import unidecode

from langchain.text_splitter import RecursiveCharacterTextSplitter

from ohq.models import Document

openai.api_key = settings.OPENAI_API_KEY
pinecone.init(api_key=settings.PINECONE_API_KEY, environment='gcp-starter')
index_name = 'ohq-test'

index = pinecone.Index(index_name)

"""
decide which chunking method to use
"""
def chunk_text(text):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size = 256,
            chunk_overlap  = 20,
        )
    texts = []
    for document in text_splitter.create_documents([text]):
        texts.append(document.page_content)
    return texts

def chunk_text_by_token_count(text, max_tokens=8192):
    # Initialize the OpenAI GPT tokenizer - this is the one for GPT 3.5
    tokenizer = tiktoken.get_encoding("cl100k_base")

    current_chunk = ""
    current_tokens = 0

    for word in text.split(" "):
        word_tokens = len(list(tokenizer.encode(word)))
        if current_tokens + word_tokens > max_tokens:
            yield current_chunk
            current_chunk = ""
            current_tokens = 0
        current_chunk += word + " "
        current_tokens += word_tokens

    yield current_chunk

def embed_vectors(chunk):
    response = openai.Embedding.create(model="text-embedding-ada-002", input=chunk)
    return response["data"][0]["embedding"]

def embed_vector_with_metadata(chunk, metadata):
    embedding = embed_vectors(chunk)
    return embedding, metadata

def sanitize_to_ascii(text):
    ascii_text = unidecode.unidecode(text)
    # Replace spaces with underscores
    ascii_text = ascii_text.replace(' ', '_')
    return ascii_text

def search_index(term, top_k=5):
    embedded_term = embed_vectors(term)

    pinecone.init(api_key=settings.PINECONE_API_KEY, environment='gcp-starter')
    index = pinecone.Index(index_name)

    query_response = index.query(vector=[embedded_term], top_k=top_k)

    matches = query_response.get('matches', [])

    results = []
    for match in matches:
        vector_id = match.get('id')
        score = match.get('score')
        results.append(f"Vector ID: {vector_id}, Score: {score}")

    return results, len(matches)

def search_index_with_metadata(term, metadata, top_k=5):
    embedded_term = embed_vectors(term)

    pinecone.init(api_key=settings.PINECONE_API_KEY, environment='gcp-starter')
    index = pinecone.Index(index_name)

    metadata = json.loads(metadata)
    query_response = index.query(vector=[embedded_term], filter=metadata, top_k=top_k, include_metadata=True)

    matches = query_response.get('matches', [])

    results = []
    for match in matches:
        vector_id = match.get('id')
        score = match.get('score')
        m = match.get('metadata')
        results.append(f"Vector ID: {vector_id}, Score: {score}, Metadata: {m}")
    
    return results, len(matches)

def upload_vectors(vector):
    index.upsert(vectors=[vector])

def upload_vectors_with_metadata(embeddings_with_metadata, batch_size):
    # Separate embeddings and metadata
    embeddings = {key: value[0] for key, value in embeddings_with_metadata.items()}
    metadata = {key: {"course": value[1]["course"], 
                      "document_name": value[1]["document_name"], 
                      } 
                for key, value in embeddings_with_metadata.items()}
    
    # Prepare data for batching
    ids_and_embeddings_batches = [dict(list(embeddings.items())[i:i + batch_size]) for i in range(0, len(embeddings), batch_size)]
    metadata_batches = [dict(list(metadata.items())[i:i + batch_size]) for i in range(0, len(metadata), batch_size)]

    # Perform the upsert operation in batches
    for e, m in zip(ids_and_embeddings_batches, metadata_batches):
        # Create a list of IDs and a list of vectors from the embeddings
        ids = list(e.keys())
        vectors = list(e.values())

        for id, vector in zip(ids, vectors):

            vector_obj = {
                'id': str(id),
                'values': vector,
                'metadata': m[id]
            }
            index.upsert(vectors=[vector_obj])
