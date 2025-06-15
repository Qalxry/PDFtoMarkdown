import os
import tempfile
from typing import List, Tuple
import fitz  # PyMuPDF
from PIL import Image
import io
from tqdm import tqdm

class PDFProcessor:
    @staticmethod
    def convert_pdf_to_images(pdf_path: str, output_dir: str = None) -> List[str]:
        """Convert PDF to images, returns list of image paths with sequential numbering."""
        # If no output directory specified, create a temp directory
        if not output_dir:
            output_dir = tempfile.mkdtemp()
        else:
            os.makedirs(output_dir, exist_ok=True)
            
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        image_paths = []
        
        # Iterate through pages and convert to images
        for page_num in tqdm(range(len(pdf_document)), desc="Converting PDF to images", unit="page"):
            page = pdf_document.load_page(page_num)
            
            # Render page to an image with a higher resolution (300 DPI)
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            
            # Generate image file path with sequential numbering
            image_path = os.path.join(output_dir, f"page_{page_num + 1:03d}.png")
            
            # Save the image
            pix.save(image_path)
            image_paths.append(image_path)
            
        pdf_document.close()
        return image_paths
        
    @staticmethod
    def load_image(image_path: str) -> bytes:
        """Load image from path and return as bytes."""
        with Image.open(image_path) as img:
            # Convert to RGB if image is in RGBA mode (has transparency)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            # Create a bytes buffer and save the image to it
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            
            # Get the bytes from the buffer
            image_bytes = buffer.getvalue()
            
        return image_bytes