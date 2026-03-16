import asyncio
from js import document, window
from pyscript.ffi import create_proxy

canvas = document.getElementById("meme-canvas")
ctx = canvas.getContext("2d")
img_el = document.getElementById("source-image")
status_el = document.getElementById("status")
template_el = document.getElementById("template")
top_el = document.getElementById("top-text")
bottom_el = document.getElementById("bottom-text")
style_el = document.getElementById("style-mode")
align_el = document.getElementById("align-mode")
font_size_el = document.getElementById("font-size")
font_size_value_el = document.getElementById("font-size-value")
line_spacing_el = document.getElementById("line-spacing")
line_spacing_value_el = document.getElementById("line-spacing-value")

DEFAULT_TOP = "WHEN THE CODE FINALLY WORKS"
DEFAULT_BOTTOM = "AND YOU HAVE TO ACT LIKE IT WAS EASY"

proxies = []
drag_target = None
is_pointer_down = False
current_background = "blank-light"
top_y_ratio = 0.08
bottom_y_ratio = 0.92
last_top_bounds = None
last_bottom_bounds = None

STYLE_MAP = {
    "white-black": {"fill": "white", "stroke": "black", "line_width_factor": 0.16},
    "black-white": {"fill": "black", "stroke": "white", "line_width_factor": 0.16},
    "color-cyan": {"fill": "#9EF0FF", "stroke": "#0D2233", "line_width_factor": 0.16},
    "color-pink": {"fill": "#FFC3E7", "stroke": "#2A1024", "line_width_factor": 0.16},
    "no-stroke": {"fill": "white", "stroke": None, "line_width_factor": 0.0},
}


def bind(element, event_name, fn):
    proxy = create_proxy(fn)
    proxies.append(proxy)
    element.addEventListener(event_name, proxy)



def set_status(text: str):
    status_el.textContent = text



def update_value_labels(event=None):
    font_size_value_el.textContent = f"{font_size_el.value}%"
    line_spacing_value_el.textContent = f"{float(line_spacing_el.value) / 100:.2f}×"



def clamp(value, low, high):
    return max(low, min(high, value))



def draw_template_background(choice: str):
    canvas.width = 1200
    canvas.height = 1200
    if choice == "blank-dark":
        ctx.fillStyle = "#121827"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = "#20283C"
        ctx.fillRect(70, 70, 1060, 1060)
        ctx.fillStyle = "#5A678A"
        for i in range(0, canvas.width, 60):
            ctx.fillRect(i, 0, 2, canvas.height)
    elif choice == "gradient":
        grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
        grad.addColorStop(0, "#2A395A")
        grad.addColorStop(0.5, "#5D7FB8")
        grad.addColorStop(1, "#11182A")
        ctx.fillStyle = grad
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = "rgba(255,255,255,.08)"
        for r in range(8):
            ctx.beginPath()
            ctx.arc(220 + r * 90, 180 + r * 50, 70 + r * 14, 0, 6.28318)
            ctx.fill()
    else:
        ctx.fillStyle = "#f4f5f7"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = "#d7dae0"
        ctx.fillRect(70, 70, 1060, 1060)



def get_selected_source() -> str:
    choice = str(template_el.value)
    if choice == "upload":
        if window.uploadedMemeData:
            return str(window.uploadedMemeData)
        return ""
    return choice


async def wait_for_image() -> bool:
    for _ in range(140):
        if img_el.complete and img_el.naturalWidth > 0:
            return True
        await asyncio.sleep(0.05)
    return False



def fit_canvas_to_image():
    width = int(img_el.naturalWidth)
    height = int(img_el.naturalHeight)
    max_side = 1400
    scale = min(1, max_side / max(width, height))
    canvas.width = round(width * scale)
    canvas.height = round(height * scale)



def get_text_x(max_width: float):
    align = str(align_el.value)
    pad = canvas.width * 0.06
    if align == "left":
        return pad
    if align == "right":
        return canvas.width - pad
    return canvas.width / 2



def wrap_text(text: str, max_width: float, font_size: int):
    text = text.strip()
    if not text:
        return []
    ctx.font = f"900 {font_size}px Impact, Arial Black, sans-serif"
    if " " in text:
        words = text.split()
        lines = []
        current = words[0]
        for word in words[1:]:
            test = current + " " + word
            if ctx.measureText(test).width <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    lines = []
    current = ""
    for char in text:
        test = current + char
        if ctx.measureText(test).width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines



def auto_fit_lines(text: str, max_width: float, base_size: int):
    size = base_size
    while size >= 24:
        lines = wrap_text(text, max_width, size)
        if len(lines) <= 4:
            return size, lines
        size -= 4
    return 24, wrap_text(text, max_width, 24)



def draw_text_block(text: str, y_ratio: float, key: str):
    global last_top_bounds, last_bottom_bounds
    text = text.strip()
    if not text:
        bounds = {"x": 0, "y": 0, "w": 0, "h": 0}
        if key == "top":
            last_top_bounds = bounds
        else:
            last_bottom_bounds = bounds
        return

    padding = canvas.width * 0.06
    max_width = canvas.width - padding * 2
    scale = float(font_size_el.value) / 100
    base_size = int(canvas.width * 0.085 * scale)
    font_size, lines = auto_fit_lines(text, max_width, max(28, base_size))
    line_height = int(font_size * (float(line_spacing_el.value) / 100))
    total_height = line_height * len(lines)
    x = get_text_x(max_width)
    y = canvas.height * y_ratio
    align = str(align_el.value)

    style = STYLE_MAP[str(style_el.value)]
    ctx.font = f"900 {font_size}px Impact, Arial Black, sans-serif"
    ctx.textAlign = align
    ctx.textBaseline = "top"
    ctx.lineJoin = "round"
    ctx.lineWidth = max(0, int(font_size * style["line_width_factor"]))
    ctx.fillStyle = style["fill"]
    if style["stroke"]:
        ctx.strokeStyle = style["stroke"]

    max_line_width = 0
    for line in lines:
        max_line_width = max(max_line_width, ctx.measureText(line).width)

    if align == "left":
        left_x = x
    elif align == "right":
        left_x = x - max_line_width
    else:
        left_x = x - max_line_width / 2

    top_y = y if key == "top" else y - total_height
    top_y = clamp(top_y, 10, canvas.height - total_height - 10)

    for i, line in enumerate(lines):
        ly = top_y + i * line_height
        if style["stroke"] and ctx.lineWidth > 0:
            ctx.strokeText(line, x, ly, max_width)
        ctx.fillText(line, x, ly, max_width)

    bounds = {"x": left_x - 18, "y": top_y - 18, "w": max_line_width + 36, "h": total_height + 36}

    ctx.save()
    ctx.setLineDash([10, 8])
    ctx.strokeStyle = "rgba(255,255,255,.35)"
    ctx.lineWidth = 2
    ctx.strokeRect(bounds["x"], bounds["y"], bounds["w"], bounds["h"])
    ctx.restore()

    if key == "top":
        last_top_bounds = bounds
    else:
        last_bottom_bounds = bounds


async def redraw(event=None):
    global current_background
    choice = get_selected_source()
    if not choice:
        set_status("No uploaded image found. Upload a photo first, or choose a built-in background.")
        return

    if choice == "upload":
        src = str(window.uploadedMemeData) if window.uploadedMemeData else ""
        if not src:
            set_status("No uploaded image found. Upload a photo first.")
            return
        set_status("Loading image...")
        img_el.src = src
        ok = await wait_for_image()
        if not ok:
            set_status("Image failed to load. Try another file.")
            return
        fit_canvas_to_image()
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img_el, 0, 0, canvas.width, canvas.height)
        current_background = "upload"
    else:
        current_background = choice
        draw_template_background(choice)

    draw_text_block(top_el.value, top_y_ratio, "top")
    draw_text_block(bottom_el.value, bottom_y_ratio, "bottom")
    set_status("Generated. Drag the text blocks or download PNG when ready.")



def point_in_bounds(x: float, y: float, bounds):
    if not bounds:
        return False
    return bounds["x"] <= x <= bounds["x"] + bounds["w"] and bounds["y"] <= y <= bounds["y"] + bounds["h"]



def canvas_point(event):
    rect = canvas.getBoundingClientRect()
    scale_x = canvas.width / rect.width
    scale_y = canvas.height / rect.height
    x = (float(event.clientX) - rect.left) * scale_x
    y = (float(event.clientY) - rect.top) * scale_y
    return x, y



def on_pointer_down(event):
    global drag_target, is_pointer_down
    is_pointer_down = True
    x, y = canvas_point(event)
    if point_in_bounds(x, y, last_top_bounds):
        drag_target = "top"
    elif point_in_bounds(x, y, last_bottom_bounds):
        drag_target = "bottom"
    else:
        drag_target = None



def on_pointer_move(event):
    global top_y_ratio, bottom_y_ratio
    if not is_pointer_down or not drag_target:
        return
    _, y = canvas_point(event)
    ratio = clamp(y / canvas.height, 0.05, 0.95)
    if drag_target == "top":
        top_y_ratio = ratio
    else:
        bottom_y_ratio = ratio
    asyncio.create_task(redraw())



def on_pointer_up(event=None):
    global drag_target, is_pointer_down
    drag_target = None
    is_pointer_down = False



def on_generate(event=None):
    asyncio.create_task(redraw())



def on_download(event=None):
    window.downloadCanvasAsPng("meme-canvas", "meme.png")
    set_status("Downloading PNG...")



def on_reset_all(event=None):
    global top_y_ratio, bottom_y_ratio, current_background
    template_el.value = "blank-light"
    top_el.value = DEFAULT_TOP
    bottom_el.value = DEFAULT_BOTTOM
    style_el.value = "white-black"
    align_el.value = "center"
    font_size_el.value = "100"
    line_spacing_el.value = "105"
    top_y_ratio = 0.08
    bottom_y_ratio = 0.92
    update_value_labels()
    current_background = "blank-light"
    asyncio.create_task(redraw())



def on_live_control(event=None):
    update_value_labels()
    asyncio.create_task(redraw())


bind(document.getElementById("generate"), "click", on_generate)
bind(document.getElementById("download"), "click", on_download)
bind(document.getElementById("reset-all"), "click", on_reset_all)
bind(template_el, "change", on_live_control)
bind(top_el, "input", on_live_control)
bind(bottom_el, "input", on_live_control)
bind(style_el, "change", on_live_control)
bind(align_el, "change", on_live_control)
bind(font_size_el, "input", on_live_control)
bind(line_spacing_el, "input", on_live_control)
bind(canvas, "pointerdown", on_pointer_down)
bind(canvas, "pointermove", on_pointer_move)
bind(canvas, "pointerup", on_pointer_up)
bind(canvas, "pointerleave", on_pointer_up)

update_value_labels()
top_el.value = DEFAULT_TOP
bottom_el.value = DEFAULT_BOTTOM
asyncio.create_task(redraw())
