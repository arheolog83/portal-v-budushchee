from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="Портал в будущее",
    description="Инструменты для учителей 5–11 классов",
    version="0.1.0",
)

INDEX_FILE = Path(__file__).with_name("index.html")
DAY_NAMES = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
]


class SubjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    lessons: int = Field(ge=1, le=60)
    difficulty: int = Field(default=3, ge=1, le=5)


class ScheduleInput(BaseModel):
    days: Literal[5, 6]
    max_lessons_per_day: int = Field(ge=1, le=10)
    subjects: list[SubjectInput] = Field(min_length=1, max_length=30)


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(INDEX_FILE)


def _assignment_score(days: list[list[dict]], total_load: int) -> int:
    day_count = len(days)
    duplicate_penalty = 0
    balance_penalty = 0

    for lessons in days:
        names: dict[str, int] = {}
        day_load = 0
        for lesson in lessons:
            names[lesson["name"]] = names.get(lesson["name"], 0) + 1
            day_load += lesson["difficulty"]
        duplicate_penalty += sum((count - 1) ** 2 for count in names.values() if count > 1)
        balance_penalty += (day_load * day_count - total_load) ** 2

    return duplicate_penalty * 10_000_000 + balance_penalty


def _improve_day_assignment(days: list[list[dict]], total_load: int) -> None:
    """Deterministically improve load balance and same-day subject distribution."""
    current_score = _assignment_score(days, total_load)

    for _ in range(100):
        best_score = current_score
        best_swap: tuple[int, int, int, int] | None = None

        for first_day in range(len(days)):
            for second_day in range(first_day + 1, len(days)):
                for first_index, first_lesson in enumerate(days[first_day]):
                    for second_index, second_lesson in enumerate(days[second_day]):
                        if first_lesson["name"] == second_lesson["name"]:
                            continue
                        days[first_day][first_index], days[second_day][second_index] = (
                            second_lesson,
                            first_lesson,
                        )
                        candidate_score = _assignment_score(days, total_load)
                        days[first_day][first_index], days[second_day][second_index] = (
                            first_lesson,
                            second_lesson,
                        )
                        if candidate_score < best_score:
                            best_score = candidate_score
                            best_swap = (first_day, first_index, second_day, second_index)

        if best_swap is None:
            return

        first_day, first_index, second_day, second_index = best_swap
        days[first_day][first_index], days[second_day][second_index] = (
            days[second_day][second_index],
            days[first_day][first_index],
        )
        current_score = best_score


def _position_penalty(lesson: dict, position: int, lesson_count: int) -> int:
    if lesson["difficulty"] < 4:
        return 0
    edge_penalty = 80 * (lesson["difficulty"] - 3) if position in (0, lesson_count - 1) else 0
    distance_from_middle = abs(2 * position - (lesson_count - 1))
    return edge_penalty + distance_from_middle * lesson["difficulty"]


def _adjacency_penalty(previous: dict, current: dict) -> int:
    penalty = 100 if previous["name"] == current["name"] else 0
    if previous["difficulty"] >= 4 and current["difficulty"] >= 4:
        penalty += 60
    return penalty


def _order_day(lessons: list[dict]) -> list[dict]:
    """Find the lowest-penalty lesson order with deterministic dynamic programming."""
    lesson_count = len(lessons)
    if lesson_count < 2:
        return lessons

    states: dict[tuple[int, int], tuple[int, tuple[int, ...]]] = {}
    for index, lesson in enumerate(lessons):
        states[(1 << index, index)] = (
            _position_penalty(lesson, 0, lesson_count),
            (index,),
        )

    full_mask = (1 << lesson_count) - 1
    for mask_size in range(1, lesson_count):
        next_states = dict(states)
        for (mask, last), (cost, path) in states.items():
            if mask.bit_count() != mask_size:
                continue
            position = mask_size
            for candidate in range(lesson_count):
                if mask & (1 << candidate):
                    continue
                new_mask = mask | (1 << candidate)
                new_cost = (
                    cost
                    + _position_penalty(lessons[candidate], position, lesson_count)
                    + _adjacency_penalty(lessons[last], lessons[candidate])
                )
                new_path = path + (candidate,)
                state_key = (new_mask, candidate)
                existing = next_states.get(state_key)
                if existing is None or (new_cost, new_path) < existing:
                    next_states[state_key] = (new_cost, new_path)
        states = next_states

    _, best_path = min(
        states[(full_mask, last)]
        for last in range(lesson_count)
        if (full_mask, last) in states
    )
    return [lessons[index] for index in best_path]


def build_schedule(data: ScheduleInput) -> list[list[dict]]:
    subjects: list[dict] = []
    seen_names: set[str] = set()
    for subject in data.subjects:
        name = " ".join(subject.name.split())
        normalized_name = name.casefold()
        if not name:
            raise HTTPException(status_code=400, detail="Укажите название каждого предмета.")
        if normalized_name in seen_names:
            raise HTTPException(
                status_code=400,
                detail=f"Предмет «{name}» указан несколько раз. Объедините его часы в одной строке.",
            )
        seen_names.add(normalized_name)
        subjects.append(
            {"name": name, "lessons": subject.lessons, "difficulty": subject.difficulty}
        )

    total_lessons = sum(subject["lessons"] for subject in subjects)
    capacity = data.days * data.max_lessons_per_day
    if total_lessons > capacity:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Невозможно разместить {total_lessons} уроков: при выбранных настройках "
                f"доступно только {capacity} мест. Увеличьте число дней или максимум уроков в день."
            ),
        )

    base_lessons, extra_days = divmod(total_lessons, data.days)
    day_capacities = [base_lessons + (1 if day < extra_days else 0) for day in range(data.days)]
    days: list[list[dict]] = [[] for _ in range(data.days)]
    day_loads = [0] * data.days
    total_load = sum(subject["lessons"] * subject["difficulty"] for subject in subjects)

    for subject in sorted(
        subjects,
        key=lambda item: (-item["difficulty"], -item["lessons"], item["name"].casefold()),
    ):
        for _ in range(subject["lessons"]):
            available_days = [
                day for day in range(data.days) if len(days[day]) < day_capacities[day]
            ]
            chosen_day = min(
                available_days,
                key=lambda day: (
                    sum(lesson["name"] == subject["name"] for lesson in days[day]),
                    abs((day_loads[day] + subject["difficulty"]) * data.days - total_load),
                    len(days[day]) / day_capacities[day] if day_capacities[day] else 0,
                    day,
                ),
            )
            lesson = {"name": subject["name"], "difficulty": subject["difficulty"]}
            days[chosen_day].append(lesson)
            day_loads[chosen_day] += subject["difficulty"]

    _improve_day_assignment(days, total_load)
    return [_order_day(lessons) for lessons in days]


@app.post("/api/schedule")
async def create_schedule(data: ScheduleInput) -> dict:
    schedule = build_schedule(data)
    return {
        "days": [
            {
                "name": DAY_NAMES[index],
                "lessons": [lesson["name"] for lesson in lessons],
                "load": sum(lesson["difficulty"] for lesson in lessons),
            }
            for index, lessons in enumerate(schedule)
        ],
        "principles": (
            "Алгоритм сохраняет заданное число часов, распределяет уроки и условную "
            "когнитивную нагрузку между днями, избегает повторов предмета и соседства "
            "сложных занятий, а сложные уроки по возможности ставит не первыми и не последними."
        ),
    }
