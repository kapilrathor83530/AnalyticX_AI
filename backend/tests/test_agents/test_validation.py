from app.agents.validation_layer import validate_columns, validate_result_shape, validate_tool_names


def test_validate_tool_names_filters():
    assert validate_tool_names(["profile_dataset", "evil_tool"]) == ["profile_dataset"]


def test_validate_columns_filters():
    assert validate_columns(["a", "b", "z"], ["a", "b", "c"]) == ["a", "b"]


def test_validate_result_shape():
    assert validate_result_shape({}) is True
    assert validate_result_shape([]) is False
