from __future__ import annotations

from app.config import get_settings

from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
)

# Vector search configuration class names can vary slightly by SDK version.
# Use the most common modern names; if your SDK differs, tell me your version and I’ll adjust.
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SemanticConfiguration,
    SemanticSearch,
    PrioritizedFields,
    SemanticField,
)

from app.utils.azure_clients import get_search_index_client


def main() -> None:
    s = get_settings()
    index_client = get_search_index_client(s)

    index_name = s.ai_search_index_chunks

    fields = [
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),

        SearchableField(name="content", type=SearchFieldDataType.String),

        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="vs-default",
        ),

        SearchableField(
            name="keywords",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),

        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
    ]

    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="vs-default",
                algorithm_configuration_name="hnsw-cosine",
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-cosine",
                parameters=HnswParameters(
                    metric="cosine",
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                ),
            )
        ],
    )

    semantic = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=PrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="keywords")],
                ),
            )
        ]
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic,
    )

    index_client.create_or_update_index(index)
    print(f"AI Search index ensured: {index_name}")


if __name__ == "__main__":
    main()