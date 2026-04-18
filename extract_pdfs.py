import PyPDF2
import os

pdfs = [f for f in os.listdir('.') if f.endswith('.pdf')]
for pdf_name in pdfs:
    out_name = pdf_name.replace('.pdf', '_extracted.txt')
    try:
        reader = PyPDF2.PdfReader(pdf_name)
        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                all_text.append(f"--- Page {i+1} ---\n{text}")
        with open(out_name, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(all_text))
        print(f"OK: {pdf_name} -> {out_name} ({len(all_text)} pages, {sum(len(t) for t in all_text)} chars)")
    except Exception as e:
        print(f"ERR: {pdf_name}: {e}")
