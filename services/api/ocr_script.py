import pytesseract
from PIL import Image
import sys

try:
    img_path = '/Users/mychanging/Downloads/learnforge-v2-product/.data/artifacts/artifacts/source.image/artifact_3f939af89723/upload-1.jpeg'
    text = pytesseract.image_to_string(Image.open(img_path))
    print("OCR Output:")
    print(text)
except Exception as e:
    print("Error:", e)
