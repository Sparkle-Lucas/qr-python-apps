from js import document, window, Image, console
from pyscript.ffi import create_proxy

canvas = document.getElementById("meme-canvas")
ctx = canvas.getContext("2d")

template_select = document.getElementById("template")
uploader = document.getElementById("uploader")
top_input = document.getElementById("top-text")
bottom_input = document.getElementById("bottom-text")
style_select = document.getElementById("style-select")
align_select = document.getElementById("align-select")
font_size_input = document.getElementById("font-size")
line_spacing_input = document.getElementById("line-spacing")
status_el = document.getElementById("status")

generate_btn = document.getElementById("generate-btn")
reset_btn = document.getElementById("reset-btn")
download_btn = document.getElementById("download-btn")
reset_pos_btn = document.getElementById("reset-pos-btn")

_event_proxies = []
_image_proxies = []

MAX_IMAGE_DIM = 1200
PADDING = 22

current_bg = {
    "mode": "template",   # "template" or "upload"
    "template": "classic-light",
    "image": None,
}

text_state = {
    "top": {
        "x_frac": 0.50,
        "y_frac": 0.07,
        "box": None,
        "anchor_px": (0, 0),
    },
    "bottom": {
        "x_frac": 0.50,
        "y_frac": 0.83,
        "box": None,
        "anchor_px": (0, 0),
    },
}

drag_state = {
    "active": False,
    "target": None,
    "offset_x": 0,
    "offset_y": 0,
}


def bind(element, event_name, func):
    proxy = create_proxy(func)
    _event_proxies.append(proxy)
    element.addEventListener(event_name, proxy)


def set_status(msg: str):
    status_el.textContent = msg


def clamp(value, low, high):
    return max(low, min(high, value))


def get_font_size():
    return int(font_size_input.value)


def get_line_spacing():
    return float(line_spacing_input.value)


def get_align():
    return align_select.value


def get_style():
    return style_select.value


def reset_text_positions(event=None):
    align = get_align()
    if align == "left":
        x_frac = 0.07
    elif align == "right":
        x_frac = 0.93
    else:
        x_frac = 0.50

    text_state["top"]["x_frac"] = x_frac
    text_state["top"]["y_frac"] = 0.07
    text_state["bottom"]["x_frac"] = x_frac
    text_state["bottom"]["y_frac"] = 0.83
    render_scene()
    set_status("Text positions reset.")


def apply_style():
    style = get_style()
    if style == "white-black":
        return {
            "fill": "#ffffff",
            "stroke": "#000000",
            "line_width_factor": 0.16,
        }
    if style == "black-white":
        return {
            "fill": "#000000",
            "stroke": "#ffffff",
            "line_width_factor": 0.16,
        }
    if style == "color-black":
        return {
            "fill": "#7ab7ff",
            "stroke": "#091625",
            "line_width_factor": 0.15,
        }
    return {
        "fill": "#ffffff",
        "stroke": None,
        "line_width_factor": 0.0,
    }


def draw_template_background(name: str):
    canvas.width = 1000
    canvas.height = 1000
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if name == "classic-dark":
        ctx.fillStyle = "#111111"
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        ctx.fillStyle = "#1e1e1e"
        ctx.fillRect(60, 60, 880, 880)

    elif name == "blue-panel":
        ctx.fillStyle = "#1250b8"
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        ctx.strokeStyle = "rgba(255,255,255,0.22)"
        ctx.lineWidth = 4
        ctx.strokeRect(70, 70, 860, 860)

        ctx.fillStyle = "rgba(255,255,255,0.06)"
        ctx.fillRect(90, 90, 820, 820)

    else:
        # classic-light
        ctx.fillStyle = "#f5f5f5"
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        ctx.fillStyle = "#ffffff"
        ctx.fillRect(55, 55, 890, 890)

        ctx.strokeStyle = "#d9d9d9"
        ctx.lineWidth = 4
        ctx.strokeRect(55, 55, 890, 890)


def set_canvas_from_uploaded_image(img):
    natural_w = int(img.naturalWidth or img.width or 1000)
    natural_h = int(img.naturalHeight or img.height or 1000)

    scale = min(1.0, MAX_IMAGE_DIM / max(natural_w, natural_h))
    canvas.width = max(1, int(natural_w * scale))
    canvas.height = max(1, int(natural_h * scale))

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)


def wrap_text(text: str, max_width: float, font_size: int):
    if not text.strip():
        return []

    ctx.font = f"900 {font_size}px Impact, Haettenschweiler, Arial Black, sans-serif"

    # If there are spaces, wrap by words; otherwise wrap by characters.
    if " " in text.strip():
        units = text.strip().split()
        joiner = " "
    else:
        units = list(text.strip())
        joiner = ""

    lines = []
    current = units[0]

    for unit in units[1:]:
        candidate = current + joiner + unit
        if ctx.measureText(candidate).width <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = unit

    lines.append(current)
    return lines


def draw_text_block(name: str, text: str):
    if not text.strip():
        text_state[name]["box"] = None
        return

    align = get_align()
    font_size = get_font_size()
    line_spacing = get_line_spacing()
    style = apply_style()

    ctx.font = f"900 {font_size}px Impact, Haettenschweiler, Arial Black, sans-serif"
    ctx.textAlign = align
    ctx.textBaseline = "top"

    max_width = canvas.width - (PADDING * 2)

    x_anchor = text_state[name]["x_frac"] * canvas.width
    y_anchor = text_state[name]["y_frac"] * canvas.height

    lines = wrap_text(text, max_width, font_size)
    if not lines:
        text_state[name]["box"] = None
        return

    line_height = font_size * line_spacing
    total_height = len(lines) * line_height

    widths = [ctx.measureText(line).width for line in lines]
    max_line_width = max(widths) if widths else 0

    # Clamp anchor positions based on alignment and block size
    if align == "center":
        min_x = PADDING + (max_line_width / 2)
        max_x = canvas.width - PADDING - (max_line_width / 2)
    elif align == "left":
        min_x = PADDING
        max_x = canvas.width - PADDING - max_line_width
    else:  # right
        min_x = PADDING + max_line_width
        max_x = canvas.width - PADDING

    min_y = PADDING
    max_y = canvas.height - PADDING - total_height

    x_anchor = clamp(x_anchor, min_x, max_x)
    y_anchor = clamp(y_anchor, min_y, max_y)

    text_state[name]["x_frac"] = x_anchor / canvas.width
    text_state[name]["y_frac"] = y_anchor / canvas.height
    text_state[name]["anchor_px"] = (x_anchor, y_anchor)

    # Draw text
    ctx.fillStyle = style["fill"]
    if style["stroke"]:
        ctx.strokeStyle = style["stroke"]
        ctx.lineJoin = "round"
        ctx.lineWidth = max(2, int(font_size * style["line_width_factor"]))

    for i, line in enumerate(lines):
        y = y_anchor + i * line_height
        if style["stroke"]:
            ctx.strokeText(line, x_anchor, y, max_width)
        ctx.fillText(line, x_anchor, y, max_width)

    # Bounding box for dragging / hit testing
    if align == "center":
        left = x_anchor - max_line_width / 2
    elif align == "left":
        left = x_anchor
    else:
        left = x_anchor - max_line_width

    text_state[name]["box"] = {
        "left": left - 16,
        "top": y_anchor - 10,
        "right": left + max_line_width + 16,
        "bottom": y_anchor + total_height + 10,
    }


def render_scene():
    if current_bg["mode"] == "upload" and current_bg["image"] is not None:
        set_canvas_from_uploaded_image(current_bg["image"])
    else:
        draw_template_background(current_bg["template"])

    draw_text_block("top", top_input.value)
    draw_text_block("bottom", bottom_input.value)


def use_template(name: str):
    current_bg["mode"] = "template"
    current_bg["template"] = name
    current_bg["image"] = None
    render_scene()
    set_status(f"Template loaded: {name}.")


def load_uploaded_image():
    if not window.uploadedImageReady or not window.uploadedMemeData:
        set_status("No uploaded image is ready yet. Please upload a JPG or PNG image first.")
        return

    img = Image.new()

    def onload(evt):
        current_bg["mode"] = "upload"
        current_bg["image"] = img
        current_bg["template"] = None
        render_scene()
        set_status("Uploaded image loaded. Meme generated.")

    def onerror(evt):
        set_status("Failed to load the uploaded image. Try a JPG or PNG file.")

    onload_proxy = create_proxy(onload)
    onerror_proxy = create_proxy(onerror)
    _image_proxies.append(onload_proxy)
    _image_proxies.append(onerror_proxy)

    img.onload = onload_proxy
    img.onerror = onerror_proxy
    img.src = window.uploadedMemeData


def generate_preview(event=None):
    selected = template_select.value

    if selected == "upload":
        load_uploaded_image()
    else:
        use_template(selected)


def on_controls_change(event=None):
    # If alignment changes, reset x positions to sensible defaults
    if event is not None and event.target.id == "align-select":
        reset_text_positions()
        return

    # If we already have an uploaded image active, redraw that immediately.
    # Otherwise redraw current template.
    if current_bg["mode"] == "upload" and current_bg["image"] is not None:
        render_scene()
        set_status("Preview updated.")
    else:
        generate_preview()


def reset_all(event=None):
    template_select.value = "classic-light"
    top_input.value = ""
    bottom_input.value = ""
    style_select.value = "white-black"
    align_select.value = "center"
    font_size_input.value = "52"
    line_spacing_input.value = "1.15"

    window.uploadedMemeData = None
    window.uploadedImageReady = False
    uploader.value = ""

    current_bg["mode"] = "template"
    current_bg["template"] = "classic-light"
    current_bg["image"] = None

    reset_text_positions()
    render_scene()
    set_status("Reset to default template.")


def download_png(event=None):
    window.downloadCanvasAsPng("meme-canvas", "meme.png")
    set_status("Downloading PNG...")


def point_in_box(x, y, box):
    if not box:
        return False
    return box["left"] <= x <= box["right"] and box["top"] <= y <= box["bottom"]


def get_canvas_coords(event):
    rect = canvas.getBoundingClientRect()
    x = (event.clientX - rect.left) * canvas.width / rect.width
    y = (event.clientY - rect.top) * canvas.height / rect.height
    return x, y


def on_pointer_down(event):
    x, y = get_canvas_coords(event)

    top_box = text_state["top"]["box"]
    bottom_box = text_state["bottom"]["box"]

    # Prefer bottom if overlapping, then top
    if point_in_box(x, y, bottom_box):
        target = "bottom"
    elif point_in_box(x, y, top_box):
        target = "top"
    else:
        return

    anchor_x, anchor_y = text_state[target]["anchor_px"]
    drag_state["active"] = True
    drag_state["target"] = target
    drag_state["offset_x"] = x - anchor_x
    drag_state["offset_y"] = y - anchor_y

    try:
        canvas.setPointerCapture(event.pointerId)
    except Exception:
        pass


def on_pointer_move(event):
    if not drag_state["active"] or not drag_state["target"]:
        return

    x, y = get_canvas_coords(event)
    target = drag_state["target"]

    new_anchor_x = x - drag_state["offset_x"]
    new_anchor_y = y - drag_state["offset_y"]

    text_state[target]["x_frac"] = new_anchor_x / canvas.width
    text_state[target]["y_frac"] = new_anchor_y / canvas.height

    render_scene()
    set_status(f"Dragging {target} text.")


def on_pointer_up(event):
    drag_state["active"] = False
    drag_state["target"] = None


# Expose a JS-callable preview trigger for the uploader script
_preview_proxy = create_proxy(generate_preview)
_event_proxies.append(_preview_proxy)
window.triggerMemePreview = _preview_proxy


# Bind UI events
bind(generate_btn, "click", generate_preview)
bind(reset_btn, "click", reset_all)
bind(download_btn, "click", download_png)
bind(reset_pos_btn, "click", reset_text_positions)

bind(template_select, "change", on_controls_change)
bind(top_input, "input", on_controls_change)
bind(bottom_input, "input", on_controls_change)
bind(style_select, "change", on_controls_change)
bind(align_select, "change", on_controls_change)
bind(font_size_input, "input", on_controls_change)
bind(line_spacing_input, "input", on_controls_change)

bind(canvas, "pointerdown", on_pointer_down)
bind(canvas, "pointermove", on_pointer_move)
bind(canvas, "pointerup", on_pointer_up)
bind(canvas, "pointerleave", on_pointer_up)
bind(canvas, "pointercancel", on_pointer_up)

# Initial render
render_scene()
set_status("Ready. Choose a template or upload a JPG/PNG, then generate.")
