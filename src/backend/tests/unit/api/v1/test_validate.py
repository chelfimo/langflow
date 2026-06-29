import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.usefixtures("active_user")
async def test_post_validate_code(client: AsyncClient, logged_in_headers):
    good_code = """
from pprint import pprint
var = {"a": 1, "b": 2}
pprint(var)
    """
    response = await client.post("api/v1/validate/code", json={"code": good_code}, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(result, dict), "The result must be a dictionary"
    assert "imports" in result, "The result must have an 'imports' key"
    assert "function" in result, "The result must have a 'function' key"


@pytest.mark.usefixtures("active_user")
async def test_post_validate_prompt(client: AsyncClient, logged_in_headers):
    basic_case = {
        "name": "string",
        "template": "string",
        "custom_fields": {},
        "frontend_node": {
            "template": {},
            "description": "string",
            "icon": "string",
            "is_input": True,
            "is_output": True,
            "is_composition": True,
            "base_classes": ["string"],
            "name": "",
            "display_name": "",
            "documentation": "",
            "custom_fields": {},
            "output_types": [],
            "full_path": "string",
            "pinned": False,
            "conditional_paths": [],
            "frozen": False,
            "outputs": [],
            "field_order": [],
            "beta": False,
            "minimized": False,
            "error": "string",
            "edited": False,
            "metadata": {},
        },
    }
    response = await client.post("api/v1/validate/prompt", json=basic_case, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(result, dict), "The result must be a dictionary"
    assert "frontend_node" in result, "The result must have a 'frontend_node' key"
    assert "input_variables" in result, "The result must have an 'input_variables' key"


@pytest.mark.usefixtures("active_user")
async def test_post_validate_prompt_with_invalid_data(client: AsyncClient, logged_in_headers):
    invalid_case = {
        "name": "string",
        # Missing required fields
        "frontend_node": {"template": {}, "is_input": True},
    }
    response = await client.post("api/v1/validate/prompt", json=invalid_case, headers=logged_in_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_post_validate_code_with_unauthenticated_user(client: AsyncClient):
    code = """
    print("Hello World")
    """
    response = await client.post("api/v1/validate/code", json={"code": code}, headers={"Authorization": "Bearer fake"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_empty(client: AsyncClient, logged_in_headers):
    response = await client.post("api/v1/validate/flow", json={}, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result == {
        "node_count": 0,
        "edge_count": 0,
        "root_nodes": [],
        "leaf_nodes": [],
        "isolated_nodes": [],
        "has_cycles": False,
        "is_connected": True,
    }


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_simple_chain(client: AsyncClient, logged_in_headers):
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["node_count"] == 3
    assert result["edge_count"] == 2
    assert result["root_nodes"] == ["a"]
    assert result["leaf_nodes"] == ["c"]
    assert result["isolated_nodes"] == []
    assert result["has_cycles"] is False
    assert result["is_connected"] is True


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_detects_cycle(client: AsyncClient, logged_in_headers):
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["has_cycles"] is True
    assert result["root_nodes"] == []
    assert result["leaf_nodes"] == []
    assert result["is_connected"] is True


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_detects_self_loop(client: AsyncClient, logged_in_headers):
    payload = {"nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "a"}]}
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["has_cycles"] is True
    # A self-looping node has both an incoming and outgoing edge, so it is neither
    # a root, a leaf, nor isolated.
    assert result["root_nodes"] == []
    assert result["leaf_nodes"] == []
    assert result["isolated_nodes"] == []


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_disconnected_components(client: AsyncClient, logged_in_headers):
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
        "edges": [{"source": "a", "target": "b"}, {"source": "c", "target": "d"}],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["is_connected"] is False
    assert result["has_cycles"] is False
    assert result["root_nodes"] == ["a", "c"]
    assert result["leaf_nodes"] == ["b", "d"]


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_isolated_node(client: AsyncClient, logged_in_headers):
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "lonely"}],
        "edges": [{"source": "a", "target": "b"}],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["isolated_nodes"] == ["lonely"]
    assert result["is_connected"] is False


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_ignores_dangling_edges(client: AsyncClient, logged_in_headers):
    # An edge referencing an unknown node id must not affect the known nodes' metrics.
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "ghost"}],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    # edge_count reflects the raw payload, but "b" stays a leaf because the dangling
    # edge to "ghost" is excluded from structural analysis.
    assert result["edge_count"] == 2
    assert result["root_nodes"] == ["a"]
    assert result["leaf_nodes"] == ["b"]
    assert result["has_cycles"] is False


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_accepts_real_flow_node_fields(client: AsyncClient, logged_in_headers):
    # Real flow nodes/edges carry many extra fields; they must be accepted and ignored.
    payload = {
        "nodes": [
            {"id": "ChatInput-1", "type": "genericNode", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "ChatOutput-1", "type": "genericNode", "position": {"x": 1, "y": 1}, "data": {}},
        ],
        "edges": [
            {
                "source": "ChatInput-1",
                "target": "ChatOutput-1",
                "sourceHandle": "out",
                "targetHandle": "in",
                "animated": False,
            }
        ],
    }
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["node_count"] == 2
    assert result["edge_count"] == 1
    assert result["root_nodes"] == ["ChatInput-1"]
    assert result["leaf_nodes"] == ["ChatOutput-1"]
    assert result["is_connected"] is True


@pytest.mark.usefixtures("active_user")
async def test_post_validate_flow_invalid_edge(client: AsyncClient, logged_in_headers):
    # Edges missing required source/target should be rejected by request validation.
    payload = {"nodes": [{"id": "a"}], "edges": [{"source": "a"}]}
    response = await client.post("api/v1/validate/flow", json=payload, headers=logged_in_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_post_validate_flow_with_unauthenticated_user(client: AsyncClient):
    response = await client.post(
        "api/v1/validate/flow", json={"nodes": [], "edges": []}, headers={"Authorization": "Bearer fake"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
