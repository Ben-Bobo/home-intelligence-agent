import uuid
import re
import base64
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.logger import get_logger
from app.errors import DocumentIngestionError

logger = get_logger(__name__)

CHUNK_CONFIGS = {
    "mortgage": {"chunk_size": 300, "chunk_overlap": 50},
    "inspection_report": {"chunk_size": 600, "chunk_overlap": 100},
    "appliance_manual": {"chunk_size": 800, "chunk_overlap": 100},
    "contractor_quote": {"chunk_size": 400, "chunk_overlap": 50},
    "warranty": {"chunk_size": 400, "chunk_overlap": 50},
    "hoa_rules": {"chunk_size": 600, "chunk_overlap": 100},
    "permit": {"chunk_size": 400, "chunk_overlap": 50},
    "general": {"chunk_size": 800, "chunk_overlap": 100}
}


def should_use_vision(page_text: str) -> bool:
    """Triggers vision when most of the page content is short disconnected lines."""
    stripped = page_text.strip()

    if len(stripped) < 50:
        return True

    lines = [l for l in stripped.split("\n") if l.strip()]
    if not lines:
        return True

    # Count lines that look like real sentences (long with punctuation)
    sentence_lines = sum(
        1 for line in lines
        if len(line) > 60 and ("." in line or "," in line)
    )

    sentence_ratio = sentence_lines / len(lines)

    # If less than 20% of lines are real sentences, this is probably a form
    if sentence_ratio < 0.2:
        return True

    return False


def vision_extract(page_image_bytes: bytes) -> str:
    """Use GPT-4o to read a page image and return structured text."""
    settings = get_settings()

    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.openai_api_key,
        timeout=30
    )

    b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

    response = llm.invoke([{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_image}"}
            },
            {
                "type": "text",
                "text": """Extract all information from this document page.

                For form fields, format as 'Label: Value' on a single line.
                For tables, format as structured text with labels and values together.
                For narrative text with headers, keep the header attached to its paragraph 
                as one continuous block — do not put a header on its own line.
                For any blank or unfilled fields, skip them entirely.
                Only include fields that have actual values filled in.
                Do not describe the layout. Just output the extracted information.

                Never output a heading or label with no following content."""
            }
        ]
    }])

    return response.content


def render_page_to_image(file_path: str, page_num: int) -> bytes:
    """Render a PDF page to a PNG image."""
    import pypdfium2 as pdfium
    import io

    pdf = pdfium.PdfDocument(file_path)
    page = pdf[page_num]
    bitmap = page.render(scale=2)  # 2x scale for readability
    pil_image = bitmap.to_pil()

    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    pdf.close()
    return image_bytes


def clean_text(text: str) -> str:
    """Remove form template noise from extracted text."""
    text = re.sub(r'_{3,}', '', text)
    text = re.sub(r'Authentisign ID:\s*[\w-]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    return text.strip()


def load_and_chunk(
    file_path: str,
    filename: str,
    doc_type: str = "general",
    chunk_size: int = None,
    chunk_overlap: int = None
) -> tuple[list[Document], dict]:
    path = Path(file_path)

    if not path.exists():
        raise DocumentIngestionError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            raw_docs = _process_pdf(str(path), filename)
        elif suffix in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            raw_docs = [Document(page_content=clean_text(content))]
        else:
            raise DocumentIngestionError(f"Unsupported file type: {suffix}")
    except DocumentIngestionError:
        raise
    except Exception as e:
        raise DocumentIngestionError(f"Failed to load {filename}: {str(e)}")

    raw_docs = [doc for doc in raw_docs if doc.page_content.strip()]

    config = CHUNK_CONFIGS.get(doc_type, CHUNK_CONFIGS["general"]).copy()
    if chunk_size is not None:
        config["chunk_size"] = chunk_size
    if chunk_overlap is not None:
        config["chunk_overlap"] = chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"]
    )
    chunks = splitter.split_documents(raw_docs)

    # Filter out chunks that are too small to be meaningful
    MIN_CHUNK_LENGTH = 20
    chunks = [c for c in chunks if len(c.page_content.strip()) >= MIN_CHUNK_LENGTH]

    doc_id = str(uuid.uuid4())

    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "document_id": doc_id,
            "filename": filename,
            "document_type": doc_type,
            "chunk_index": i,
            "total_chunks": len(chunks)
        })

    logger.info(
        "Chunked %s | type=%s | chunk_size=%d | overlap=%d | chunks=%d",
        filename, doc_type, config["chunk_size"], config["chunk_overlap"], len(chunks)
    )
    return chunks, config


def _process_pdf(file_path: str, filename: str) -> list[Document]:
    """Process PDF with per-page strategy: text extraction or vision."""
    loader = PyPDFLoader(file_path)
    text_pages = loader.load()

    processed = []
    vision_count = 0
    text_count = 0

    for i, page in enumerate(text_pages):
        page_text = page.page_content

        if should_use_vision(page_text):
            try:
                image_bytes = render_page_to_image(file_path, i)
                content = vision_extract(image_bytes)
                processed.append(Document(
                    page_content=content,
                    metadata={"page": i, "extraction": "vision"}
                ))
                vision_count += 1
                logger.debug("Page %d | vision extraction", i)
            except Exception as e:
                logger.warning("Page %d | vision failed, falling back to text | %s", i, str(e))
                cleaned = clean_text(page_text)
                if cleaned:
                    processed.append(Document(
                        page_content=cleaned,
                        metadata={"page": i, "extraction": "text_fallback"}
                    ))
                    text_count += 1
        else:
            cleaned = clean_text(page_text)
            if cleaned:
                processed.append(Document(
                    page_content=cleaned,
                    metadata={"page": i, "extraction": "text"}
                ))
                text_count += 1

    logger.info(
        "Processed %s | text_pages=%d | vision_pages=%d | total=%d",
        filename, text_count, vision_count, len(processed)
    )
    return processed