"""sequential-dependent-calls: two @tool functions; call 2's argument comes from call 1's result."""

from crewai.tools import tool

from tcc_crewai.common import MockTool, Run, execute, load_scenario, tool_spec

SCENARIO_ID = "sequential-dependent-calls"


def run(llm=None) -> Run:
    sc = load_scenario(SCENARIO_ID)
    find_mock = MockTool(tool_spec(sc, "find_user"))
    order_mock = MockTool(tool_spec(sc, "get_latest_order"))

    @tool("find_user")
    def find_user(email: str) -> str:
        """Look up a user id by email."""
        return find_mock(email=email)

    @tool("get_latest_order")
    def get_latest_order(user_id: str) -> str:
        """Get latest order for a user id."""
        return order_mock(user_id=user_id)

    mocks = {"find_user": find_mock, "get_latest_order": order_mock}
    return execute(sc, [find_user, get_latest_order], mocks, llm)
