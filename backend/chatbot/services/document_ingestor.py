from pathlib import Path
from pypdf import PdfReader

class DocumentIngestor: 
    def __init__(self, file_path : str | Path):
        self.file_path = Path(file_path)
        
    def extract_pages(self) -> list[dict]:
        if not self.file_path.is_file():
            raise FileNotFoundError(f"PDF not found: {self.file_path}")
        
        pages = []
        
        with self.file_path.open('rb') as pdf_file:
            reader = PdfReader(pdf_file) 
            
            for page_number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                
                # Preserve PDF page numbers, including pages without text
                
                pages.append({
                    "page_number" : page_number,
                    "text" : text,
                })
        
        if not any(page['text'] for page in pages):
            raise ValueError("The PDF contains no extractable text.")
        
        return pages