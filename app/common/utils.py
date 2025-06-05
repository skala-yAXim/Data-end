import json
import re

from docx import Document
import pandas as pd

def clean_html(raw_html):
    return re.sub(r'<[^>]+>', '', raw_html)
  
def extract_text_from_json(json_str):
    def recursive_extract(obj, results):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "text":
                    results.append(value)
                else:
                    recursive_extract(value, results)
        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item, results)

    try:
        parsed = json.loads(json_str)
        texts = []
        recursive_extract(parsed, texts)
        return texts
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)
        return []

def extract_from_docx(file_path: str) -> str:
    """DOCX 파일에서 텍스트 추출"""
    doc = Document(file_path)
    text_parts = []
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text.strip())
            
    # 표 내용도 추출
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                if cell.text.strip():
                    row_text.append(cell.text.strip())
            if row_text:
                text_parts.append(" | ".join(row_text))
    
    return "\n".join(text_parts)

def extract_from_xlsx(file_path: str) -> str:
    """XLSX 파일에서 텍스트 추출"""
    text_parts = []
    
    # 모든 시트 읽기
    excel_file = pd.ExcelFile(file_path)
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        text_parts.append(f"[시트: {sheet_name}]")
        
        # 컬럼명 추가
        if not df.empty:
            text_parts.append("컬럼: " + " | ".join(str(col) for col in df.columns))
            
            # 데이터 행 추가 (최대 100행)
            for idx, row in df.head(100).iterrows():
                row_text = " | ".join(str(val) for val in row.values if pd.notna(val))
                if row_text.strip():
                    text_parts.append(row_text)
    
    return "\n".join(text_parts)


def extract_from_txt(file_path: str) -> str:
    """TXT 파일에서 텍스트 추출"""
    encodings = ['utf-8', 'cp949', 'euc-kr']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # 모든 인코딩 실패 시
    return "텍스트 파일 인코딩 오류"
