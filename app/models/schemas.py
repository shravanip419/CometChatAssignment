from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str = ""
    title: str = ""
    status: str = "active"  # "active" | "superseded" | "draft"
    effective_date: Optional[str] = None
    superseded_date: Optional[str] = None
    last_reviewed: Optional[str] = None
    audience: str = "customer"  # "customer" | "internal"
    policy_authority: str = "official"  # "official" | "none"
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    customer_answering: bool = True


class DocumentChunk(BaseModel):
    chunk_id: str
    filename: str
    heading: str
    content: str
    metadata: DocumentMetadata


class SourceCitation(BaseModel):
    filename: str
    heading: str

    def __str__(self) -> str:
        return f"{self.filename} - {self.heading}"


class CustomerOrderItem(BaseModel):
    name: str
    quantity: int
    final_sale: bool = False


class CustomerOrder(BaseModel):
    order_id: str
    membership_tier: str
    items: List[CustomerOrderItem] = []
    placed_at: str
    status: str
    status_updated_at: str
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[str] = None
    customer_safe_message: Optional[str] = None


class OrderLookupResult(BaseModel):
    found: bool
    order_id: Optional[str] = None
    order: Optional[CustomerOrder] = None
    message: str = ""
    requires_human_review: bool = False
    is_stale_delivery_suppressed: bool = False


class AgentResponse(BaseModel):
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    handoff: bool = False
    tool_called: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
