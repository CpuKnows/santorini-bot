# pylint: disable=C,W,R
import os
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, Generator

import numpy as np
import numpy.typing as npt
import pytest

from santorini_bot.app import App
from santorini_bot.board import Board, Color, TurnActions, Worker
from santorini_bot.game import GameManager


@dataclass
class BoardParameters:
    length: int
    width: int
    max_height: int
    max_workers_per_player: int


@dataclass
class UpdateGameStateParameters:
    turn_action: TurnActions
    turn_coordinates: list[int]
    active_player: Optional[Color] = None


class TestSaveLoadLoop:
    @dataclass
    class Parameters:
        description: str
        game_manager_player_order: Optional[Iterable[Color]]
        board_parameters: BoardParameters
        update_game_state_parameters: Optional[List[UpdateGameStateParameters]]
        expected_active_player: Color
        expected_workers: set[Worker]
        expected_block_heights: npt.NDArray[np.int_]
        expected_turn_action: TurnActions = TurnActions.PLACE_WORKER

    @dataclass
    class Fixture:
        expected_board_length: int
        expected_board_width: int
        expected_board_max_height: int
        expected_board_max_workers_per_player: int
        test_board_length: int
        test_board_width: int
        test_board_max_height: int
        test_board_max_workers_per_player: int
        expected_turn_action: TurnActions
        test_turn_action: TurnActions
        expected_active_player: Color
        test_active_player: Color
        expected_workers: set[Worker]
        test_workers: set[Worker]
        expected_block_heights: npt.NDArray[np.int_]
        test_block_heights: npt.NDArray[np.int_]

    @pytest.fixture(
        params=[
            Parameters(
                description="Board setup, no moves",
                game_manager_player_order=None,
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=None,
                expected_active_player=Color.BLUE,
                expected_turn_action=TurnActions.PLACE_WORKER,
                expected_workers=set(),
                expected_block_heights=np.zeros(shape=(3, 3), dtype=int),
            ),
            Parameters(
                description="Place worker turn next",
                game_manager_player_order=None,
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=[
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[0, 0],
                    ),
                ],
                expected_active_player=Color.WHITE,
                expected_turn_action=TurnActions.PLACE_WORKER,
                expected_workers={Worker(x=0, y=0, height=0, color=Color.BLUE)},
                expected_block_heights=np.zeros(shape=(3, 3), dtype=int),
            ),
            Parameters(
                description="Move turn next",
                game_manager_player_order=None,
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=[
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[0, 0],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[1, 1],
                    ),
                ],
                expected_active_player=Color.BLUE,
                expected_turn_action=TurnActions.MOVE,
                expected_workers={
                    Worker(x=0, y=0, height=0, color=Color.BLUE),
                    Worker(x=1, y=1, height=0, color=Color.WHITE),
                },
                expected_block_heights=np.zeros(shape=(3, 3), dtype=int),
            ),
            Parameters(
                description="Build turn next",
                game_manager_player_order=None,
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=[
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[0, 0],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[1, 1],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.MOVE,
                        turn_coordinates=[0, 0, 1, 0],
                    ),
                ],
                expected_active_player=Color.BLUE,
                expected_turn_action=TurnActions.BUILD,
                expected_workers={
                    Worker(x=1, y=0, height=0, color=Color.BLUE),
                    Worker(x=1, y=1, height=0, color=Color.WHITE),
                },
                expected_block_heights=np.zeros(shape=(3, 3), dtype=int),
            ),
            Parameters(
                description="Next player move turn next",
                game_manager_player_order=None,
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=[
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[0, 0],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.PLACE_WORKER,
                        turn_coordinates=[1, 1],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.MOVE,
                        turn_coordinates=[0, 0, 1, 0],
                    ),
                    UpdateGameStateParameters(
                        turn_action=TurnActions.BUILD,
                        turn_coordinates=[1, 0, 2, 0],
                    ),
                ],
                expected_active_player=Color.WHITE,
                expected_turn_action=TurnActions.MOVE,
                expected_workers={
                    Worker(x=1, y=0, height=0, color=Color.BLUE),
                    Worker(x=1, y=1, height=0, color=Color.WHITE),
                },
                expected_block_heights=np.array(
                    [
                        [0, 0, 1],
                        [0, 0, 0],
                        [0, 0, 0],
                    ]
                ),
            ),
            Parameters(
                description="Custom player order",
                game_manager_player_order=[Color.WHITE, Color.BLUE],
                board_parameters=BoardParameters(
                    length=3,
                    width=3,
                    max_height=2,
                    max_workers_per_player=1,
                ),
                update_game_state_parameters=None,
                expected_active_player=Color.WHITE,
                expected_turn_action=TurnActions.PLACE_WORKER,
                expected_workers=set(),
                expected_block_heights=np.zeros(shape=(3, 3), dtype=int),
            ),
        ],
        ids=lambda x: x.description,
    )
    def setup(
        self,
        tmp_path,
        request,
    ) -> Generator[Fixture, None, None]:
        param: TestSaveLoadLoop.Parameters = request.param

        # setup Board
        if param.board_parameters is not None:
            board = Board(**asdict(param.board_parameters))
        else:
            board = None

        # setup GameManager
        game_manager_kwargs = dict(
            player_order=param.game_manager_player_order, board=board
        )
        game_manager_kwargs = dict(
            (k, v) for k, v in game_manager_kwargs.items() if v is not None
        )
        if (
            param.board_parameters is not None
            or param.game_manager_player_order is not None
        ):
            game_manager = GameManager(**game_manager_kwargs)  # type: ignore
        else:
            game_manager = None

        # setup App
        app = App(game_manager=game_manager)
        if param.update_game_state_parameters is not None:
            for game_state_parameters in param.update_game_state_parameters:
                app.game_manager.update_game_state(**asdict(game_state_parameters))

        # save and load loop
        app.save_game(path=tmp_path / "test_save_load_loop.log")
        app.load_game(path=tmp_path / "test_save_load_loop.log")

        yield self.Fixture(
            expected_board_length=param.board_parameters.length,
            expected_board_width=param.board_parameters.width,
            expected_board_max_height=param.board_parameters.max_height,
            expected_board_max_workers_per_player=param.board_parameters.max_workers_per_player,
            test_board_length=app.game_manager.board.length,
            test_board_width=app.game_manager.board.width,
            test_board_max_height=app.game_manager.board.max_height,
            test_board_max_workers_per_player=app.game_manager.board.max_workers_per_player,
            expected_turn_action=param.expected_turn_action,
            test_turn_action=app.game_manager.current_turn_action,
            expected_active_player=param.expected_active_player,
            test_active_player=app.game_manager.active_player,
            expected_workers=param.expected_workers,
            test_workers=set(app.game_manager.board.workers),
            expected_block_heights=param.expected_block_heights,
            test_block_heights=app.game_manager.board.board_blocks,
        )

        # clean up
        try:
            os.remove(tmp_path)
        except PermissionError:
            pass

    def test_board_parameters(self, setup: Fixture):
        expected_parameters = BoardParameters(
            length=setup.expected_board_length,
            width=setup.expected_board_width,
            max_height=setup.expected_board_max_height,
            max_workers_per_player=setup.expected_board_max_workers_per_player,
        )

        test_parameters = BoardParameters(
            length=setup.test_board_length,
            width=setup.test_board_width,
            max_height=setup.test_board_max_height,
            max_workers_per_player=setup.test_board_max_workers_per_player,
        )
        assert test_parameters == expected_parameters

    def test_next_turn_action(self, setup: Fixture):
        assert setup.test_turn_action == setup.expected_turn_action

    def test_next_active_player(self, setup: Fixture):
        assert setup.test_active_player == setup.expected_active_player

    def test_workers_at_coordinates(self, setup: Fixture):
        assert setup.test_workers == setup.expected_workers

    def test_block_heights(self, setup: Fixture):
        # assert setup.test_block_heights == setup.expected_block_heights
        np.testing.assert_array_equal(
            setup.test_block_heights, setup.expected_block_heights
        )
