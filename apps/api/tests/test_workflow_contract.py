from app.workflow_engine.engine import WORKFLOWS


def test_reference_workflow_order():
    assert WORKFLOWS["intelligence-refresh"] == (
        "features",
        "semantics",
        "graph",
        "discovery",
    )
