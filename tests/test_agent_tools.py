from agent.tools import get_tool_declarations


def test_all_expected_tools_are_declared():
    declarations = get_tool_declarations()

    names = {
        declaration["name"]
        for declaration in declarations
    }

    assert names == {
        "search_trials",
        "get_trial_evidence",
        "find_data_quality_issues",
        "compare_trials",
    }


def test_required_parameters_are_declared():
    declarations = get_tool_declarations()

    declarations_by_name = {
        declaration["name"]: declaration
        for declaration in declarations
    }

    assert "trial_id" in (
        declarations_by_name["get_trial_evidence"]
        ["parameters"]["required"]
    )

    assert "trial_ids" in (
        declarations_by_name["compare_trials"]
        ["parameters"]["required"]
    )


def test_quality_tool_has_supported_issue_types():
    declarations = get_tool_declarations()

    quality_tool = next(
        declaration
        for declaration in declarations
        if declaration["name"]
        == "find_data_quality_issues"
    )

    issue_type = (
        quality_tool["parameters"]["properties"]
        ["issue_type"]
    )

    assert issue_type["enum"] == [
        "duplicate",
        "conflict",
        "missing_value",
        "single_source",
    ]


def test_tool_declarations_have_descriptions():
    declarations = get_tool_declarations()

    for declaration in declarations:
        assert declaration["name"]
        assert declaration["description"]
        assert declaration["parameters"]