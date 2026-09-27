import pytest
from pydantic import ValidationError

from pokemon_agent.models import Button, ButtonAction, CellKind, Viewport


def test_button_action_requires_hold_to_fit_inside_step() -> None:
    with pytest.raises(ValidationError):
        ButtonAction(button=Button.DOWN, hold_frames=10, frames=5)


def test_viewport_validates_matrix_dimensions() -> None:
    viewport = Viewport(
        width=2,
        height=1,
        tile_ids=((1, 2),),
        walkable=((True, False),),
        semantic=((CellKind.WALKABLE, CellKind.BLOCKED),),
    )
    assert viewport.semantic[0][1] == CellKind.BLOCKED

    with pytest.raises(ValidationError):
        Viewport(width=2, height=1, tile_ids=((1,),))
