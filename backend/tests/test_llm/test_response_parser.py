from app.llm.response_parser import extract_json, parse_chart_command, parse_tool_selection


def test_extract_json_pure():
    data = extract_json('{"a": 1}')
    assert data == {"a": 1}


def test_extract_json_from_text():
    data = extract_json('Sure, here it is: {"a": 1} done')
    assert data == {"a": 1}


def test_extract_json_invalid():
    assert extract_json("not json at all") is None


def test_parse_tool_selection_ok():
    parsed = parse_tool_selection('{"tools": ["profile_dataset"], "reason": "x"}')
    assert parsed["tools"] == ["profile_dataset"]


def test_parse_tool_selection_bad_tools_type():
    parsed = parse_tool_selection('{"tools": "profile_dataset"}')
    assert parsed["tools"] == []


def test_parse_chart_command_ok():
    parsed = parse_chart_command(
        '{"action": "add_chart", "chart_type": "bar", "data_mapping": {"x": "region", "y": "revenue"}}'
    )
    assert parsed["action"] == "add_chart"
    assert parsed["chart_type"] == "bar"
    assert parsed["data_mapping"]["x"] == "region"


def test_parse_chart_command_clarification():
    parsed = parse_chart_command('{"action": "unknown", "clarification_needed": true, "clarification_question": "Which metric?"}')
    assert parsed["clarification_needed"] is True
    assert parsed["clarification_question"] == "Which metric?"
