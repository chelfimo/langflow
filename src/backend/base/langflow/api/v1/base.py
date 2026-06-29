from lfx.template.frontend_node.base import FrontendNode
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer


class CacheResponse(BaseModel):
    data: dict


class Code(BaseModel):
    code: str


class FrontendNodeRequest(FrontendNode):
    template: dict  # type: ignore[assignment]

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        # Override the default serialization method in FrontendNode
        # because we don't need the name in the response (i.e. {name: {}})
        return handler(self)


class ValidatePromptRequest(BaseModel):
    name: str
    template: str
    custom_fields: dict | None = None
    frontend_node: FrontendNodeRequest | None = None
    mustache: bool = False


# Build ValidationResponse class for {"imports": {"errors": []}, "function": {"errors": []}}
class CodeValidationResponse(BaseModel):
    imports: dict
    function: dict

    @field_validator("imports")
    @classmethod
    def validate_imports(cls, v):
        return v or {"errors": []}

    @field_validator("function")
    @classmethod
    def validate_function(cls, v):
        return v or {"errors": []}


class PromptValidationResponse(BaseModel):
    input_variables: list
    # object return for tweak call
    frontend_node: FrontendNodeRequest | None = None


class FlowStructureNode(BaseModel):
    # A flow node carries many fields (data, position, type, ...); only the id is
    # relevant for structural analysis, so extra keys are accepted and ignored.
    model_config = ConfigDict(extra="allow")

    id: str


class FlowStructureEdge(BaseModel):
    # Real flow edges carry handles, styling, etc.; only the endpoints matter here.
    model_config = ConfigDict(extra="allow")

    source: str
    target: str


class FlowStructureRequest(BaseModel):
    nodes: list[FlowStructureNode] = Field(default_factory=list)
    edges: list[FlowStructureEdge] = Field(default_factory=list)


class FlowStructureResponse(BaseModel):
    node_count: int
    edge_count: int
    # Nodes with no incoming edges (entry points).
    root_nodes: list[str]
    # Nodes with no outgoing edges (terminal points).
    leaf_nodes: list[str]
    # Nodes with no connected edges at all.
    isolated_nodes: list[str]
    # True if the directed graph contains at least one cycle (incl. self-loops).
    has_cycles: bool
    # True if every node is reachable from every other when edges are treated as
    # undirected. Graphs with 0 or 1 nodes are trivially connected.
    is_connected: bool
