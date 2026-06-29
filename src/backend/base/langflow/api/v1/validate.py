from fastapi import APIRouter, Depends, HTTPException
from lfx.base.prompts.api_utils import process_prompt_template
from lfx.custom.validate import validate_code
from lfx.log.logger import logger

from langflow.api.v1.base import (
    Code,
    CodeValidationResponse,
    FlowStructureRequest,
    FlowStructureResponse,
    PromptValidationResponse,
    ValidatePromptRequest,
)
from langflow.services.auth.utils import get_current_active_user

# build router
router = APIRouter(prefix="/validate", tags=["Validate"])


@router.post("/code", status_code=200, dependencies=[Depends(get_current_active_user)], include_in_schema=False)
async def post_validate_code(code: Code) -> CodeValidationResponse:
    try:
        errors = validate_code(code.code)
        return CodeValidationResponse(
            imports=errors.get("imports", {}),
            function=errors.get("function", {}),
        )
    except Exception as e:
        logger.debug("Error validating code", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/prompt", status_code=200, dependencies=[Depends(get_current_active_user)], include_in_schema=False)
async def post_validate_prompt(
    prompt_request: ValidatePromptRequest,
) -> PromptValidationResponse:
    try:
        if not prompt_request.frontend_node:
            return PromptValidationResponse(
                input_variables=[],
                frontend_node=None,
            )

        # Process the prompt template using direct attributes
        input_variables = process_prompt_template(
            template=prompt_request.template,
            name=prompt_request.name,
            custom_fields=prompt_request.frontend_node.custom_fields,
            frontend_node_template=prompt_request.frontend_node.template,
            is_mustache=prompt_request.mustache,
        )

        return PromptValidationResponse(
            input_variables=input_variables,
            frontend_node=prompt_request.frontend_node,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def analyze_flow_structure(node_ids: list[str], edges: list[tuple[str, str]]) -> FlowStructureResponse:
    """Compute deterministic structural metrics for a flow graph.

    The graph is defined purely by node ids and directed (source, target) edges.
    Edges referencing unknown node ids are ignored so a malformed payload cannot
    skew the metrics for the nodes that do exist. Node order from the request is
    preserved in the returned lists to keep results stable.
    """
    known = set(node_ids)
    valid_edges = [(src, tgt) for src, tgt in edges if src in known and tgt in known]

    has_incoming = {tgt for _, tgt in valid_edges}
    has_outgoing = {src for src, _ in valid_edges}

    root_nodes = [n for n in node_ids if n not in has_incoming]
    leaf_nodes = [n for n in node_ids if n not in has_outgoing]
    isolated_nodes = [n for n in node_ids if n not in has_incoming and n not in has_outgoing]

    return FlowStructureResponse(
        node_count=len(node_ids),
        edge_count=len(edges),
        root_nodes=root_nodes,
        leaf_nodes=leaf_nodes,
        isolated_nodes=isolated_nodes,
        has_cycles=_has_cycle(known, valid_edges),
        is_connected=_is_weakly_connected(node_ids, valid_edges),
    )


def _has_cycle(nodes: set[str], edges: list[tuple[str, str]]) -> bool:
    """Detect a cycle (including self-loops) in a directed graph via DFS coloring."""
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for src, tgt in edges:
        adjacency[src].append(tgt)

    # 0 = unvisited, 1 = in current DFS stack, 2 = fully explored
    state = dict.fromkeys(nodes, 0)

    def visit(node: str) -> bool:
        state[node] = 1
        for neighbor in adjacency[node]:
            if state[neighbor] == 1 or (state[neighbor] == 0 and visit(neighbor)):
                return True
        state[node] = 2
        return False

    return any(state[node] == 0 and visit(node) for node in nodes)


def _is_weakly_connected(node_ids: list[str], edges: list[tuple[str, str]]) -> bool:
    """Return True if treating edges as undirected leaves a single component.

    Graphs with 0 or 1 nodes are trivially connected.
    """
    if len(node_ids) <= 1:
        return True

    adjacency: dict[str, set[str]] = {n: set() for n in node_ids}
    for src, tgt in edges:
        adjacency[src].add(tgt)
        adjacency[tgt].add(src)

    start = node_ids[0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbor in adjacency[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)

    return len(seen) == len(node_ids)


@router.post("/flow", status_code=200, dependencies=[Depends(get_current_active_user)])
async def post_validate_flow(flow_request: FlowStructureRequest) -> FlowStructureResponse:
    """Analyze a flow's graph structure and return deterministic diagnostics.

    Accepts the standard flow ``data`` payload (``nodes`` and ``edges``) and reports
    node/edge counts, root/leaf/isolated nodes, cycle presence, and connectivity. It
    is a lightweight structural linter: it does not build or execute the graph.
    """
    try:
        node_ids = [node.id for node in flow_request.nodes]
        edges = [(edge.source, edge.target) for edge in flow_request.edges]
        return analyze_flow_structure(node_ids, edges)
    except Exception as e:
        logger.debug("Error analyzing flow structure", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
