# pylint: disable=C,W,R
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Optional
from unittest.mock import Mock, patch, PropertyMock

import pytest

from santorini_bot.board import Color, IllegalMoveError, TurnActions, TurnArgs, MoveTurn
from santorini_bot.game import GameManager, GameState


class TestUpdateGameState:
    @dataclass
    class Parameters:
        description: str
        initial_player_order: Iterable[Color]
        initial_turn_order: deque[TurnActions]
        next_turn_action: TurnActions
        next_turn_coordinates: list[int]
        next_active_player: Optional[Color]
        previous_turn_action: Optional[TurnActions]
        previous_turn: Optional[TurnArgs]
        in_lose_state_after_move: bool
        in_win_state_after_move: bool

    @dataclass
    class Fixture:
        game_manager: GameManager
        next_turn_action: TurnActions
        mock_place_worker: Mock
        mock_move: Mock
        mock_build: Mock
        mock_check_moved_worker_before_build: Mock
        mock_change_active_player: Mock
        mock_change_current_turn_action: Mock
        initial_game_state_log_len: int
        in_lose_state_after_move: bool
        in_win_state_after_move: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="Place Worker turn",
                initial_player_order=[Color.BLUE, Color.WHITE],
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                next_turn_action=TurnActions.PLACE_WORKER,
                next_turn_coordinates=[0, 0],
                next_active_player=Color.BLUE,
                previous_turn_action=None,
                previous_turn=None,
                in_lose_state_after_move=False,
                in_win_state_after_move=False,
            ),
            Parameters(
                description="Move turn",
                initial_player_order=[Color.BLUE, Color.WHITE],
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                next_turn_action=TurnActions.MOVE,
                next_turn_coordinates=[0, 0, 1, 1],
                next_active_player=Color.BLUE,
                previous_turn_action=None,
                previous_turn=None,
                in_lose_state_after_move=False,
                in_win_state_after_move=False,
            ),
            Parameters(
                description="Move turn, in lose state after move",
                initial_player_order=[Color.BLUE, Color.WHITE],
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                next_turn_action=TurnActions.MOVE,
                next_turn_coordinates=[0, 0, 1, 1],
                next_active_player=Color.BLUE,
                previous_turn_action=None,
                previous_turn=None,
                in_lose_state_after_move=True,
                in_win_state_after_move=False,
            ),
            Parameters(
                description="Move turn, in win state after move",
                initial_player_order=[Color.BLUE, Color.WHITE],
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                next_turn_action=TurnActions.MOVE,
                next_turn_coordinates=[0, 0, 1, 1],
                next_active_player=Color.BLUE,
                previous_turn_action=None,
                previous_turn=None,
                in_lose_state_after_move=False,
                in_win_state_after_move=True,
            ),
            Parameters(
                description="Build turn",
                initial_player_order=[Color.BLUE, Color.WHITE],
                initial_turn_order=deque([TurnActions.BUILD, TurnActions.MOVE]),
                next_turn_action=TurnActions.BUILD,
                next_turn_coordinates=[0, 0, 1, 1],
                next_active_player=Color.BLUE,
                previous_turn_action=TurnActions.MOVE,
                previous_turn=MoveTurn(
                    color=Color.WHITE, start_x=0, start_y=1, end_x=0, end_y=0
                ),
                in_lose_state_after_move=False,
                in_win_state_after_move=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.game.GameManager._change_current_turn_action", autospec=True)
    @patch("santorini_bot.game.GameManager._change_active_player", autospec=True)
    @patch(
        "santorini_bot.game.GameManager._check_moved_worker_before_build", autospec=True
    )
    @patch(
        "santorini_bot.game.GameManager._check_win_state_board_win_state", autospec=True
    )
    @patch("santorini_bot.board.Board.build", autospec=True)
    @patch("santorini_bot.board.Board.move", autospec=True)
    @patch("santorini_bot.board.Board.place_worker", autospec=True)
    @patch("santorini_bot.board.Board.player_can_place_workers", autospec=True)
    @patch("santorini_bot.board.Board.player_in_lose_state_after_move", autospec=True)
    def setup(
        self,
        mock_player_in_lose_state_after_move: Mock,
        mock_player_can_place_workers: Mock,
        mock_place_worker: Mock,
        mock_move: Mock,
        mock_build: Mock,
        mock_check_win_state_board_win_state: Mock,
        mock_check_moved_worker_before_build: Mock,
        mock_change_active_player: Mock,
        mock_change_current_turn_action: Mock,
        request,
    ):
        param: TestUpdateGameState.Parameters = request.param

        mock_player_in_lose_state_after_move.return_value = (
            param.in_lose_state_after_move
        )
        mock_check_win_state_board_win_state.return_value = (
            param.in_win_state_after_move
        )

        mock_player_can_place_workers.return_value = (
            True if param.next_turn_action == TurnActions.PLACE_WORKER else False
        )
        mock_check_moved_worker_before_build.return_value = None

        game_manager = GameManager(player_order=param.initial_player_order)
        game_manager.turn_order = deepcopy(param.initial_turn_order)
        if param.previous_turn_action is not None and param.previous_turn is not None:
            game_manager.game_state_log = [
                GameState(
                    active_player=Mock(),
                    board=Mock(),
                    turn_action=param.previous_turn_action,
                    turn=param.previous_turn,
                )
            ]

        initial_game_state_log_len = len(game_manager.game_state_log)

        game_manager.update_game_state(
            turn_action=param.next_turn_action,
            turn_coordinates=param.next_turn_coordinates,
            active_player=param.next_active_player,
        )

        return self.Fixture(
            game_manager=game_manager,
            next_turn_action=param.next_turn_action,
            mock_place_worker=mock_place_worker,
            mock_move=mock_move,
            mock_build=mock_build,
            mock_check_moved_worker_before_build=mock_check_moved_worker_before_build,
            mock_change_active_player=mock_change_active_player,
            mock_change_current_turn_action=mock_change_current_turn_action,
            initial_game_state_log_len=initial_game_state_log_len,
            in_lose_state_after_move=param.in_lose_state_after_move,
            in_win_state_after_move=param.in_win_state_after_move,
        )

    def test_calls_correct_board_turn_action(self, setup: Fixture):
        if setup.next_turn_action == TurnActions.PLACE_WORKER:
            setup.mock_place_worker.assert_called()
        elif setup.next_turn_action == TurnActions.MOVE:
            setup.mock_move.assert_called()
        elif setup.next_turn_action == TurnActions.BUILD:
            setup.mock_build.assert_called()
        else:
            ValueError(f"Unexpected turn action: {setup.next_turn_action}")

    def test_calls_check_moved_worker_before_build(self, setup: Fixture):
        if setup.next_turn_action == TurnActions.BUILD:
            setup.mock_check_moved_worker_before_build.assert_called()

    def test_updates_game_state_log(self, setup: Fixture):
        assert (
            len(setup.game_manager.game_state_log)
            == setup.initial_game_state_log_len + 1
        )

    def test_updates_player_order(self, setup: Fixture):
        if not setup.in_win_state_after_move and (
            setup.next_turn_action != TurnActions.MOVE or setup.in_lose_state_after_move
        ):
            setup.mock_change_active_player.assert_called()

    def test_updates_turn_order(self, setup: Fixture):
        if not setup.in_win_state_after_move and not setup.in_lose_state_after_move:
            setup.mock_change_current_turn_action.assert_called()

    @pytest.mark.parametrize(
        "initial_player_order,next_active_player",
        [([Color.BLUE, Color.WHITE], Color.WHITE)],
    )
    def test_raise_error_player_out_of_order(
        self, initial_player_order: Iterable[Color], next_active_player: Color
    ):
        game_manager = GameManager(player_order=initial_player_order)

        with pytest.raises(IllegalMoveError, match=r"Player turn is out of order.*"):
            game_manager.update_game_state(
                turn_action=Mock(),
                turn_coordinates=Mock(),
                active_player=next_active_player,
            )

    @pytest.mark.parametrize(
        "initial_turn_order,next_turn_action",
        [(deque([TurnActions.MOVE, TurnActions.BUILD]), TurnActions.BUILD)],
    )
    @patch("santorini_bot.board.Board.player_can_place_workers", autospec=True)
    def test_raise_error_action_out_of_order(
        self,
        mock_player_can_place_workers: Mock,
        initial_turn_order: deque[TurnActions],
        next_turn_action: TurnActions,
    ):
        game_manager = GameManager(player_order=[Color.BLUE, Color.WHITE])
        game_manager.turn_order = deepcopy(initial_turn_order)

        mock_player_can_place_workers.return_value = False

        with pytest.raises(IllegalMoveError, match=r"Turn action is out of order.*"):
            game_manager.update_game_state(
                turn_action=next_turn_action,
                turn_coordinates=Mock(),
                active_player=Color.BLUE,
            )


class TestCheckMovedWorkerBeforeBuild:
    @pytest.mark.parametrize(
        "previous_turn,next_turn_coordinates",
        [
            (
                MoveTurn(color=Color.WHITE, start_x=0, start_y=1, end_x=0, end_y=2),
                [0, 0, 1, 1],
            )
        ],
    )
    @patch("santorini_bot.board.Board.player_can_place_workers", autospec=True)
    def test_raise_error_build_with_different_worker_from_move(
        self,
        mock_player_can_place_workers: Mock,
        previous_turn: TurnArgs,
        next_turn_coordinates: list[int],
    ):
        game_manager = GameManager(player_order=[Color.BLUE, Color.WHITE])
        game_manager.turn_order = deque([TurnActions.BUILD, TurnActions.MOVE])
        game_manager.game_state_log = [
            GameState(
                active_player=Mock(),
                board=Mock(),
                turn_action=TurnActions.MOVE,
                turn=previous_turn,
            )
        ]

        mock_player_can_place_workers.return_value = False

        with pytest.raises(
            IllegalMoveError, match=r"Must build with the last worker to move.*"
        ):
            game_manager.update_game_state(
                turn_action=TurnActions.BUILD,
                turn_coordinates=next_turn_coordinates,
                active_player=Color.BLUE,
            )


def test_change_active_player():
    game_manager = GameManager(player_order=[Color.BLUE, Color.WHITE])
    game_manager._change_active_player()
    assert (
        game_manager.active_player == Color.WHITE
        and game_manager.player_order == deque([Color.WHITE, Color.BLUE])
    )


class TestChangeCurrentTurnAction:
    @dataclass
    class Parameters:
        description: str
        player_can_place_workers: bool
        initial_turn_order: deque[TurnActions]
        previous_turn_action: Optional[TurnActions]
        expected_current_turn_action: TurnActions
        expected_turn_order: deque[TurnActions]

    @dataclass
    class Fixture:
        expected_current_turn_action: TurnActions
        expected_turn_order: deque[TurnActions]
        current_turn_action: TurnActions
        turn_order: deque[TurnActions]

    @pytest.fixture(
        params=[
            Parameters(
                description="Can place workers",
                player_can_place_workers=True,
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                previous_turn_action=None,
                expected_current_turn_action=TurnActions.PLACE_WORKER,
                expected_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
            ),
            Parameters(
                description="Cannot place workers, previous action is place",
                player_can_place_workers=False,
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                previous_turn_action=TurnActions.PLACE_WORKER,
                expected_current_turn_action=TurnActions.MOVE,
                expected_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
            ),
            Parameters(
                description="Cannot place workers, previous action is move",
                player_can_place_workers=False,
                initial_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
                previous_turn_action=TurnActions.MOVE,
                expected_current_turn_action=TurnActions.BUILD,
                expected_turn_order=deque([TurnActions.BUILD, TurnActions.MOVE]),
            ),
            Parameters(
                description="Cannot place workers, previous action is build",
                player_can_place_workers=False,
                initial_turn_order=deque([TurnActions.BUILD, TurnActions.MOVE]),
                previous_turn_action=TurnActions.BUILD,
                expected_current_turn_action=TurnActions.MOVE,
                expected_turn_order=deque([TurnActions.MOVE, TurnActions.BUILD]),
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board.player_can_place_workers", autospec=True)
    def setup(self, mock_player_can_place_workers: Mock, request):
        param: TestChangeCurrentTurnAction.Parameters = request.param

        mock_player_can_place_workers.return_value = param.player_can_place_workers

        game_manager = GameManager()
        game_manager.turn_order = deepcopy(param.initial_turn_order)
        if param.previous_turn_action is not None:
            game_manager.game_state_log = [
                GameState(
                    active_player=Mock(),
                    board=Mock(),
                    turn_action=param.previous_turn_action,
                    turn=Mock(),
                )
            ]

        game_manager._change_current_turn_action()

        return self.Fixture(
            expected_current_turn_action=param.expected_current_turn_action,
            expected_turn_order=param.expected_turn_order,
            current_turn_action=game_manager.current_turn_action,
            turn_order=game_manager.turn_order,
        )

    def test_current_turn_action(self, setup: Fixture):
        assert setup.current_turn_action == setup.expected_current_turn_action

    def test_turn_order(self, setup: Fixture):
        assert setup.turn_order == setup.expected_turn_order


class TestCheckLoseStatePlayerCantBuild:
    @dataclass
    class Parameters:
        description: str
        previous_game_state_exists: bool
        initial_player_order: deque[Color]
        final_player_order: deque[Color]
        previous_turn_action: TurnActions
        player_in_lose_state_after_move: bool
        expect_log_message: bool

    @dataclass
    class Fixture:
        expected_player_order: deque[Color]
        test_player_order: deque[Color]
        player_in_lose_state_after_move: bool
        captured_log: str
        expect_log_message: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="No previous game states",
                previous_game_state_exists=False,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                previous_turn_action=TurnActions.MOVE,
                player_in_lose_state_after_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="One player in player order",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE]),
                final_player_order=deque([Color.BLUE]),
                previous_turn_action=TurnActions.MOVE,
                player_in_lose_state_after_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="Previous action is place worker",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                previous_turn_action=TurnActions.PLACE_WORKER,
                player_in_lose_state_after_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="Previous action is build",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                previous_turn_action=TurnActions.BUILD,
                player_in_lose_state_after_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="In lose state after move",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.WHITE]),
                previous_turn_action=TurnActions.MOVE,
                player_in_lose_state_after_move=True,
                expect_log_message=True,
            ),
            Parameters(
                description="Not in lose state after move",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                previous_turn_action=TurnActions.MOVE,
                player_in_lose_state_after_move=False,
                expect_log_message=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch(
        "santorini_bot.game.GameManager.previous_game_state", new_callable=PropertyMock
    )
    def setup(
        self,
        mock_previous_game_state_property: Mock,
        caplog,
        request,
    ) -> Fixture:
        param: TestCheckLoseStatePlayerCantBuild.Parameters = request.param

        if not param.previous_game_state_exists:
            mock_previous_game_state_property.return_value = None

        game_manager = GameManager(player_order=param.initial_player_order)

        if param.previous_game_state_exists:
            type(
                game_manager.previous_game_state
            ).turn_action = param.previous_turn_action  # type: ignore
            type(  # type: ignore
                game_manager.previous_game_state
            ).active_player = param.initial_player_order[0]
            game_manager.previous_game_state.board.player_in_lose_state_after_move.return_value = (  # type: ignore # noqa: E501
                param.player_in_lose_state_after_move
            )

        game_manager._check_lose_state_player_cant_build()

        return self.Fixture(
            expected_player_order=param.final_player_order,
            test_player_order=game_manager.player_order,
            player_in_lose_state_after_move=param.player_in_lose_state_after_move,
            captured_log=caplog.text,
            expect_log_message=param.expect_log_message,
        )

    def test_display_message_if_in_lose_state(self, setup: Fixture):
        if setup.expect_log_message:
            assert "lost! No valid builds." in setup.captured_log

    def test_expected_player_order(self, setup: Fixture):
        assert setup.test_player_order == setup.expected_player_order


class TestCheckLoseStatePlayerCantMove:
    @dataclass
    class Parameters:
        description: str
        previous_game_state_exists: bool
        initial_player_order: deque[Color]
        final_player_order: deque[Color]
        current_turn_action: TurnActions
        player_in_lose_state_before_move: bool
        expect_log_message: bool

    @dataclass
    class Fixture:
        expected_player_order: deque[Color]
        test_player_order: deque[Color]
        player_in_lose_state_before_move: bool
        captured_log: str
        expect_log_message: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="No previous game states",
                previous_game_state_exists=False,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                current_turn_action=TurnActions.MOVE,
                player_in_lose_state_before_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="One player in player order",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE]),
                final_player_order=deque([Color.BLUE]),
                current_turn_action=TurnActions.MOVE,
                player_in_lose_state_before_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="Current action is place worker",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                current_turn_action=TurnActions.PLACE_WORKER,
                player_in_lose_state_before_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="Current action is build",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                current_turn_action=TurnActions.BUILD,
                player_in_lose_state_before_move=True,
                expect_log_message=False,
            ),
            Parameters(
                description="In lose state before move",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.WHITE]),
                current_turn_action=TurnActions.MOVE,
                player_in_lose_state_before_move=True,
                expect_log_message=True,
            ),
            Parameters(
                description="Not in lose state before move",
                previous_game_state_exists=True,
                initial_player_order=deque([Color.BLUE, Color.WHITE]),
                final_player_order=deque([Color.BLUE, Color.WHITE]),
                current_turn_action=TurnActions.MOVE,
                player_in_lose_state_before_move=False,
                expect_log_message=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch(
        "santorini_bot.game.GameManager.previous_game_state", new_callable=PropertyMock
    )
    @patch(
        "santorini_bot.game.GameManager.current_turn_action", new_callable=PropertyMock
    )
    def setup(
        self,
        mock_current_turn_action_property: Mock,
        mock_previous_game_state_property: Mock,
        caplog,
        request,
    ) -> Fixture:
        param: TestCheckLoseStatePlayerCantMove.Parameters = request.param

        if not param.previous_game_state_exists:
            mock_previous_game_state_property.return_value = None

        game_manager = GameManager(player_order=param.initial_player_order)

        mock_current_turn_action_property.return_value = param.current_turn_action

        if param.previous_game_state_exists:
            type(  # type: ignore
                game_manager.previous_game_state
            ).active_player = param.initial_player_order[0]
            game_manager.previous_game_state.board.player_in_lose_state_before_move.return_value = (  # type: ignore # noqa: E501
                param.player_in_lose_state_before_move
            )

        game_manager._check_lose_state_player_cant_move()

        return self.Fixture(
            expected_player_order=param.final_player_order,
            test_player_order=game_manager.player_order,
            player_in_lose_state_before_move=param.player_in_lose_state_before_move,
            captured_log=caplog.text,
            expect_log_message=param.expect_log_message,
        )

    def test_display_message_if_in_lose_state(self, setup: Fixture):
        if setup.expect_log_message:
            assert "lost! No valid moves." in setup.captured_log

    def test_expected_player_order(self, setup: Fixture):
        assert setup.test_player_order == setup.expected_player_order


class TestCheckWinStateOnePlayerLeft:
    @dataclass
    class Parameters:
        description: str
        player_order: deque[Color]
        expected_in_win_state: bool
        expect_log_message: bool

    @dataclass
    class Fixture:
        expected_in_win_state: bool
        actual_in_win_state: bool
        captured_log: str
        expect_log_message: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="One player in player order",
                player_order=deque([Color.BLUE]),
                expected_in_win_state=True,
                expect_log_message=True,
            ),
            Parameters(
                description="More than one player in player order",
                player_order=deque([Color.BLUE, Color.WHITE]),
                expected_in_win_state=False,
                expect_log_message=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    def setup(
        self,
        caplog,
        request,
    ) -> Fixture:
        param: TestCheckWinStateOnePlayerLeft.Parameters = request.param

        game_manager = GameManager(player_order=param.player_order)
        actual_in_win_state = game_manager._check_win_state_one_player_left()

        return self.Fixture(
            expected_in_win_state=param.expected_in_win_state,
            actual_in_win_state=actual_in_win_state,
            captured_log=caplog.text,
            expect_log_message=param.expect_log_message,
        )

    def test_display_message_if_in_lose_state(self, setup: Fixture):
        if setup.expect_log_message:
            assert "won!" in setup.captured_log

    def test_expected_in_win_state(self, setup: Fixture):
        assert setup.actual_in_win_state == setup.expected_in_win_state


class TestCheckWinStateBoardWinState:
    @dataclass
    class Parameters:
        description: str
        previous_game_state_exists: bool
        player_in_win_state: bool
        expect_log_message: bool

    @dataclass
    class Fixture:
        expected_in_win_state: bool
        actual_in_win_state: bool
        captured_log: str
        expect_log_message: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="No previous game states",
                previous_game_state_exists=False,
                player_in_win_state=False,
                expect_log_message=False,
            ),
            Parameters(
                description="Player not in win state",
                previous_game_state_exists=True,
                player_in_win_state=False,
                expect_log_message=False,
            ),
            Parameters(
                description="Player in win state, log info message",
                previous_game_state_exists=True,
                player_in_win_state=True,
                expect_log_message=True,
            ),
            Parameters(
                description="Player in win state, don't log info message",
                previous_game_state_exists=True,
                player_in_win_state=True,
                expect_log_message=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch(
        "santorini_bot.game.GameManager.previous_game_state", new_callable=PropertyMock
    )
    def setup(
        self,
        mock_previous_game_state_property: Mock,
        caplog,
        request,
    ) -> Fixture:
        param: TestCheckWinStateBoardWinState.Parameters = request.param

        if not param.previous_game_state_exists:
            mock_previous_game_state_property.return_value = None

        game_manager = GameManager()

        if param.previous_game_state_exists:
            game_manager.previous_game_state.board.player_in_win_state.return_value = (  # type: ignore # noqa: E501
                param.player_in_win_state
            )

        actual_in_win_state = game_manager._check_win_state_board_win_state(
            logger_info_message=param.expect_log_message
        )

        return self.Fixture(
            expected_in_win_state=param.player_in_win_state,
            actual_in_win_state=actual_in_win_state,
            captured_log=caplog.text,
            expect_log_message=param.expect_log_message,
        )

    def test_display_message_if_in_lose_state(self, setup: Fixture):
        if setup.expect_log_message:
            assert "won!" in setup.captured_log

    def test_expected_in_win_state(self, setup: Fixture):
        assert setup.actual_in_win_state == setup.expected_in_win_state
