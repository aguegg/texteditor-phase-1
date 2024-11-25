from flask import Flask, request, render_template, send_file, redirect, url_for, session
from PIL import Image, ImageDraw, ImageFont
import os
import cv2
import pytesseract
import numpy as np
from collections import Counter

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.secret_key = b'\xa2\xd4\x07\x18\x9c\xba\xcd\xee\xf4\x8d\xbc\x1a\xe7\x35\xf1\x9e\x6c\x3d\x72\x10\x5e\xc4\x81\x2f'


# Ensure folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

def convert_to_png(image_path):
    img = Image.open(image_path)
    png_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(os.path.basename(image_path))[0] + ".png")
    img.convert("RGB").save(png_path, "PNG")
    return png_path

def remove_text(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pixels = img.reshape(-1, 3)
    most_common_color = Counter(map(tuple, pixels)).most_common(1)[0][0]
    boxes = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    margin = 5

    for i in range(len(boxes['text'])):
        if int(boxes['conf'][i]) > 60:
            x, y, w, h = boxes['left'][i], boxes['top'][i], boxes['width'][i], boxes['height'][i]
            img[max(0, y-margin):y+h+margin, max(0, x-margin):x+w+margin] = most_common_color

    processed_path = os.path.join(PROCESSED_FOLDER, 'processed_' + os.path.basename(image_path))
    cv2.imwrite(processed_path, img)
    return processed_path

def extract_text(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    extracted_text = pytesseract.image_to_string(gray)
    return extracted_text

def add_text_to_image(image_path, text):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()  # You can specify a TTF font file for custom fonts
    draw.text((10, 10), text, fill="black", font=font)  # Position and color of the text can be customized
    edited_path = os.path.join(PROCESSED_FOLDER, 'edited_' + os.path.basename(image_path))
    img.save(edited_path)
    return edited_path

@app.route('/', methods=['GET', 'POST'])
def upload_and_process_image():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            original_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(original_path)
            png_path = convert_to_png(original_path)
            session['uploaded_image_path'] = png_path  # Save path in session
            
            if 'process' in request.form:
                processed_path = remove_text(png_path)
                session['processed_image_path'] = processed_path

                return send_file(processed_path, mimetype='image/png')
            
    return render_template('upload3r.html', extracted_text=None)

@app.route('/extract_text', methods=['POST'])
def extract_text_route():
    file = request.files['file']
    if file:
        original_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(original_path)
        png_path = convert_to_png(original_path)
        extracted_text = extract_text(png_path)
        return render_template('upload3r.html', extracted_text=extracted_text)

@app.route('/edit_text', methods=['POST'])
def edit_text_route():
    edited_text = request.form['edited_text']
        # Get the uploaded image path from the session
    file_path = session.get('processed_image_path')
    if not file_path:
        return "Error: No processed image available.", 400
    # file_path = os.path.join(UPLOAD_FOLDER, 'file.png')  # Use the previously saved file
    
    edited_image_path = add_text_to_image(file_path, edited_text)
        # Store the edited image path in session
    session['edited_image_path'] = edited_image_path
    return send_file(edited_image_path, mimetype='image/png')

@app.route('/download_image')
def download_image():
    # Get the path to the edited or processed image from the session
    image_path = session.get('processed_image_path')
    if not image_path:
        return "Error: No processed image available.", 400
    
    return send_file(image_path, as_attachment=True, download_name=os.path.basename(image_path))

@app.route('/download_edited_image')
def download_edited_image():
    # Get the path to the edited image from the session
    edited_image_path = session.get('edited_image_path')
    if not edited_image_path:
        return "Error: No edited image available.", 400

    # Serve the edited image file for download
    return send_file(edited_image_path, as_attachment=True, download_name='edited_image.png')

if __name__ == '__main__':
    app.run(debug=True)
