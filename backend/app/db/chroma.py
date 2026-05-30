import chromadb
from chromadb.config import Settings
from app.config import get_settings

_settings = get_settings()
_client = None
_collection = None


def get_chroma_client():
    global _client
    if _client is None:
        if _settings.CHROMA_HOST and _settings.CHROMA_PORT:
            try:
                _client = chromadb.HttpClient(
                    host=_settings.CHROMA_HOST,
                    port=int(_settings.CHROMA_PORT),
                    settings=Settings(anonymized_telemetry=False),
                )
            except Exception:
                # Fallback for version mismatch - try with different settings
                _client = chromadb.HttpClient(
                    host=_settings.CHROMA_HOST,
                    port=int(_settings.CHROMA_PORT),
                    settings=Settings(
                        anonymized_telemetry=False,
                        chroma_api_impl="chromadb.api.segment.SegmentAPI",
                        chroma_server_host=_settings.CHROMA_HOST,
                        chroma_server_http_port=int(_settings.CHROMA_PORT),
                    ),
                )
        else:
            _client = chromadb.PersistentClient(path="./chroma_data")
    return _client


def get_or_create_collection(name: str = "documents"):
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection
