import docx
def extract():
    doc = docx.Document('sample.docx')
    with open('sample_docx_text.txt', 'w', encoding='utf-8') as f:
        for para in doc.paragraphs:
            f.write(para.text + '\n')
extract()
