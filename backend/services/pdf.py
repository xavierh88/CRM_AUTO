"""PDF service for document processing"""
import io
import shutil
from pathlib import Path
from config import UPLOADS_DIR, logger

def merge_files_to_pdf(files_list: list, output_path: Path) -> bool:
    """
    Merge multiple PDF/image files into a single PDF
    
    Args:
        files_list: List of tuples (file_path, file_extension)
        output_path: Path for the output PDF
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from PyPDF2 import PdfMerger, PdfReader
        from PIL import Image
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        merger = PdfMerger()
        temp_pdfs = []
        
        for file_path, file_ext in files_list:
            if file_ext == '.pdf':
                merger.append(str(file_path))
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                # Convert image to PDF
                img = Image.open(file_path)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Create PDF from image
                temp_pdf_path = file_path.with_suffix('.temp.pdf')
                temp_pdfs.append(temp_pdf_path)
                
                img_width, img_height = img.size
                page_width, page_height = letter
                
                # Scale image to fit page
                scale = min(page_width / img_width, page_height / img_height) * 0.9
                new_width = img_width * scale
                new_height = img_height * scale
                
                # Center on page
                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2
                
                c = canvas.Canvas(str(temp_pdf_path), pagesize=letter)
                c.drawImage(str(file_path), x, y, new_width, new_height)
                c.save()
                
                merger.append(str(temp_pdf_path))
        
        # Write merged PDF
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        merger.close()
        
        # Clean up temp files
        for temp_pdf in temp_pdfs:
            if temp_pdf.exists():
                temp_pdf.unlink()
        
        logger.info(f"PDF merged successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error merging PDFs: {str(e)}")
        return False
