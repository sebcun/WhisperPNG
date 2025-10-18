from flask import Flask, render_template, request, send_file, abort
from werkzeug.utils import secure_filename
from PIL import Image
import io
import os

app = Flask(__name__)
app.secret_key = "secret-key"


def to_bin(data):
    if isinstance(data, str):
        return "".join(format(ord(i), "08b") for i in data)
    elif isinstance(data, (bytes, bytearray)):
        return "".join(format(i, "08b") for i in data)
    elif isinstance(data, int):
        return format(data, "08b")
    else:
        raise TypeError("Type not supported.")


def encode(img: Image.Image, message: str):
    if img.mode != "RGB":
        img = img.convert("RGB")
    encoded = img.copy()
    width, height = img.size
    pixels = encoded.load()

    marker = "<<<END>>>"
    data = to_bin(message + marker)
    data_len = len(data)
    capacity = width * height * 3

    if data_len > capacity:
        raise ValueError(f"Message too large for this image.")

    data_index = 0
    for y in range(height):
        for x in range(width):
            if data_index >= data_len:
                break

            r, g, b = pixels[x, y]
            r_bin = format(r, "08b")
            b_bin = format(g, "08b")
            g_bin = format(b, "08b")

            if data_index < data_len:
                r = int(r_bin[:-1] + data[data_index], 2)
                data_index += 1
            if data_index < data_len:
                g = int(g_bin[:-1] + data[data_index], 2)
                data_index += 1
            if data_index < data_len:
                b = int(b_bin[:-1] + data[data_index], 2)
                data_index += 1

            pixels[x, y] = (r, g, b)
        if data_index >= data_len:
            break

    out = io.BytesIO()

    encoded.save(out, format="PNG")
    out.seek(0)
    return out


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    message = request.form.get("message")
    image_file = request.files.get("file")

    if not image_file or image_file.filename == "":
        return "No image uploaded", 400

    try:
        pil_img = Image.open(image_file.stream)
    except Exception as e:
        return f"Failed to open uploaded image: {e}", 400

    try:
        encoded_io = encode(pil_img, message)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"Encoding failed: {e}", 500
    original_name = secure_filename(image_file.filename) or "image.png"
    base, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".png"

    if message.strip():
        new_base = secure_filename(message.strip())
        if not new_base:
            new_base = base
    else:
        new_base = base

    new_filename = f"{new_base}_whisper{ext}"

    mimetype = image_file.mimetype or "application/octet-stream"

    return send_file(
        encoded_io,
        mimetype=mimetype,
        as_attachment=True,
        download_name=new_filename,
    )


if __name__ == "__main__":
    app.run(debug=True)
