import pytest
from pydantic import ValidationError

from aunix.spec import ActionPermission
from aunix.testing import make_spec


def test_autonomy_allows_levels_1_to_4():
    assert make_spec(autonomy_level=3, actions=[ActionPermission(type="email", to="x@y.com")]).autonomy_level == 3
    assert make_spec(autonomy_level=4, actions=[ActionPermission(type="resolve")]).autonomy_level == 4


def test_autonomy_rejects_level_5():
    with pytest.raises(ValidationError):
        make_spec(autonomy_level=5)


def test_l3_requires_at_least_one_action():
    with pytest.raises(ValidationError):
        make_spec(autonomy_level=3, actions=[])


def test_l1_l2_forbid_actions():
    with pytest.raises(ValidationError):
        make_spec(autonomy_level=1, actions=[ActionPermission(type="resolve")])


def test_action_permission_defaults():
    p = ActionPermission(type="hubspot", ops=["add_note"])
    assert p.to_field is None and p.to is None and p.ops == ["add_note"]
