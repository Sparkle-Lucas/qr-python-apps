import asyncio
from js import document, window
from pyscript import ffi

canvas = document.getElementById("meme-canvas")
ctx = canvas.getContext("2d")
img_el = document.getElementById("source-image")
status_el = document.getElementById("status")
template_el = document.getElementById("template")
top_el = document.getElementById("top-text")
bottom_el = document.getElementById("bottom-text")
font_scale_el = document.getElementById("font-scale")

DEFAULT_TOP = "WHEN THE CODE FINALLY WORKS"
DEFAULT_BOTTOM = "AND YOU HAVE TO ACT LIKE IT WAS EASY"


_CALLBACKS = []


def bind(element, event_name: str, handler):
    proxy = ffi.create_proxy(handler)
    _CALLBACKS.append(proxy)
    element.addEventListener(event_name, proxy)



def set_status(text: str):
    status_el.textContent = text


def draw_placeholder():
    canvas.width = 1200
    canvas.height = 1200
    ctx.fillStyle = "#f4f5f7"
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = "#d7dae0"
    ctx.fillRect(70, 70, 1060, 1060)
    ctx.fillStyle = "#2b3140"
    ctx.font = "bold 54px Impact, Arial Black, sans-serif"
    ctx.textAlign = "center"
    ctx.fillText("MEME GENERATOR", canvas.width / 2, 540)
    ctx.font = "28px Inter, Arial, sans-serif"
    ctx.fillText("Choose a template or upload an image, then tap Generate", canvas.width / 2, 600)


def get_selected_source() -> str:
    choice = template_el.value
    if choice == "upload":
        if window.uploadedMemeData:
            return str(window.uploadedMemeData)
        return ""
    return choice


async def wait_for_image() -> bool:
    for _ in range(120):
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


def draw_meme_text(text: str, anchor_y: float, from_bottom: bool = False):
    text = text.strip()
    if not text:
        return

    padding = canvas.width * 0.06
    max_width = canvas.width - padding * 2
    scale = float(font_scale_el.value) / 100
    base_size = int(canvas.width * 0.085 * scale)
    font_size, lines = auto_fit_lines(text, max_width, max(28, base_size))

    ctx.font = f"900 {font_size}px Impact, Arial Black, sans-serif"
    ctx.textAlign = "center"
    ctx.textBaseline = "top"
    ctx.lineJoin = "round"
    ctx.lineWidth = max(4, int(font_size * 0.17))
    ctx.strokeStyle = "black"
    ctx.fillStyle = "white"

    line_height = int(font_size * 1.05)
    total_height = line_height * len(lines)
    y = anchor_y - total_height if from_bottom else anchor_y

    for i, line in enumerate(lines):
        ly = y + i * line_height
        ctx.strokeText(line, canvas.width / 2, ly, max_width)
        ctx.fillText(line, canvas.width / 2, ly, max_width)


async def generate(event=None):
    src = get_selected_source()
    if not src:
        set_status("No uploaded image found. Choose a template or upload a photo first.")
        return

    set_status("Loading image...")
    img_el.src = src
    ok = await wait_for_image()
    if not ok:
        set_status("Image failed to load. Check the file or try another template.")
        return

    fit_canvas_to_image()
    ctx.drawImage(img_el, 0, 0, canvas.width, canvas.height)
    draw_meme_text(top_el.value, canvas.height * 0.05, from_bottom=False)
    draw_meme_text(bottom_el.value, canvas.height * 0.95, from_bottom=True)
    set_status("Generated. Download PNG when ready.")


def download(event=None):
    window.downloadCanvasAsPng("meme-canvas", "meme.png")


def reset_text(event=None):
    top_el.value = ""
    bottom_el.value = ""
    set_status("Text cleared.")


def load_defaults(event=None):
    top_el.value = DEFAULT_TOP
    bottom_el.value = DEFAULT_BOTTOM
    font_scale_el.value = "100"
    template_el.value = "./assets/classic_blank.png"
    asyncio.create_task(generate())


bind(document.getElementById("generate"), "click", lambda event: asyncio.create_task(generate()))
bind(document.getElementById("download"), "click", download)
bind(document.getElementById("reset-text"), "click", reset_text)
bind(document.getElementById("load-default"), "click", load_defaults)

top_el.value = DEFAULT_TOP
bottom_el.value = DEFAULT_BOTTOM
draw_placeholder()
asyncio.create_task(generate())
