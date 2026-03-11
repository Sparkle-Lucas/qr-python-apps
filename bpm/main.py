import asyncio
import random
from js import document, window
from pyscript.ffi import create_proxy

TRACKS = ["kick", "snare", "hat"]
STEPS = 16

seq_grid = document.getElementById("seq-grid")
status_el = document.getElementById("status")
bpm_el = document.getElementById("bpm")
swing_el = document.getElementById("swing")
bpm_value_el = document.getElementById("bpm-value")
swing_value_el = document.getElementById("swing-value")
preset_el = document.getElementById("preset")

audio_debug_el = document.getElementById("audio-debug")

pattern = {track: [0] * STEPS for track in TRACKS}
pad_elements = {track: [] for track in TRACKS}
running = False
loop_task = None
current_step = -1
_event_proxies = []

PRESETS = {
    "starter": {
        "kick": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    "house": {
        "kick": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    },
    "trap": {
        "kick": [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat": [1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1],
    },
    "drill": {
        "kick": [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat": [1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0],
    },
}


def bind_event(element, event_name, func):
    proxy = create_proxy(func)
    _event_proxies.append(proxy)
    element.addEventListener(event_name, proxy)


def set_status(text: str):
    status_el.textContent = text


def set_audio_debug(text: str):
    if audio_debug_el:
        audio_debug_el.textContent = text


def update_value_labels(event=None):
    bpm_value_el.textContent = bpm_el.value
    swing_value_el.textContent = f"{swing_el.value}%"


def build_grid():
    seq_grid.innerHTML = ""
    label_spacer = document.createElement("div")
    label_spacer.className = "track-label"
    label_spacer.textContent = "Track"
    seq_grid.appendChild(label_spacer)

    for i in range(STEPS):
        step_label = document.createElement("div")
        step_label.className = "step-head"
        step_label.textContent = str(i + 1)
        seq_grid.appendChild(step_label)

    for track in TRACKS:
        label = document.createElement("div")
        label.className = "track-label"
        label.textContent = track.title()
        seq_grid.appendChild(label)

        for step in range(STEPS):
            button = document.createElement("button")
            button.className = f"pad track-{track}"
            button.dataset.track = track
            button.dataset.step = str(step)
            bind_event(button, "click", make_toggle_handler(track, step))
            pad_elements[track].append(button)
            seq_grid.appendChild(button)


def make_toggle_handler(track, step):
    def handler(event):
        pattern[track][step] = 0 if pattern[track][step] else 1
        refresh_pads()
    return handler


def refresh_pads():
    for track in TRACKS:
        for step, pad in enumerate(pad_elements[track]):
            classes = ["pad", f"track-{track}"]
            if pattern[track][step]:
                classes.append("active")
            if step == current_step and running:
                classes.append("current")
            pad.className = " ".join(classes)


def load_preset(name: str):
    for track in TRACKS:
        pattern[track] = PRESETS[name][track][:]
    refresh_pads()
    set_status(f"Loaded preset: {name}.")


def clear_pattern(event=None):
    for track in TRACKS:
        pattern[track] = [0] * STEPS
    refresh_pads()
    set_status("Pattern cleared.")


def randomize_pattern(event=None):
    pattern["kick"] = [1 if i in (0, 8) else (1 if random.random() < 0.18 else 0) for i in range(STEPS)]
    pattern["snare"] = [1 if i in (4, 12) else 0 for i in range(STEPS)]
    pattern["hat"] = [1 if i % 2 == 0 else (1 if random.random() < 0.35 else 0) for i in range(STEPS)]
    refresh_pads()
    set_status("Randomized a playable beat.")


def fill_hats(event=None):
    pattern["hat"] = [1] * STEPS
    refresh_pads()
    set_status("Hi-hats filled.")


def drop_kick(event=None):
    for step in (0, 6, 8, 14):
        pattern["kick"][step] = 1
    refresh_pads()
    set_status("Extra kicks added.")


def get_bpm() -> float:
    return float(bpm_el.value)


def get_swing() -> float:
    return float(swing_el.value) / 100.0


def play_step(step: int):
    if pattern["kick"][step]:
        window.audioHelper.kick()
    if pattern["snare"][step]:
        window.audioHelper.snare()
    if pattern["hat"][step]:
        window.audioHelper.hat()


def stop(event=None):
    global running, current_step, loop_task
    running = False
    current_step = -1
    loop_task = None
    refresh_pads()
    set_status("Stopped.")


async def sequencer_loop():
    global current_step, running, loop_task
    step = 0
    while running:
        current_step = step
        refresh_pads()
        play_step(step)
        bpm = get_bpm()
        swing = get_swing()
        base = 60 / bpm / 4
        wait = base * (1 + swing) if step % 2 else base * (1 - swing)
        await asyncio.sleep(max(0.03, wait))
        step = (step + 1) % STEPS
    loop_task = None


def start(event=None):
    global running, loop_task
    if running:
        return
    try:
        state = window.audioHelper.ensureUnlockedState()
        set_audio_debug(f"Audio context: {state}")
    except Exception as exc:
        set_audio_debug(f"Audio unlock check failed: {exc}")
    running = True
    set_status("Running. Tap pads live while it plays.")
    loop_task = asyncio.create_task(sequencer_loop())


def on_load_preset(event=None):
    load_preset(preset_el.value)


def test_sound(event=None):
    try:
        state = window.audioHelper.ensureUnlockedState()
        window.audioHelper.kick()
        window.audioHelper.hat()
        set_audio_debug(f"Test sound played. Audio context: {state}")
        set_status("Triggered a test sound.")
    except Exception as exc:
        set_audio_debug(f"Test sound failed: {exc}")
        set_status("Test sound failed.")


build_grid()
load_preset("starter")
update_value_labels()
set_audio_debug("Audio not unlocked yet.")

bind_event(bpm_el, "input", update_value_labels)
bind_event(swing_el, "input", update_value_labels)
bind_event(document.getElementById("load-preset"), "click", on_load_preset)
bind_event(document.getElementById("clear"), "click", clear_pattern)
bind_event(document.getElementById("randomize"), "click", randomize_pattern)
bind_event(document.getElementById("fill-hats"), "click", fill_hats)
bind_event(document.getElementById("drop-kick"), "click", drop_kick)
bind_event(document.getElementById("start"), "click", start)
bind_event(document.getElementById("stop"), "click", stop)
bind_event(document.getElementById("test-sound"), "click", test_sound)
