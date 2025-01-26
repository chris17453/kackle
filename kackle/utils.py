import os
import re
import uuid
import unicodedata
import string
from pathlib import Path
from PIL import Image
from .config import config 

def clean_title(title):
    cleaned_title = title.strip()
    cleaned_title = ''.join(ch for ch in cleaned_title if ch in string.printable)
    cleaned_title = unicodedata.normalize('NFKD', cleaned_title).encode('ascii', 'ignore').decode('utf-8')
    cleaned_title = re.sub(r'[^\w\s-]', '', cleaned_title).strip()
    return cleaned_title

def create_config_folders(config):
    """Create all folders specified in config['folders'] including parent directories"""
    for folder in config['folders'].values():
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {folder}")    

def sanitize_folder_name( path: str) -> str:
    """Convert folder to friendly name"""
    # Remove HTML tags
    no_html = re.sub('<[^<]+?>', '', path)
    # Convert to lowercase, replace spaces with underscore
    sanitized = re.sub(r'[^a-z0-9\s]', '', no_html.lower())
    return re.sub(r'\s+', '_', sanitized.strip())

def get_clean_path(path: str, file_name: str = None) -> str:
    """Get full path for topic directory and file"""
    # Generate a UUID-based file name if file_name is None
    if not file_name:
        file_name = f"{uuid.uuid4().hex}.webp"  # Default file extension is .webp
    
    sub_folder_name = sanitize_folder_name(path)
    base_dir = os.path.join(config['folders']['articles'], sub_folder_name)
    
    return base_dir, os.path.join(base_dir, file_name)


def compress_image(input_path, output_path, quality=85,img_type="webp"):
    """
    Compress an image and save it to a new file.
    :param input_path: Path to the input image file.
    :param output_path: Path to save the compressed image file.
    :param quality: Compression quality (1-100). Lower means more compression.
    """
    print(f"Compressing image: {input_path}")
    
    # Open the image
    with Image.open(input_path) as img:
        # Convert to RGB (to ensure compatibility with JPEG)
        img = img.convert("RGB")
        # Save with the desired quality
        img.save(output_path, img_type, quality=quality)
    
    print(f"Compressed image saved to: {output_path}")        