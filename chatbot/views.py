import logging
from io import BytesIO

import requests

from django.contrib import messages
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from pypdf import PdfReader

from .models import Conversation, Message


logger = logging.getLogger(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 200
MAX_PDF_TEXT_LENGTH = 100_000


# =========================================================
# SESSION / CONVERSATION HELPERS
# =========================================================

def get_session_key(request):
    """Browser session chi key milavto (nasel tar session banavto)."""

    if not request.session.session_key:
        request.session.create()

    return request.session.session_key


def get_conversation(request):
    """
    Active chat milavto.

    1. Session madhe saved active_chat_id asel tar toch chat.
    2. Nasel tar ya session cha sarvat navin chat.
    3. Tehi nasel tar navin chat banavto.
    """

    session_key = get_session_key(request)

    active_id = request.session.get("active_chat_id")

    if active_id:
        conversation = Conversation.objects.filter(
            id=active_id,
            session_key=session_key,
        ).first()

        if conversation:
            return conversation

    conversation = (
        Conversation.objects
        .filter(session_key=session_key)
        .order_by("-updated_at")
        .first()
    )

    if not conversation:
        conversation = Conversation.objects.create(
            session_key=session_key,
            title="New Chat",
        )

    request.session["active_chat_id"] = conversation.id

    return conversation


def get_user_conversations(request):
    """Sidebar sathi ya session che sarve chats."""

    session_key = get_session_key(request)

    return Conversation.objects.filter(
        session_key=session_key
    ).order_by("-updated_at")


# =========================================================
# OLLAMA AI RESPONSE
# =========================================================

def ask_ollama(messages_list, pdf_text=""):
    """Local Ollama kadun uttar milavto."""

    system_prompt = """
You are RohGPT, a helpful AI assistant.

Instructions:
1. Answer clearly, accurately, and helpfully.
2. Support programming, Python, Django, AI, and general topics.
3. Your default response language is English. Write all explanations in English, regardless of the language or script used in the user's message or uploaded document.
4. Do not mirror the user's language. If they write in Marathi, Hindi, or another language, understand their request and answer in English.
5. Continue answering in English even if earlier assistant messages in this conversation used another language.
6. Only include non-English text when the user explicitly asks for a translation, a direct quote, or specific wording in that language; keep explanations in English.
7. For programming questions, provide understandable code and explain it in English. Keep code syntax and standard technical identifiers unchanged.
8. Never claim that you read a document unless its content was provided.
"""

    if pdf_text:
        system_prompt += f"""

The user has uploaded a PDF document.

Use the following extracted PDF content when answering
questions about the document.

If the answer is not available in the document, clearly
tell the user that the document does not contain enough
information to answer the question.

PDF CONTENT START
{pdf_text}
PDF CONTENT END
"""

    ollama_messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    recent_messages = messages_list[-12:]
    last_user_index = next(
        (
            index
            for index in range(len(recent_messages) - 1, -1, -1)
            if recent_messages[index].get("role") == "user"
        ),
        None,
    )

    # Keep the active language instruction adjacent to the current request.
    for index, item in enumerate(recent_messages):

        role = item.get("role")

        if role not in ("user", "assistant"):
            continue

        content = str(item.get("content", "")).strip()

        if not content:
            continue

        if index == last_user_index:
            content += (
                "\n\nReminder: answer in English unless I explicitly "
                "request another language."
            )

        ollama_messages.append({
            "role": role,
            "content": content,
        })

    payload = {
        "model": OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180,
        )

        response.raise_for_status()

        result = response.json()

        answer = result.get("message", {}).get("content", "")

        if not answer.strip():
            return (
                "The AI returned an empty response. Please try again."
            )

        return answer.strip()

    except requests.exceptions.ConnectionError:
        logger.exception("Ollama connection failed")

        return (
            "Could not connect to Ollama. Check that Ollama is running, then try again."
        )

    except requests.exceptions.Timeout:
        logger.exception("Ollama request timed out")

        return (
            "The AI is taking too long to respond. Please try again."
        )

    except requests.exceptions.RequestException:
        logger.exception("Ollama request failed")

        return (
            "The AI service is unavailable. Check Ollama and the selected model."
        )

    except (ValueError, TypeError, AttributeError):
        logger.exception("Invalid Ollama response")

        return (
            "The AI returned an invalid response. Please try again."
        )


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_pdf_text(uploaded_file):
    """
    PDF madhil text extract karto.

    Maryada: 10 MB, 200 pages, 100,000 characters.
    """

    if not uploaded_file:
        raise ValueError("Please choose a PDF file.")

    filename = uploaded_file.name

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    if uploaded_file.size > MAX_PDF_SIZE:
        raise ValueError(
            "The PDF file must be 10 MB or smaller."
        )

    try:
        file_bytes = uploaded_file.read()

        if not file_bytes:
            raise ValueError("The uploaded PDF is empty.")

        reader = PdfReader(BytesIO(file_bytes), strict=False)

        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")

                if not decrypted:
                    raise ValueError(
                        "Password-protected PDFs are not supported."
                    )

            except Exception as exc:
                raise ValueError(
                    "This PDF is encrypted. Upload an unencrypted PDF."
                ) from exc

        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(
                f"The PDF can contain at most {MAX_PDF_PAGES} pages."
            )

        extracted_parts = []
        total_length = 0

        for page in reader.pages:

            page_text = page.extract_text() or ""

            if page_text.strip():
                remaining = MAX_PDF_TEXT_LENGTH - total_length

                if remaining <= 0:
                    break

                page_text = page_text[:remaining]

                extracted_parts.append(page_text)
                total_length += len(page_text)

        pdf_text = "\n\n".join(extracted_parts).strip()

        if not pdf_text:
            raise ValueError(
                "Could not extract text from this PDF. It may be scanned; OCR is not supported."
            )

        return pdf_text

    except ValueError:
        raise

    except Exception as exc:
        logger.exception("PDF extraction failed")

        raise ValueError(
            "There was a problem reading the PDF. Please try another file."
        ) from exc


# =========================================================
# CHAT HOME
# =========================================================

@require_http_methods(["GET", "POST"])
def chat_home(request):
    """RohGPT che mukhya chat page."""

    conversation = get_conversation(request)

    if request.method == "POST":

        action = request.POST.get("action", "").strip()

        # ---------------- CLEAR CHAT ----------------

        if action == "clear":

            conversation.messages.all().delete()

            conversation.title = "New Chat"
            conversation.pdf_name = ""
            conversation.pdf_text = ""

            conversation.save(
                update_fields=[
                    "title",
                    "pdf_name",
                    "pdf_text",
                    "updated_at",
                ]
            )

            messages.success(request, "Chat cleared.")

            return redirect("chat_home")

        # ---------------- REGENERATE RESPONSE ----------------

        if action == "regenerate":
            history = list(conversation.messages.order_by("created_at", "id"))

            if (
                len(history) < 2
                or history[-1].role != "assistant"
                or history[-2].role != "user"
            ):
                messages.warning(
                    request,
                    "There is no previous user message to regenerate a response for.",
                )
                return redirect("chat_home")

            previous_answer = history[-1]
            ollama_messages = [
                {"role": item.role, "content": item.content}
                for item in history[:-1]
            ]
            answer = ask_ollama(
                ollama_messages,
                pdf_text=conversation.pdf_text or "",
            )
            previous_answer.content = answer
            previous_answer.save(update_fields=["content"])
            conversation.save(update_fields=["updated_at"])

            return redirect("chat_home")

        # ---------------- SEND MESSAGE ----------------

        user_message = (
            request.POST.get("message")
            or request.POST.get("prompt")
            or ""
        ).strip()

        if not user_message:

            messages.warning(request, "Please enter a message.")

            return redirect("chat_home")

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        if conversation.title == "New Chat":

            conversation.title = user_message[:60]

            conversation.save(
                update_fields=[
                    "title",
                    "updated_at",
                ]
            )

        history = conversation.messages.order_by("created_at", "id")

        ollama_messages = [
            {"role": item.role, "content": item.content}
            for item in history
        ]

        answer = ask_ollama(
            ollama_messages,
            pdf_text=conversation.pdf_text or "",
        )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer,
        )

        conversation.save(update_fields=["updated_at"])

        return redirect("chat_home")

    # ---------------- GET REQUEST ----------------

    chat_messages = conversation.messages.all()

    conversations = get_user_conversations(request)

    # Mahatvacha: context madhe "messages" key vaparu nako.
    # Toh Django cha messages framework (success/error alerts) override karto.
    context = {
        "conversation": conversation,
        "conversations": conversations,
        "chat_messages": chat_messages,
        "pdf_name": conversation.pdf_name,
        "has_pdf": bool(conversation.pdf_text),
    }

    return render(request, "chatbot/index.html", context)


# =========================================================
# MULTI CHAT: NEW / OPEN / DELETE
# =========================================================

@require_http_methods(["POST"])
def new_chat(request):
    """Navin chat banavto ani active karto."""

    session_key = get_session_key(request)

    # Jar active chat ajun rikama asel tar navin banvaychi garaj nahi.
    current = Conversation.objects.filter(
        id=request.session.get("active_chat_id"),
        session_key=session_key,
    ).first()

    if current and not current.messages.exists():
        return redirect("chat_home")

    conversation = Conversation.objects.create(
        session_key=session_key,
        title="New Chat",
    )

    request.session["active_chat_id"] = conversation.id

    return redirect("chat_home")


@require_http_methods(["POST"])
def open_chat(request, chat_id):
    """Sidebar madhla chat ughadto."""

    session_key = get_session_key(request)

    conversation = get_object_or_404(
        Conversation,
        id=chat_id,
        session_key=session_key,
    )

    request.session["active_chat_id"] = conversation.id

    return redirect("chat_home")


@require_http_methods(["POST"])
def delete_chat(request, chat_id):
    """Chat ani tyatle messages delete karto."""

    session_key = get_session_key(request)

    conversation = get_object_or_404(
        Conversation,
        id=chat_id,
        session_key=session_key,
    )

    conversation.delete()

    if request.session.get("active_chat_id") == chat_id:
        request.session.pop("active_chat_id", None)

    messages.success(request, "Chat deleted.")

    return redirect("chat_home")


# =========================================================
# PDF UPLOAD / REMOVE
# =========================================================

@require_http_methods(["POST"])
def upload_pdf(request):
    """PDF madhla text active conversation madhe save karto."""

    conversation = get_conversation(request)

    uploaded_file = (
        request.FILES.get("pdf_file")
        or request.FILES.get("pdf")
        or request.FILES.get("file")
    )

    if not uploaded_file:

        messages.error(request, "Please choose a PDF file.")

        return redirect("chat_home")

    try:

        pdf_text = extract_pdf_text(uploaded_file)

        conversation.pdf_name = uploaded_file.name
        conversation.pdf_text = pdf_text

        conversation.save(
            update_fields=[
                "pdf_name",
                "pdf_text",
                "updated_at",
            ]
        )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=(
                f"PDF '{uploaded_file.name}' attached successfully.\n\n"
                "You can now ask questions about its contents."
            ),
        )

        messages.success(request, "PDF uploaded successfully.")

    except ValueError as exc:

        messages.error(request, str(exc))

    except DatabaseError:

        logger.exception("Database error during PDF upload")

        messages.error(
            request,
            "A database error occurred while saving the PDF. Check that migrations are up to date."
        )

    except Exception:

        logger.exception("Unexpected PDF upload error")

        messages.error(
            request,
            "An unexpected error occurred while uploading the PDF."
        )

    return redirect("chat_home")


@require_http_methods(["POST"])
def remove_pdf(request):
    """Active conversation madhun PDF kadhto."""

    conversation = get_conversation(request)

    conversation.pdf_name = ""
    conversation.pdf_text = ""

    conversation.save(
        update_fields=[
            "pdf_name",
            "pdf_text",
            "updated_at",
        ]
    )

    messages.success(request, "PDF removed from this chat.")

    return redirect("chat_home")