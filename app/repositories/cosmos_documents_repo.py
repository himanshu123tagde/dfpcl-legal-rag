from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from azure.cosmos import PartitionKey, exceptions

from app.config import Settings
from app.models.documents import DocumentMetadata
from app.models.users import UserClaims, Classification
from app.utils.azure_clients import get_cosmos_client


_CLASSIFICATION_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


def _allowed_classifications(user_clearance: Classification) -> list[str]:
    max_level = _CLASSIFICATION_ORDER.get(user_clearance, 2)
    return [c for c, lvl in _CLASSIFICATION_ORDER.items() if lvl <= max_level]


@dataclass
class CosmosDocumentsRepository:
    settings: Settings

    def __post_init__(self) -> None:
        self._client = get_cosmos_client(self.settings)
        self._db = self._client.create_database_if_not_exists(self.settings.cosmos_db_name)

        # Partition key matches the architecture: /doc_id
        self._container = self._db.create_container_if_not_exists(
            id=self.settings.cosmos_container_documents,
            partition_key=PartitionKey(path="/doc_id"),
        )

    def upsert(self, doc: DocumentMetadata) -> None:
        self._container.upsert_item(doc.model_dump(mode="json"))

    def get_by_doc_id(self, doc_id: str) -> Optional[DocumentMetadata]:
        try:
            item = self._container.read_item(item=doc_id, partition_key=doc_id)
            return DocumentMetadata(**item)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def set_status(self, doc_id: str, status: str) -> None:
        doc = self.get_by_doc_id(doc_id)
        if not doc:
            raise ValueError(f"doc_id not found: {doc_id}")
        doc.status = status  # type: ignore
        doc.updated_at = datetime.utcnow()
        self.upsert(doc)

    def search_stage1(
        self,
        *,
        user: UserClaims,
        keyword: str,
        doc_type: str | None = None,
        jurisdiction: str | None = None,
        limit: int = 25,
    ) -> List[DocumentMetadata]:
        """
        Stage 1-style metadata search (POC):
        - keyword match on title/keywords/parties
        - optional filters: doc_type, jurisdiction
        - RBAC: department/team match (if user has them)
        - classification <= user's clearance
        """

        where = []
        params = [{"name": "@kw", "value": keyword}]

        # keyword in title OR keywords OR parties
        where.append(
            "("
            "CONTAINS(LOWER(c.title), LOWER(@kw)) "
            "OR (IS_DEFINED(c.full_summary) AND CONTAINS(LOWER(c.full_summary), LOWER(@kw))) "
            "OR EXISTS(SELECT VALUE k FROM k IN c.keywords WHERE CONTAINS(LOWER(k), LOWER(@kw))) "
            "OR EXISTS(SELECT VALUE p FROM p IN c.parties WHERE CONTAINS(LOWER(p), LOWER(@kw)))"
            ")"
        )

        if doc_type:
            where.append("c.doc_type = @doc_type")
            params.append({"name": "@doc_type", "value": doc_type})

        if jurisdiction:
            where.append("c.jurisdiction = @jurisdiction")
            params.append({"name": "@jurisdiction", "value": jurisdiction})

        # RBAC (department/team)
        if user.department:
            where.append("c.department = @dept")
            params.append({"name": "@dept", "value": user.department})
        if user.team:
            where.append("c.team = @team")
            params.append({"name": "@team", "value": user.team})

        # classification filter
        allowed = _allowed_classifications(user.clearance)
        # Cosmos SQL doesn't always handle IN consistently across patterns; build OR chain.
        cls_or = " OR ".join([f"c.classification = '{c}'" for c in allowed])
        where.append(f"({cls_or})")

        where_clause = " AND ".join(where)
        query = f"SELECT TOP {limit} * FROM c WHERE {where_clause} ORDER BY c.updated_at DESC"

        items = self._container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )

        return [DocumentMetadata(**it) for it in items]