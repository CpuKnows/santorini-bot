# pylint: disable=C,W,R
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import Mock, create_autospec, patch

import pytest

from santorini_bot.board import (
    Board,
    Color,
    Worker,
    BuildTurn,
    MoveTurn,
    PlaceWorkerTurn,
    IllegalMoveError,
    IllegalBoardStateError,
)


class TestMove:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=2)

    @dataclass
    class Parameters:
        description: str
        board: Board
        workers: list[Worker]
        moved_worker_color: Color
        start_x: int
        start_y: int
        start_height: int
        end_x: int
        end_y: int
        end_height: int
        is_valid_move: bool
        expect_illegal_move_error: Optional[str]
        alter_blocks: list[tuple[int, int, int]] = field(default_factory=list)

    @dataclass
    class Fixture:
        board: Board
        workers: list[Worker]
        moved_worker_color: Color
        start_x: int
        start_y: int
        start_height: int
        end_x: int
        end_y: int
        end_height: int
        mock_is_valid_move: Mock
        expect_illegal_move_error: Optional[str]
        threw_illegal_move_error: bool
        captured_log: str

    @pytest.fixture(
        params=[
            Parameters(
                description="Simple move",
                board=_default_board,
                workers=[Worker(x=0, y=0, height=0, color=Color.BLUE)],
                moved_worker_color=Color.BLUE,
                start_x=0,
                start_y=0,
                start_height=0,
                end_x=1,
                end_y=1,
                end_height=0,
                is_valid_move=True,
                expect_illegal_move_error=None,
            ),
            Parameters(
                description="Invalid move",
                board=_default_board,
                workers=[Worker(x=1, y=1, height=0, color=Color.BLUE)],
                moved_worker_color=Color.BLUE,
                start_x=1,
                start_y=1,
                start_height=0,
                end_x=0,
                end_y=0,
                end_height=0,
                is_valid_move=False,
                expect_illegal_move_error="Invalid move",
            ),
            Parameters(
                description="Move with other friendly worker present",
                board=_default_board,
                workers=[
                    Worker(x=1, y=1, height=0, color=Color.BLUE),
                    Worker(x=0, y=1, height=0, color=Color.BLUE),
                ],
                moved_worker_color=Color.BLUE,
                start_x=1,
                start_y=1,
                start_height=0,
                end_x=0,
                end_y=0,
                end_height=0,
                is_valid_move=True,
                expect_illegal_move_error=None,
            ),
            Parameters(
                description="Move with other opponent worker present",
                board=_default_board,
                workers=[
                    Worker(x=1, y=1, height=0, color=Color.BLUE),
                    Worker(x=0, y=1, height=0, color=Color.WHITE),
                ],
                moved_worker_color=Color.BLUE,
                start_x=1,
                start_y=1,
                start_height=0,
                end_x=0,
                end_y=0,
                end_height=0,
                is_valid_move=True,
                expect_illegal_move_error=None,
            ),
            Parameters(
                description="Move changes height",
                board=_default_board,
                workers=[Worker(x=1, y=1, height=0, color=Color.BLUE)],
                moved_worker_color=Color.BLUE,
                start_x=1,
                start_y=1,
                start_height=0,
                end_x=0,
                end_y=0,
                end_height=1,
                is_valid_move=True,
                expect_illegal_move_error=None,
                alter_blocks=[(0, 0, 1)],
            ),
            Parameters(
                description="Move to highest block (win state)",
                board=_default_board,
                workers=[Worker(x=1, y=1, height=2, color=Color.BLUE)],
                moved_worker_color=Color.BLUE,
                start_x=1,
                start_y=1,
                start_height=2,
                end_x=0,
                end_y=0,
                end_height=3,
                is_valid_move=True,
                expect_illegal_move_error=None,
                alter_blocks=[(1, 1, 2), (0, 0, 3)],
            ),
            Parameters(
                description="Move from location without worker",
                board=_default_board,
                workers=[Worker(x=1, y=1, height=0, color=Color.BLUE)],
                moved_worker_color=Color.BLUE,
                start_x=0,
                start_y=0,
                start_height=0,
                end_x=0,
                end_y=1,
                end_height=0,
                is_valid_move=False,
                expect_illegal_move_error="No worker at",
            ),
            Parameters(
                description="Move opponent's worker",
                board=_default_board,
                workers=[Worker(x=1, y=1, height=0, color=Color.BLUE)],
                moved_worker_color=Color.WHITE,
                start_x=1,
                start_y=1,
                start_height=0,
                end_x=0,
                end_y=1,
                end_height=0,
                is_valid_move=False,
                expect_illegal_move_error="Invalid move",
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board.is_valid_move", autospec=True)
    def setup(self, mock_is_valid_move: Mock, caplog, request) -> Fixture:
        param: TestMove.Parameters = request.param
        board = deepcopy(param.board)

        # Add other workers to board
        for worker in param.workers:
            board.place_worker(x=worker.x, y=worker.y, color=worker.color)

        for x, y, height in param.alter_blocks:
            board.board_blocks[y][x] = height

        mock_is_valid_move.return_value = param.is_valid_move

        try:
            board.move(
                color=param.moved_worker_color,
                start_x=param.start_x,
                start_y=param.start_y,
                end_x=param.end_x,
                end_y=param.end_y,
            )
        except IllegalMoveError:
            threw_illegal_move_error = True
        else:
            threw_illegal_move_error = False

        return self.Fixture(
            board=board,
            workers=param.workers,
            moved_worker_color=param.moved_worker_color,
            start_x=param.start_x,
            start_y=param.start_y,
            start_height=param.start_height,
            end_x=param.end_x,
            end_y=param.end_y,
            end_height=param.end_height,
            mock_is_valid_move=mock_is_valid_move,
            captured_log=caplog.text,
            expect_illegal_move_error=param.expect_illegal_move_error,
            threw_illegal_move_error=threw_illegal_move_error,
        )

    def test_moves_correct_worker(self, setup: Fixture):
        if (
            setup.expect_illegal_move_error is None
            and setup.mock_is_valid_move.return_value
        ):
            worker_start = Worker(
                x=setup.start_x,
                y=setup.start_y,
                height=setup.start_height,
                color=setup.moved_worker_color,
            )
            assert worker_start not in setup.board.workers

    def test_worker_moves_to_correct_coordinates(self, setup: Fixture):
        if (
            setup.expect_illegal_move_error is None
            and setup.mock_is_valid_move.return_value
        ):
            worker_end = Worker(
                x=setup.end_x,
                y=setup.end_y,
                height=setup.end_height,
                color=setup.moved_worker_color,
            )
            assert worker_end in setup.board.workers

    def test_calls_is_valid_move(self, setup: Fixture):
        if setup.expect_illegal_move_error is None:
            setup.mock_is_valid_move.assert_called_once()

    def test_prints_no_worker_at_start(self, setup: Fixture):
        if setup.expect_illegal_move_error is not None:
            assert (
                setup.expect_illegal_move_error in setup.captured_log
                and setup.threw_illegal_move_error
            )

    def test_prints_invalid_move(self, setup: Fixture):
        if (
            setup.expect_illegal_move_error is not None
            and not setup.mock_is_valid_move.return_value
        ):
            assert (
                setup.expect_illegal_move_error in setup.captured_log
                and setup.threw_illegal_move_error
            )


class TestGetValidMoves:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=2)

    @dataclass
    class Parameters:
        description: str
        board: Board
        worker: Worker
        expected_num_valid_moves: int
        other_workers: list[Worker] = field(default_factory=list)
        alter_blocks: list[tuple[int, int, int]] = field(default_factory=list)

    @dataclass
    class Fixture:
        board: Board
        worker: Worker
        other_workers: list[Worker]
        move_turns: list[MoveTurn]
        expected_num_valid_moves: int

    @pytest.fixture(
        params=[
            Parameters(
                description="Worker in top left corner",
                board=_default_board,
                worker=Worker(x=0, y=0, height=0, color=Color.BLUE),
                expected_num_valid_moves=3,
            ),
            Parameters(
                description="Worker in bottom right corner",
                board=_default_board,
                worker=Worker(x=2, y=2, height=0, color=Color.BLUE),
                expected_num_valid_moves=3,
            ),
            Parameters(
                description="Worker in top middle",
                board=_default_board,
                worker=Worker(x=1, y=0, height=0, color=Color.BLUE),
                expected_num_valid_moves=5,
            ),
            Parameters(
                description="Worker in right middle",
                board=_default_board,
                worker=Worker(x=2, y=1, height=0, color=Color.BLUE),
                expected_num_valid_moves=5,
            ),
            Parameters(
                description="Worker in middle",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                expected_num_valid_moves=8,
            ),
            Parameters(
                description="Friendly other worker",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                other_workers=[Worker(x=2, y=1, height=0, color=Color.BLUE)],
                expected_num_valid_moves=7,
            ),
            Parameters(
                description="Opponent other worker",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                other_workers=[Worker(x=2, y=1, height=0, color=Color.WHITE)],
                expected_num_valid_moves=7,
            ),
            Parameters(
                description="Worker can move up 1 height from 0",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                alter_blocks=[
                    (0, 0, 1),
                    (0, 1, 2),
                    (0, 2, 2),
                    (1, 0, 2),
                    (1, 1, 2),
                    (1, 2, 2),
                    (2, 0, 2),
                    (2, 1, 2),
                    (2, 2, 2),
                ],
                expected_num_valid_moves=1,
            ),
            Parameters(
                description="Worker can move up 1 height from non-0",
                board=_default_board,
                worker=Worker(x=1, y=1, height=1, color=Color.BLUE),
                alter_blocks=[
                    (0, 0, 2),
                    (0, 1, 3),
                    (0, 2, 3),
                    (1, 0, 3),
                    (1, 1, 3),
                    (1, 2, 3),
                    (2, 0, 3),
                    (2, 1, 3),
                    (2, 2, 3),
                ],
                expected_num_valid_moves=1,
            ),
            Parameters(
                description="Worker can move down",
                board=_default_board,
                worker=Worker(x=1, y=1, height=2, color=Color.BLUE),
                expected_num_valid_moves=8,
            ),
            Parameters(
                description="Worker can't move to max height",
                board=_default_board,
                worker=Worker(x=1, y=1, height=3, color=Color.BLUE),
                alter_blocks=[
                    (0, 0, 4),
                    (0, 1, 4),
                    (0, 2, 4),
                    (1, 0, 4),
                    (1, 1, 4),
                    (1, 2, 4),
                    (2, 0, 4),
                    (2, 1, 4),
                    (2, 2, 4),
                ],
                expected_num_valid_moves=0,
            ),
        ],
        ids=lambda x: x.description,
    )
    def setup(self, request) -> Fixture:
        param: TestGetValidMoves.Parameters = request.param
        board = deepcopy(param.board)

        # Add other workers to board
        for worker in param.other_workers:
            board.place_worker(x=worker.x, y=worker.y, color=worker.color)

        for x, y, height in param.alter_blocks:
            board.board_blocks[y][x] = height

        move_turns = board.get_valid_moves(worker=param.worker)

        return self.Fixture(
            board=board,
            worker=param.worker,
            other_workers=param.other_workers,
            move_turns=move_turns,
            expected_num_valid_moves=param.expected_num_valid_moves,
        )

    def test_valid_moves_returns_move_turns(self, setup: Fixture):
        assert all(list(type(turn) is MoveTurn for turn in setup.move_turns))

    def test_valid_moves_on_board(self, setup: Fixture):
        valid_move_turns: list[bool] = []
        for turn in setup.move_turns:
            if type(turn) is MoveTurn:
                valid_move_turns.append(
                    setup.board._is_on_board(x=turn.end_x, y=turn.end_y)
                )

        assert all(valid_move_turns)

    def test_valid_moves_not_on_other_workers(self, setup: Fixture):
        valid_move_turns: list[bool] = []
        for turn in setup.move_turns:
            if type(turn) is MoveTurn:
                valid_move_turns.append(
                    not setup.board._worker_on_space(x=turn.end_x, y=turn.end_y)
                )

        assert all(valid_move_turns)

    def test_valid_moves_below_max_height(self, setup: Fixture):
        is_move_below_max_height = []
        for turn in setup.move_turns:
            if type(turn) is MoveTurn:
                is_move_below_max_height.append(
                    setup.board._block_height(x=turn.end_x, y=turn.end_y)
                    < setup.board.max_height
                )

        assert all(is_move_below_max_height)

    def test_valid_moves_returns_expected_num_valid_moves(self, setup: Fixture):
        assert len(setup.move_turns) == setup.expected_num_valid_moves


class TestGetValidBuilds:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=2)

    @dataclass
    class Parameters:
        description: str
        board: Board
        worker: Worker
        expected_num_valid_builds: int
        other_workers: list[Worker] = field(default_factory=list)
        alter_blocks: list[tuple[int, int, int]] = field(default_factory=list)

    @dataclass
    class Fixture:
        board: Board
        worker: Worker
        other_workers: list[Worker]
        build_turns: list[BuildTurn]
        expected_num_valid_builds: int

    @pytest.fixture(
        params=[
            Parameters(
                description="Worker in top left corner",
                board=_default_board,
                worker=Worker(x=0, y=0, height=0, color=Color.BLUE),
                expected_num_valid_builds=3,
            ),
            Parameters(
                description="Worker in bottom right corner",
                board=_default_board,
                worker=Worker(x=2, y=2, height=0, color=Color.BLUE),
                expected_num_valid_builds=3,
            ),
            Parameters(
                description="Worker in top middle",
                board=_default_board,
                worker=Worker(x=1, y=0, height=0, color=Color.BLUE),
                expected_num_valid_builds=5,
            ),
            Parameters(
                description="Worker in right middle",
                board=_default_board,
                worker=Worker(x=2, y=1, height=0, color=Color.BLUE),
                expected_num_valid_builds=5,
            ),
            Parameters(
                description="Worker in middle",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                expected_num_valid_builds=8,
            ),
            Parameters(
                description="Friendly other worker",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                other_workers=[Worker(x=2, y=1, height=0, color=Color.BLUE)],
                expected_num_valid_builds=7,
            ),
            Parameters(
                description="Opponent other worker",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                other_workers=[Worker(x=2, y=1, height=0, color=Color.WHITE)],
                expected_num_valid_builds=7,
            ),
            Parameters(
                description="Worker can build at multiple heights",
                board=_default_board,
                worker=Worker(x=1, y=1, height=0, color=Color.BLUE),
                alter_blocks=[
                    (0, 0, 0),
                    (0, 1, 1),
                    (0, 2, 2),
                    (1, 0, 3),
                ],
                expected_num_valid_builds=8,
            ),
            Parameters(
                description="Worker can build down",
                board=_default_board,
                worker=Worker(x=1, y=1, height=2, color=Color.BLUE),
                expected_num_valid_builds=8,
            ),
            Parameters(
                description="Worker can't build above max height",
                board=_default_board,
                worker=Worker(x=1, y=1, height=2, color=Color.BLUE),
                alter_blocks=[
                    (0, 0, 4),
                    (0, 1, 4),
                    (0, 2, 4),
                    (1, 0, 4),
                    (1, 1, 4),
                    (1, 2, 4),
                    (2, 0, 4),
                    (2, 1, 4),
                    (2, 2, 4),
                ],
                expected_num_valid_builds=0,
            ),
        ],
        ids=lambda x: x.description,
    )
    def setup(self, request) -> Fixture:
        param: TestGetValidBuilds.Parameters = request.param
        board = deepcopy(param.board)

        # Add other workers to board
        for worker in param.other_workers:
            board.place_worker(x=worker.x, y=worker.y, color=worker.color)

        for x, y, height in param.alter_blocks:
            board.board_blocks[y][x] = height

        build_turns = board.get_valid_builds(worker=param.worker)

        return self.Fixture(
            board=board,
            worker=param.worker,
            other_workers=param.other_workers,
            build_turns=build_turns,
            expected_num_valid_builds=param.expected_num_valid_builds,
        )

    def test_valid_builds_returns_build_turns(self, setup: Fixture):
        assert all(list(type(turn) is BuildTurn for turn in setup.build_turns))

    def test_valid_builds_on_board(self, setup: Fixture):
        valid_build_turns: list[bool] = []
        for turn in setup.build_turns:
            if type(turn) is BuildTurn:
                valid_build_turns.append(
                    setup.board._is_on_board(x=turn.build_x, y=turn.build_y)
                )

        assert all(valid_build_turns)

    def test_valid_builds_not_on_other_workers(self, setup: Fixture):
        valid_build_turns: list[bool] = []
        for turn in setup.build_turns:
            if type(turn) is BuildTurn:
                valid_build_turns.append(
                    not setup.board._worker_on_space(x=turn.build_x, y=turn.build_y)
                )

        assert all(valid_build_turns)

    def test_valid_builds_below_max_height(self, setup: Fixture):
        is_build_below_max_height = []
        for turn in setup.build_turns:
            if type(turn) is BuildTurn:
                is_build_below_max_height.append(
                    setup.board._block_height(x=turn.build_x, y=turn.build_y)
                    < setup.board.max_height
                )

        assert all(is_build_below_max_height)

    def test_valid_builds_returns_expected_num_valid_builds(self, setup: Fixture):
        assert len(setup.build_turns) == setup.expected_num_valid_builds


class TestGetValidPlacements:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=2)

    @dataclass
    class Parameters:
        description: str
        board: Board
        color: Color
        expected_num_valid_placements: int
        other_workers: list[Worker] = field(default_factory=list)

    @dataclass
    class Fixture:
        board: Board
        other_workers: list[Worker]
        placement_turns: list[PlaceWorkerTurn]
        expected_num_valid_placements: int

    @pytest.fixture(
        params=[
            Parameters(
                description="Worker in top left corner",
                board=_default_board,
                color=Color.BLUE,
                expected_num_valid_placements=9,
            ),
            Parameters(
                description="Worker in middle",
                board=_default_board,
                color=Color.BLUE,
                expected_num_valid_placements=9,
            ),
            Parameters(
                description="One other friendly worker",
                board=_default_board,
                color=Color.BLUE,
                other_workers=[Worker(x=2, y=1, height=0, color=Color.BLUE)],
                expected_num_valid_placements=8,
            ),
            Parameters(
                description="One other opponent worker",
                board=_default_board,
                color=Color.BLUE,
                other_workers=[Worker(x=2, y=1, height=0, color=Color.WHITE)],
                expected_num_valid_placements=8,
            ),
            Parameters(
                description="Max friendly workers already present",
                board=_default_board,
                color=Color.BLUE,
                other_workers=[
                    Worker(x=0, y=0, height=0, color=Color.WHITE),
                    Worker(x=2, y=1, height=0, color=Color.BLUE),
                    Worker(x=2, y=2, height=0, color=Color.BLUE),
                ],
                expected_num_valid_placements=0,
            ),
            Parameters(
                description="Max opponent workers already present",
                board=_default_board,
                color=Color.BLUE,
                other_workers=[
                    Worker(x=0, y=0, height=0, color=Color.WHITE),
                    Worker(x=2, y=1, height=0, color=Color.WHITE),
                    Worker(x=2, y=2, height=0, color=Color.BLUE),
                ],
                expected_num_valid_placements=6,
            ),
        ],
        ids=lambda x: x.description,
    )
    def setup(self, request) -> Fixture:
        param: TestGetValidPlacements.Parameters = request.param
        board = deepcopy(param.board)

        # Add other workers to board
        for worker in param.other_workers:
            board.place_worker(x=worker.x, y=worker.y, color=worker.color)

        placement_turns = board.get_valid_placements(color=param.color)

        return self.Fixture(
            board=board,
            other_workers=param.other_workers,
            placement_turns=placement_turns,
            expected_num_valid_placements=param.expected_num_valid_placements,
        )

    def test_valid_placements_returns_placement_turns(self, setup: Fixture):
        assert all(
            list(type(turn) is PlaceWorkerTurn for turn in setup.placement_turns)
        )

    def test_valid_placements_on_board(self, setup: Fixture):
        valid_placement_turns: list[bool] = []
        for turn in setup.placement_turns:
            if type(turn) is PlaceWorkerTurn:
                valid_placement_turns.append(
                    setup.board._is_on_board(x=turn.x, y=turn.y)
                )

        assert all(valid_placement_turns)

    def test_valid_placements_not_on_other_workers(self, setup: Fixture):
        valid_placement_turns: list[bool] = []
        for turn in setup.placement_turns:
            if type(turn) is PlaceWorkerTurn:
                valid_placement_turns.append(
                    not setup.board._worker_on_space(x=turn.x, y=turn.y)
                )

        assert all(valid_placement_turns)

    def test_valid_placements_returns_expected_num_valid_placements(
        self, setup: Fixture
    ):
        assert len(setup.placement_turns) == setup.expected_num_valid_placements


class TestPlayerCanMove:

    _mock_move_turn = create_autospec(MoveTurn)

    @dataclass
    class Parameters:
        description: str
        valid_moves: list[list[MoveTurn]]
        expected_player_can_move: bool

    @dataclass
    class Fixture:
        expected_player_can_move: bool
        test_player_can_move: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="No workers",
                valid_moves=[],
                expected_player_can_move=False,
            ),
            Parameters(
                description="Second worker has valid moves",
                valid_moves=[[], [_mock_move_turn]],
                expected_player_can_move=True,
            ),
            Parameters(
                description="No worker has valid moves",
                valid_moves=[[], []],
                expected_player_can_move=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board.get_workers_with_color", autospec=True)
    @patch("santorini_bot.board.Board.get_valid_moves", autospec=True)
    def setup(
        self, mock_get_valid_moves: Mock, mock_get_workers_with_color: Mock, request
    ) -> Fixture:
        param: TestPlayerCanMove.Parameters = request.param

        mock_worker = create_autospec(Worker)
        mock_get_workers_with_color.return_value = [mock_worker] * len(
            param.valid_moves
        )
        mock_get_valid_moves.side_effect = param.valid_moves

        board = Board(length=3, width=3, max_height=4, max_workers_per_player=1)
        test_has_valid_moves = board.player_can_move(color=create_autospec(Color))

        return self.Fixture(
            expected_player_can_move=param.expected_player_can_move,
            test_player_can_move=test_has_valid_moves,
        )

    def test_expected_player_can_move(self, setup: Fixture):
        assert setup.test_player_can_move == setup.expected_player_can_move


class TestPlayerCanBuild:

    _mock_move_turn = create_autospec(BuildTurn)

    @dataclass
    class Parameters:
        description: str
        valid_builds: list[list[BuildTurn]]
        expected_player_can_build: bool

    @dataclass
    class Fixture:
        expected_player_can_build: bool
        test_player_can_build: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="No workers",
                valid_builds=[],
                expected_player_can_build=False,
            ),
            Parameters(
                description="Second worker has valid builds",
                valid_builds=[[], [_mock_move_turn]],
                expected_player_can_build=True,
            ),
            Parameters(
                description="No worker has valid builds",
                valid_builds=[[], []],
                expected_player_can_build=False,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board.get_workers_with_color", autospec=True)
    @patch("santorini_bot.board.Board.get_valid_builds", autospec=True)
    def setup(
        self, mock_get_valid_builds: Mock, mock_get_workers_with_color: Mock, request
    ) -> Fixture:
        param: TestPlayerCanBuild.Parameters = request.param

        mock_worker = create_autospec(Worker)
        mock_get_workers_with_color.return_value = [mock_worker] * len(
            param.valid_builds
        )
        mock_get_valid_builds.side_effect = param.valid_builds

        board = Board(length=3, width=3, max_height=4, max_workers_per_player=1)
        test_has_valid_build = board.player_can_build(color=create_autospec(Color))

        return self.Fixture(
            expected_player_can_build=param.expected_player_can_build,
            test_player_can_build=test_has_valid_build,
        )

    def test_expected_player_can_build(self, setup: Fixture):
        assert setup.test_player_can_build == setup.expected_player_can_build


class TestPlayerInWinState:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=1)

    @dataclass
    class Parameters:
        description: str
        board: Board
        player_color: Color
        expect_is_win_state: bool
        expect_illegal_board_state_error: bool
        add_workers: list[Worker] = field(default_factory=list)

    @dataclass
    class Fixture:
        board: Board
        expected_is_win_state: bool
        test_is_win_state: bool
        expect_illegal_board_state_error: bool
        threw_illegal_board_state_error: bool
        captured_log: str

    @pytest.fixture(
        params=[
            Parameters(
                description="No workers",
                board=_default_board,
                player_color=Color.BLUE,
                expect_is_win_state=False,
                expect_illegal_board_state_error=False,
            ),
            Parameters(
                description="Worker below max height",
                board=_default_board,
                player_color=Color.BLUE,
                expect_is_win_state=False,
                expect_illegal_board_state_error=False,
                add_workers=[
                    Worker(x=0, y=0, height=1, color=Color.BLUE),
                ],
            ),
            Parameters(
                description="Worker at max height",
                board=_default_board,
                player_color=Color.BLUE,
                expect_is_win_state=True,
                expect_illegal_board_state_error=False,
                add_workers=[
                    Worker(x=0, y=0, height=3, color=Color.BLUE),
                ],
            ),
            Parameters(
                description="Multiple worker at max height",
                board=_default_board,
                player_color=Color.BLUE,
                expect_is_win_state=False,
                expect_illegal_board_state_error=True,
                add_workers=[
                    Worker(x=0, y=0, height=3, color=Color.BLUE),
                    Worker(x=0, y=1, height=3, color=Color.BLUE),
                ],
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board.get_workers_with_color")
    def setup(self, mock_get_workers_with_color: Mock, caplog, request) -> Fixture:
        param: TestPlayerInWinState.Parameters = request.param

        mock_get_workers_with_color.return_value = param.add_workers

        board = deepcopy(param.board)
        try:
            test_is_win_state = board.player_in_win_state(color=param.player_color)
        except IllegalBoardStateError:
            test_is_win_state = False
            threw_illegal_board_state_error = True
        else:
            threw_illegal_board_state_error = False

        return self.Fixture(
            board=board,
            expected_is_win_state=param.expect_is_win_state,
            test_is_win_state=test_is_win_state,
            expect_illegal_board_state_error=param.expect_illegal_board_state_error,
            threw_illegal_board_state_error=threw_illegal_board_state_error,
            captured_log=caplog.text,
        )

    def test_win_state(self, setup: Fixture):
        assert setup.test_is_win_state == setup.expected_is_win_state

    def test_prints_multiple_workers_in_win_state(self, setup: Fixture):
        if setup.expect_illegal_board_state_error:
            assert (
                "Multiple workers are in a winning state" in setup.captured_log
                and setup.threw_illegal_board_state_error
            )


class TestPlayerInlossStateAfterMove:

    _default_board = Board(length=3, width=3, max_height=4, max_workers_per_player=1)

    @dataclass
    class Parameters:
        description: str
        board: Board
        worker_x: int
        worker_y: int
        worker: Worker
        valid_builds: list[BuildTurn]
        expect_is_loss_state: bool

    @dataclass
    class Fixture:
        board: Board
        expected_is_loss_state: bool
        test_is_loss_state: bool

    @pytest.fixture(
        params=[
            Parameters(
                description="Worker has valid build",
                board=_default_board,
                worker_x=0,
                worker_y=0,
                worker=Worker(x=0, y=0, height=0, color=Color.BLUE),
                valid_builds=[
                    BuildTurn(
                        color=Color.BLUE, worker_x=0, worker_y=0, build_x=1, build_y=1
                    )
                ],
                expect_is_loss_state=False,
            ),
            Parameters(
                description="Worker has no valid build",
                board=_default_board,
                worker_x=0,
                worker_y=0,
                worker=Worker(x=0, y=0, height=0, color=Color.BLUE),
                valid_builds=[],
                expect_is_loss_state=True,
            ),
        ],
        ids=lambda x: x.description,
    )
    @patch("santorini_bot.board.Board._get_worker_at")
    @patch("santorini_bot.board.Board.get_valid_builds")
    def setup(
        self, mock_get_valid_builds: Mock, mock_get_worker_at: Mock, caplog, request
    ) -> Fixture:
        param: TestPlayerInlossStateAfterMove.Parameters = request.param

        mock_get_valid_builds.return_value = param.valid_builds
        mock_get_worker_at.return_value = param.worker

        board = deepcopy(param.board)
        test_is_loss_state = board.player_in_loss_state_after_move(
            worker_x=param.worker_x, worker_y=param.worker_y
        )

        return self.Fixture(
            board=board,
            expected_is_loss_state=param.expect_is_loss_state,
            test_is_loss_state=test_is_loss_state,
        )

    def test_loss_state(self, setup: Fixture):
        assert setup.test_is_loss_state == setup.expected_is_loss_state
