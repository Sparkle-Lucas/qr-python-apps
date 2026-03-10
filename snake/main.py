import asyncio
import random
from js import document, localStorage
from pyscript import ffi

CELL_COUNT = 16
BASE_SPEED = 5
MAX_SPEED = 11

canvas = document.getElementById("board")
ctx = canvas.getContext("2d")
score_el = document.getElementById("score")
best_el = document.getElementById("best")
speed_el = document.getElementById("speed")
status_el = document.getElementById("status")

best_score = 0
try:
    stored = localStorage.getItem("snake_best")
    if stored:
        best_score = int(stored)
except Exception:
    best_score = 0

best_el.textContent = str(best_score)

snake = []
food = None
current_dir = (1, 0)
next_dir = (1, 0)
running = False
paused = False
game_task = None
score = 0
speed = BASE_SPEED
start_touch = None

_CALLBACKS = []


def bind(element, event_name: str, handler):
    proxy = ffi.create_proxy(handler)
    _CALLBACKS.append(proxy)
    element.addEventListener(event_name, proxy)


def set_status(text: str):
    status_el.textContent = text


def sync_hud():
    score_el.textContent = str(score)
    best_el.textContent = str(best_score)
    speed_el.textContent = str(speed)


def reset_state():
    global snake, food, current_dir, next_dir, score, speed, paused
    snake = [(5, 8), (4, 8), (3, 8)]
    current_dir = (1, 0)
    next_dir = (1, 0)
    score = 0
    speed = BASE_SPEED
    paused = False
    spawn_food()
    sync_hud()
    draw()


def spawn_food():
    global food
    occupied = set(snake)
    choices = [(x, y) for x in range(CELL_COUNT) for y in range(CELL_COUNT) if (x, y) not in occupied]
    food = random.choice(choices)


def update_speed():
    global speed
    speed = min(MAX_SPEED, BASE_SPEED + score // 4)


def set_direction(dx: int, dy: int):
    global next_dir
    if not running or paused:
        return
    if (dx, dy) == (-current_dir[0], -current_dir[1]):
        return
    next_dir = (dx, dy)


def draw_background():
    cell = canvas.width / CELL_COUNT
    ctx.fillStyle = "#11162e"
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    for y in range(CELL_COUNT):
        for x in range(CELL_COUNT):
            ctx.fillStyle = "#161d39" if (x + y) % 2 == 0 else "#121833"
            ctx.fillRect(x * cell, y * cell, cell, cell)


def draw_food(cell):
    fx, fy = food
    cx = fx * cell + cell / 2
    cy = fy * cell + cell / 2
    radius = cell * 0.28

    ctx.beginPath()
    ctx.fillStyle = "#ff6b6b"
    ctx.arc(cx, cy, radius, 0, 6.28318)
    ctx.fill()

    ctx.beginPath()
    ctx.fillStyle = "#5bd18a"
    ctx.arc(cx + radius * 0.45, cy - radius * 0.75, radius * 0.42, 0, 6.28318)
    ctx.fill()


def draw_snake(cell):
    for i, (x, y) in enumerate(snake):
        px = x * cell
        py = y * cell
        size = cell - 4
        inset = 2
        ctx.fillStyle = "#7cf0b9" if i == 0 else "#34d399"
        ctx.fillRect(px + inset, py + inset, size, size)

        if i == 0:
            ctx.fillStyle = "#0b1b18"
            eye_offset_x = cell * 0.24
            eye_offset_y = cell * 0.28
            ctx.beginPath()
            ctx.arc(px + eye_offset_x, py + eye_offset_y, cell * 0.06, 0, 6.28318)
            ctx.arc(px + cell - eye_offset_x, py + eye_offset_y, cell * 0.06, 0, 6.28318)
            ctx.fill()


def draw_overlay(text: str, subtext: str):
    ctx.fillStyle = "rgba(6, 9, 20, 0.68)"
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = "#eef1ff"
    ctx.font = "bold 38px Inter, system-ui"
    ctx.textAlign = "center"
    ctx.fillText(text, canvas.width / 2, canvas.height / 2 - 8)
    ctx.fillStyle = "#aab3d8"
    ctx.font = "20px Inter, system-ui"
    ctx.fillText(subtext, canvas.width / 2, canvas.height / 2 + 28)


def draw():
    cell = canvas.width / CELL_COUNT
    draw_background()
    draw_food(cell)
    draw_snake(cell)
    if not running:
        draw_overlay("Snake", "Tap Start / Restart")
    elif paused:
        draw_overlay("Paused", "Tap Pause again or swipe")


def end_game():
    global running, best_score
    running = False
    if score > best_score:
        best_score = score
        try:
            localStorage.setItem("snake_best", str(best_score))
        except Exception:
            pass
    sync_hud()
    draw_background()
    draw_food(canvas.width / CELL_COUNT)
    draw_snake(canvas.width / CELL_COUNT)
    draw_overlay("Game Over", f"Score {score} • Best {best_score}")
    set_status("Game over. Tap Start / Restart to go again.")


def step_once():
    global snake, current_dir, next_dir, score
    current_dir = next_dir
    head_x, head_y = snake[0]
    dx, dy = current_dir
    new_head = (head_x + dx, head_y + dy)

    if (
        new_head[0] < 0
        or new_head[0] >= CELL_COUNT
        or new_head[1] < 0
        or new_head[1] >= CELL_COUNT
        or new_head in snake[:-1]
    ):
        end_game()
        return

    snake.insert(0, new_head)
    if new_head == food:
        score += 1
        update_speed()
        spawn_food()
        sync_hud()
        set_status("Nice. Keep going.")
    else:
        snake.pop()

    draw()


async def game_loop():
    global running
    while running:
        if not paused:
            step_once()
            if not running:
                break
        await asyncio.sleep(1 / speed)


def start_game(event=None):
    global running, paused, game_task
    if game_task:
        game_task.cancel()
    reset_state()
    running = True
    paused = False
    set_status("Game running. Swipe or use the buttons.")
    game_task = asyncio.create_task(game_loop())


def toggle_pause(event=None):
    global paused
    if not running:
        return
    paused = not paused
    draw()
    set_status("Paused." if paused else "Back in play.")


def on_keydown(event):
    key = event.key.lower()
    mapping = {
        "arrowup": (0, -1),
        "w": (0, -1),
        "arrowdown": (0, 1),
        "s": (0, 1),
        "arrowleft": (-1, 0),
        "a": (-1, 0),
        "arrowright": (1, 0),
        "d": (1, 0),
    }
    if key in mapping:
        dx, dy = mapping[key]
        if paused:
            toggle_pause()
        set_direction(dx, dy)


def on_touch_start(event):
    global start_touch
    if event.touches.length:
        touch = event.touches.item(0)
        start_touch = (touch.clientX, touch.clientY)


def on_touch_end(event):
    global start_touch
    if start_touch is None or event.changedTouches.length == 0:
        return

    touch = event.changedTouches.item(0)
    end_touch = (touch.clientX, touch.clientY)
    dx = end_touch[0] - start_touch[0]
    dy = end_touch[1] - start_touch[1]
    start_touch = None

    if abs(dx) < 18 and abs(dy) < 18:
        if paused and running:
            toggle_pause()
        return

    if paused and running:
        toggle_pause()

    if abs(dx) > abs(dy):
        set_direction(1, 0) if dx > 0 else set_direction(-1, 0)
    else:
        set_direction(0, 1) if dy > 0 else set_direction(0, -1)


bind(document.getElementById("start"), "click", start_game)
bind(document.getElementById("pause"), "click", toggle_pause)
bind(document.getElementById("up"), "click", lambda event: set_direction(0, -1))
bind(document.getElementById("down"), "click", lambda event: set_direction(0, 1))
bind(document.getElementById("left"), "click", lambda event: set_direction(-1, 0))
bind(document.getElementById("right"), "click", lambda event: set_direction(1, 0))
bind(document, "keydown", on_keydown)
bind(canvas, "touchstart", on_touch_start)
bind(canvas, "touchend", on_touch_end)

reset_state()
