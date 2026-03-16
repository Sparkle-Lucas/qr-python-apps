import asyncio
import random
from js import document, window
from pyscript.ffi import create_proxy

TRACKS = ["kick", "snare", "hat", "clap", "openhat", "bass"]
STEPS = 16

seq_grid = document.getElementById("seq-grid")
status_el = document.getElementById("status")
audio_debug_el = document.getElementById("audio-debug")
bpm_el = document.getElementById("bpm")
swing_el = document.getElementById("swing")
bpm_value_el = document.getElementById("bpm-value")
swing_value_el = document.getElementById("swing-value")
preset_el = document.getElementById("preset")

pattern = {track: [0] * STEPS for track in TRACKS}
pad_elements = {track: [] for track in TRACKS}
running = False
loop_task = None
current_step = -1
proxies = []

PRESETS = {
    "starter": {
        "kick":    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":     [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        "clap":    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "openhat": [0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,1],
        "bass":    [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
    },
    "house": {
        "kick":    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":     [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
        "clap":    [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "openhat": [0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
        "bass":    [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,1,0],
    },
    "trap": {
        "kick":    [1,0,0,1, 0,0,1,0, 1,0,0,0, 1,0,1,0],
        "snare":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":     [1,1,1,1, 1,1,0,1, 1,0,1,1, 1,1,1,1],
        "clap":    [0,0,0,0, 0,0,0,0, 0,0,0,0, 1,0,0,0],
        "openhat": [0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,1],
        "bass":    [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,1,0,0],
    },
    "drill": {
        "kick":    [1,0,0,0, 0,1,0,0, 1,0,1,0, 0,1,0,0],
        "snare":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hat":     [1,1,0,1, 1,1,1,0, 1,1,0,1, 1,1,1,0],
        "clap":    [0,0,0,0, 1,0,0,0, 0,0,0,0, 0,0,0,0],
        "openhat": [0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,1],
        "bass":    [1,0,0,0, 0,0,0,0, 1,0,0,1, 0,0,0,0],
    },
}


def bind(element, event_name, fn):
    proxy = create_proxy(fn)
    proxies.append(proxy)
    element.addEventListener(event_name, proxy)



def set_status(text: str):
    status_el.textContent = text



def set_audio_debug(text: str):
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
        label.textContent = track.title() if track != "openhat" else "Open hat"
        seq_grid.appendChild(label)
        for step in range(STEPS):
            button = document.createElement("button")
            button.className = f"pad track-{track}"
            button.dataset.track = track
            button.dataset.step = str(step)
            bind(button, "click", make_toggle_handler(track, step))
            pad_elements[track].append(button)
            seq_grid.appendChild(button)



def make_toggle_handler(track, step):
    def handler(event=None):
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
    preset = PRESETS[name]
    for track in TRACKS:
        pattern[track] = preset[track][:]
    refresh_pads()
    set_status(f"Loaded preset: {name}.")



def clear_pattern(event=None):
    for track in TRACKS:
        pattern[track] = [0] * STEPS
    refresh_pads()
    set_status("Pattern cleared.")



def randomize_pattern(event=None):
    pattern["kick"] = [1 if i in (0, 8) else (1 if random.random() < 0.16 else 0) for i in range(STEPS)]
    pattern["snare"] = [1 if i in (4, 12) else 0 for i in range(STEPS)]
    pattern["hat"] = [1 if i % 2 == 0 else (1 if random.random() < 0.3 else 0) for i in range(STEPS)]
    pattern["clap"] = [1 if i in (4, 12) and random.random() < 0.75 else 0 for i in range(STEPS)]
    pattern["openhat"] = [1 if i in (7, 15) and random.random() < 0.75 else 0 for i in range(STEPS)]
    pattern["bass"] = [1 if i in (0, 6, 10, 14) and random.random() < 0.7 else 0 for i in range(STEPS)]
    refresh_pads()
    set_status("Randomized a fuller six-track beat.")



def fill_hats(event=None):
    pattern["hat"] = [1] * STEPS
    refresh_pads()
    set_status("Closed hats filled across all 16 steps.")



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
    if pattern["clap"][step]:
        window.audioHelper.clap()
    if pattern["openhat"][step]:
        window.audioHelper.openhat()
    if pattern["bass"][step]:
        window.audioHelper.bass()



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
    try:
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
    except asyncio.CancelledError:
        pass
    finally:
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
    set_status(f"Running at {bpm_el.value} BPM. Tap pads live while it plays.")
    loop_task = asyncio.create_task(sequencer_loop())



def on_load_preset(event=None):
    load_preset(str(preset_el.value))



def test_sound(event=None):
    try:
        state = window.audioHelper.ensureUnlockedState()
        window.audioHelper.kick()
        window.audioHelper.clap()
        window.audioHelper.openhat()
        set_audio_debug(f"Test sound played. Audio context: {state}")
        set_status("Triggered a short test sound.")
    except Exception as exc:
        set_audio_debug(f"Test sound failed: {exc}")
        set_status("Test sound failed.")


build_grid()
load_preset("starter")
update_value_labels()
set_audio_debug("Audio not unlocked yet.")

bind(bpm_el, "input", update_value_labels)
bind(swing_el, "input", update_value_labels)
bind(document.getElementById("load-preset"), "click", on_load_preset)
bind(document.getElementById("clear"), "click", clear_pattern)
bind(document.getElementById("randomize"), "click", randomize_pattern)
bind(document.getElementById("fill-hats"), "click", fill_hats)
bind(document.getElementById("drop-kick"), "click", drop_kick)
bind(document.getElementById("start"), "click", start)
bind(document.getElementById("stop"), "click", stop)
bind(document.getElementById("test-sound"), "click", test_sound)
