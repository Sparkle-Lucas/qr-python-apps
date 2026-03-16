import asyncio
import random
import time
from js import document, window, localStorage
from pyscript.ffi import create_proxy

DIFFICULTIES = {
    "easy": {"cells": 18, "base_speed": 5, "max_speed": 10},
    "normal": {"cells": 16, "base_speed": 6, "max_speed": 13},
    "hard": {"cells": 14, "base_speed": 8, "max_speed": 16},
}

FOOD_TYPES = {
    "normal": {"points": 1, "color": "#ff7788", "leaf": "#6de7b7", "ttl": None},
    "bonus": {"points": 3, "color": "#ffd166", "leaf": "#fff1b0", "ttl": None},
    "timed": {"points": 1, "color": "#78b7ff", "leaf": "#d8ebff", "ttl": 3.0},
}
FOOD_POOL = ["normal"] * 7 + ["bonus"] * 2 + ["timed"]

canvas = document.getElementById("board")
ctx = canvas.getContext("2d")
score_el = document.getElementById("score")
best_el = document.getElementById("best")
speed_el = document.getElementById("speed")
status_el = document.getElementById("status")
hint_el = document.getElementById("hint")
difficulty_el = document.getElementById("difficulty")
mode_el = document.getElementById("wrap-mode")

best_score = 0
try:
    stored = localStorage.getItem("snake_best")
    if stored:
        best_score = int(stored)
except Exception:
    best_score = 0

best_el.textContent = str(best_score)

cell_count = DIFFICULTIES["normal"]["cells"]
base_speed = DIFFICULTIES["normal"]["base_speed"]
max_speed = DIFFICULTIES["normal"]["max_speed"]

snake = []
food = None
current_dir = (1, 0)
next_dir = (1, 0)
running = False
paused = False
game_task = None
score = 0
speed = base_speed
start_touch = None
proxies = []


def bind(element, event_name, fn):
    proxy = create_proxy(fn)
    proxies.append(proxy)
    element.addEventListener(event_name, proxy)


class Food:
    def __init__(self, pos, kind, created_at):
        self.pos = pos
        self.kind = kind
        self.created_at = created_at



def set_status(text: str):
    status_el.textContent = text



def set_hint(text: str):
    hint_el.textContent = text



def apply_difficulty():
    global cell_count, base_speed, max_speed, speed
    config = DIFFICULTIES[str(difficulty_el.value)]
    cell_count = config["cells"]
    base_speed = config["base_speed"]
    max_speed = config["max_speed"]
    speed = base_speed



def sync_hud():
    score_el.textContent = str(score)
    best_el.textContent = str(best_score)
    speed_el.textContent = str(speed)



def reset_state():
    global snake, food, current_dir, next_dir, score, speed, paused
    apply_difficulty()
    mid = cell_count // 2
    snake = [(mid + 1, mid), (mid, mid), (mid - 1, mid)]
    current_dir = (1, 0)
    next_dir = (1, 0)
    score = 0
    speed = base_speed
    paused = False
    spawn_food()
    sync_hud()
    draw()



def random_food_type():
    return random.choice(FOOD_POOL)



def spawn_food(kind=None):
    global food
    occupied = set(snake)
    choices = [(x, y) for x in range(cell_count) for y in range(cell_count) if (x, y) not in occupied]
    if not choices:
        return
    food = Food(random.choice(choices), kind or random_food_type(), time.monotonic())



def maybe_expire_timed_food():
    global food
    if not food:
        return
    ttl = FOOD_TYPES[food.kind]["ttl"]
    if ttl is None:
        return
    if time.monotonic() - food.created_at > ttl:
        spawn_food()
        set_status("Timed food expired. New food spawned.")



def update_speed():
    global speed
    speed = min(max_speed, base_speed + score // 3)



def set_direction(dx: int, dy: int):
    global next_dir
    if not running or paused:
        return
    if (dx, dy) == (-current_dir[0], -current_dir[1]):
        return
    next_dir = (dx, dy)



def draw_background():
    cell = canvas.width / cell_count
    ctx.fillStyle = "#11162e"
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    for y in range(cell_count):
        for x in range(cell_count):
            ctx.fillStyle = "#161d39" if (x + y) % 2 == 0 else "#121833"
            ctx.fillRect(x * cell, y * cell, cell, cell)



def draw_food(cell):
    if not food:
        return
    fx, fy = food.pos
    cx = fx * cell + cell / 2
    cy = fy * cell + cell / 2
    radius = cell * 0.28
    spec = FOOD_TYPES[food.kind]

    ctx.beginPath()
    ctx.fillStyle = spec["color"]
    ctx.arc(cx, cy, radius, 0, 6.28318)
    ctx.fill()

    ctx.beginPath()
    ctx.fillStyle = spec["leaf"]
    ctx.arc(cx + radius * 0.42, cy - radius * 0.7, radius * 0.36, 0, 6.28318)
    ctx.fill()

    if food.kind == "bonus":
        ctx.strokeStyle = "rgba(255,255,255,.85)"
        ctx.lineWidth = max(2, cell * 0.05)
        ctx.beginPath()
        ctx.arc(cx, cy, radius * 1.22, 0, 6.28318)
        ctx.stroke()
    elif food.kind == "timed":
        ttl = FOOD_TYPES[food.kind]["ttl"]
        remain = max(0.0, ttl - (time.monotonic() - food.created_at))
        ratio = remain / ttl if ttl else 1
        ctx.strokeStyle = "rgba(255,255,255,.9)"
        ctx.lineWidth = max(2, cell * 0.06)
        ctx.beginPath()
        ctx.arc(cx, cy, radius * 1.32, -1.57, -1.57 + 6.28318 * ratio)
        ctx.stroke()



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
    cell = canvas.width / cell_count
    draw_background()
    draw_food(cell)
    draw_snake(cell)
    if not running:
        draw_overlay("Snake", "Tap Start / Restart")
    elif paused:
        draw_overlay("Paused", "Tap Pause again to continue")



def save_best():
    try:
        localStorage.setItem("snake_best", str(best_score))
    except Exception:
        pass



def trigger_feedback(kind: str):
    try:
        if kind == "eat":
            window.snakeFx.eat()
            window.snakeFx.vibrate([18])
        elif kind == "bonus":
            window.snakeFx.eat()
            window.snakeFx.vibrate([22, 20, 22])
        elif kind == "gameover":
            window.snakeFx.gameover()
            window.snakeFx.vibrate([45, 30, 45])
    except Exception:
        pass



def end_game():
    global running, best_score
    running = False
    if score > best_score:
        best_score = score
        save_best()
    sync_hud()
    draw_background()
    draw_food(canvas.width / cell_count)
    draw_snake(canvas.width / cell_count)
    draw_overlay("Game Over", f"Score {score} • Best {best_score}")
    set_status("Game over. Tap Start / Restart to go again.")
    set_hint("Try a lower difficulty or switch to Wrap mode for more space.")
    trigger_feedback("gameover")



def advance_head(x: int, y: int, dx: int, dy: int):
    new_x = x + dx
    new_y = y + dy
    if str(mode_el.value) == "wrap":
        return new_x % cell_count, new_y % cell_count
    return new_x, new_y



def step_once():
    global snake, current_dir, next_dir, score, food
    maybe_expire_timed_food()
    current_dir = next_dir
    head_x, head_y = snake[0]
    dx, dy = current_dir
    new_head = advance_head(head_x, head_y, dx, dy)

    if (
        str(mode_el.value) == "classic"
        and (new_head[0] < 0 or new_head[0] >= cell_count or new_head[1] < 0 or new_head[1] >= cell_count)
    ):
        end_game()
        return

    if new_head in snake[:-1]:
        end_game()
        return

    snake.insert(0, new_head)
    if food and new_head == food.pos:
        gained = FOOD_TYPES[food.kind]["points"]
        kind = food.kind
        score += gained
        update_speed()
        spawn_food()
        sync_hud()
        if kind == "bonus":
            set_status("Gold food. +3 points.")
            set_hint("Nice. Big score spike.")
            trigger_feedback("bonus")
        elif kind == "timed":
            set_status("Timed food grabbed before it expired.")
            set_hint("Keep moving. Timed food disappears after 3 seconds.")
            trigger_feedback("eat")
        else:
            set_status("Normal food. +1 point.")
            set_hint("Swipe or tap arrows. Score increases speed every 3 points.")
            trigger_feedback("eat")
    else:
        snake.pop()

    draw()


async def game_loop():
    global running, game_task
    try:
        while running:
            if not paused:
                step_once()
                if not running:
                    break
            await asyncio.sleep(1 / max(1, speed))
    except asyncio.CancelledError:
        pass
    finally:
        game_task = None



def start_game(event=None):
    global running, paused, game_task
    if game_task:
        game_task.cancel()
    reset_state()
    running = True
    paused = False
    set_status("Game running. Swipe or use the arrows.")
    set_hint(f"{str(difficulty_el.value).title()} mode • {str(mode_el.value).title()} map")
    try:
        window.snakeFx.ensure()
    except Exception:
        pass
    game_task = asyncio.create_task(game_loop())



def toggle_pause(event=None):
    global paused
    if not running:
        return
    paused = not paused
    draw()
    set_status("Paused." if paused else "Back in play.")
    set_hint("Tap Pause again or resume with the arrows.")



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
        set_direction(dx, dy)



def make_dir_handler(dx, dy):
    def handler(event=None):
        set_direction(dx, dy)
    return handler



def on_touch_start(event):
    global start_touch
    touch = event.touches[0]
    start_touch = (float(touch.clientX), float(touch.clientY))



def on_touch_end(event):
    global start_touch
    if not start_touch:
        return
    touch = event.changedTouches[0]
    end_touch = (float(touch.clientX), float(touch.clientY))
    dx = end_touch[0] - start_touch[0]
    dy = end_touch[1] - start_touch[1]
    start_touch = None
    if abs(dx) < 12 and abs(dy) < 12:
        return
    if abs(dx) > abs(dy):
        set_direction(1, 0) if dx > 0 else set_direction(-1, 0)
    else:
        set_direction(0, 1) if dy > 0 else set_direction(0, -1)



def on_mode_change(event=None):
    draw()
    set_status(f"Mode set to {str(mode_el.value).title()}.")



def on_difficulty_change(event=None):
    if running:
        set_status("Difficulty will apply when you restart the round.")
    else:
        reset_state()
        set_status(f"Difficulty set to {str(difficulty_el.value).title()}.")


bind(document.getElementById("start-btn"), "click", start_game)
bind(document.getElementById("pause-btn"), "click", toggle_pause)
bind(document.getElementById("btn-up"), "click", make_dir_handler(0, -1))
bind(document.getElementById("btn-down"), "click", make_dir_handler(0, 1))
bind(document.getElementById("btn-left"), "click", make_dir_handler(-1, 0))
bind(document.getElementById("btn-right"), "click", make_dir_handler(1, 0))
bind(document, "keydown", on_keydown)
bind(canvas, "touchstart", on_touch_start)
bind(canvas, "touchend", on_touch_end)
bind(difficulty_el, "change", on_difficulty_change)
bind(mode_el, "change", on_mode_change)

reset_state()
set_status("Ready. Choose a difficulty, then tap Start.")
set_hint("Swipe or tap arrows after the round begins.")
