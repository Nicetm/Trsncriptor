# utils/file_handler.py
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY
import textwrap

def save_as_text(text, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print("Error al guardar el archivo de texto:", e)

def save_as_docx(text, file_path="transcription.docx"):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(file_path)

def save_as_pdf_normal(text, file_path="transcription.pdf"):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    y_position = height - 40  # Inicializa la posición en la parte superior

    # Configura el ancho máximo de la línea
    max_line_width = 80  # Ajusta este valor si necesitas más o menos espacio

    # Divide el texto en líneas según los saltos de línea y ajusta al ancho de la página
    lines = text.split("\n")
    for line in lines:
        # Usa textwrap para dividir las líneas largas
        wrapped_lines = textwrap.wrap(line, width=max_line_width)
        for wrapped_line in wrapped_lines:
            c.drawString(40, y_position, wrapped_line)
            y_position -= 14
            if y_position < 40:  # Salta a la siguiente página si es necesario
                c.showPage()
                y_position = height - 40

    c.save()


def save_as_pdf(text, file_path="transcription.pdf"):
    # Crear documento PDF
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilo para texto justificado
    style = styles["Normal"]
    style.alignment = TA_JUSTIFY
    style.fontSize = 11
    style.leading = 14  # Espaciado entre líneas

    # Título del documento
    title_style = styles["Title"]
    title = Paragraph("Transcripción Generada", title_style)

    # Unir las líneas del texto en párrafos completos
    paragraphs = [title, Spacer(1, 12)]  # Título con espacio
    processed_text = text.replace("\n", " ").strip()  # Combina el texto en un solo bloque
    paragraphs.append(Paragraph(processed_text, style))

    # Construir el PDF
    doc.build(paragraphs)

