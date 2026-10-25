import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Conversation, Message
from .views import ask_ollama, retrieve_relevant_pdf_chunks


class ChatHomeTests(TestCase):
    def setUp(self):
        self.models_patcher = patch(
            "chatbot.views.get_ollama_models",
            return_value=["llama3.2:3b", "llava:latest"],
        )
        self.models_patcher.start()
        self.addCleanup(self.models_patcher.stop)

    @patch("chatbot.views.ask_ollama", return_value="नमस्कार!")
    def test_sends_message_and_saves_response(self, ask_ollama):
        self.client.get(reverse("chat_home"))

        response = self.client.post(
            reverse("chat_home"),
            {"message": "नमस्कार"},
        )

        self.assertRedirects(response, reverse("chat_home"))
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.title, "नमस्कार")
        self.assertEqual(
            list(conversation.messages.values_list("role", "content")),
            [("user", "नमस्कार"), ("assistant", "नमस्कार!")],
        )
        self.assertEqual(ask_ollama.call_args.args[0][0]["content"], "नमस्कार")
        self.assertEqual(ask_ollama.call_args.kwargs["pdf_text"], "")
        self.assertEqual(ask_ollama.call_args.kwargs["model_name"], "llama3.2:3b")

    @patch("chatbot.views.ask_ollama", return_value="नवे उत्तर")
    def test_regenerates_latest_assistant_response(self, ask_ollama):
        self.client.get(reverse("chat_home"))
        session = self.client.session
        conversation = Conversation.objects.get(
            id=session["active_chat_id"],
        )
        Message.objects.create(
            conversation=conversation,
            role="user",
            content="हा प्रश्न आहे",
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="जुने उत्तर",
        )

        response = self.client.post(
            reverse("chat_home"),
            {"action": "regenerate"},
        )

        self.assertRedirects(response, reverse("chat_home"))
        assistant_message.refresh_from_db()
        self.assertEqual(assistant_message.content, "नवे उत्तर")
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(
            ask_ollama.call_args.args[0][0]["content"],
            "हा प्रश्न आहे",
        )

    def test_empty_chat_renders_prompt_cards_and_model_label(self):
        response = self.client.get(reverse("chat_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What can I help with?")
        self.assertContains(response, "Replies are in English by default.")
        self.assertContains(response, "lang=\"en\"")
        self.assertNotContains(response, "नमस्कार")
        self.assertNotContains(response, "पाठवा")
        self.assertContains(response, "LOCAL")
        self.assertContains(response, 'data-prompt="')

    @patch("chatbot.views.ask_ollama")
    def test_regenerate_without_latest_user_message_is_rejected(self, ask_ollama):
        self.client.get(reverse("chat_home"))
        conversation = Conversation.objects.get()
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content="PDF जोडली आहे.",
        )

        response = self.client.post(
            reverse("chat_home"),
            {"action": "regenerate"},
            follow=True,
        )

        self.assertContains(response, "There is no previous user message")
        self.assertEqual(
            list(conversation.messages.values_list("content", flat=True)),
            ["PDF जोडली आहे."],
        )
        ask_ollama.assert_not_called()

    @patch("chatbot.views.requests.post")
    def test_ollama_prompt_requires_english_for_every_user_language(self, post):
        post.return_value.json.return_value = {
            "message": {"content": "Sure, here is a plan."},
        }

        answer = ask_ollama([
            {"role": "user", "content": "Mala abhyasache planning karun de"},
        ])

        system_prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertEqual(answer, "Sure, here is a plan.")
        self.assertIn(
            "Your default response language is English",
            system_prompt,
        )
        self.assertIn(
            "Continue answering in English even if earlier assistant messages",
            system_prompt,
        )
        self.assertIn(
            "Reminder: answer in English unless I explicitly request another language.",
            post.call_args.kwargs["json"]["messages"][-1]["content"],
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["options"]["temperature"],
            0.2,
        )

    def test_pdf_retrieval_returns_relevant_chunk(self):
        text = ("general reference words " * 100) + (
            "Local Django migrations update the database schema safely. " * 24
        ) + ("unrelated footer details " * 100)

        results = retrieve_relevant_pdf_chunks(
            text,
            "Django migrations database schema",
        )

        self.assertTrue(results)
        self.assertTrue(any("migrations" in chunk for chunk in results))
        self.assertLessEqual(len(results), 4)

    def test_markdown_rendering_sanitizes_script_tags(self):
        from chatbot.templatetags.chat_formatting import render_markdown

        result = str(
            render_markdown(
                "## Safe heading\n\n<script>alert(1)</script>\n\n"
                '<img src=x onerror="alert(1)">'
            )
        )

        self.assertIn("<h2>Safe heading</h2>", result)
        self.assertNotIn("<script>", result)
        self.assertNotIn("<img", result)
        self.assertNotIn("onerror", result)

    def test_markdown_formats_tables_and_highlighted_code(self):
        from chatbot.templatetags.chat_formatting import render_markdown

        result = str(
            render_markdown(
                "| Name | Value |\n| --- | --- |\n| answer | 42 |\n\n"
                "```python\nprint('hello')\n```"
            )
        )

        self.assertIn("<table>", result)
        self.assertIn('class="codehilite"', result)
        self.assertIn("print", result)

    def test_signup_claims_guest_chats_and_login_keeps_them(self):
        self.client.get(reverse("chat_home"))
        guest_chat = Conversation.objects.get()

        response = self.client.post(
            reverse("register"),
            {
                "username": "local-user",
                "password1": "A-secure-local-password-472!",
                "password2": "A-secure-local-password-472!",
            },
        )

        self.assertRedirects(response, reverse("chat_home"))
        guest_chat.refresh_from_db()
        self.assertEqual(guest_chat.user.username, "local-user")
        self.assertContains(self.client.get(reverse("chat_home")), "local-user")

    def test_logged_in_user_cannot_open_another_users_chat(self):
        owner = User.objects.create_user("owner", password="safe-password-123")
        other_chat = Conversation.objects.create(
            user=owner,
            title="Private chat",
        )
        self.client.force_login(User.objects.create_user("other", password="safe-password-123"))

        response = self.client.post(reverse("open_chat", args=[other_chat.id]))

        self.assertEqual(response.status_code, 404)

    @patch("chatbot.views.iter_ollama_response", return_value=iter(["Hello", " there."]))
    def test_streaming_endpoint_persists_complete_response(self, iter_response):
        response = self.client.post(
            reverse("stream_chat"),
            {"message": "Say hello", "model": "llama3.2:3b"},
        )

        events = b"".join(response.streaming_content).decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: token", events)
        self.assertIn("event: done", events)
        self.assertEqual(
            list(Message.objects.values_list("role", "content")),
            [("user", "Say hello"), ("assistant", "Hello there.")],
        )
        iter_response.assert_called_once()

    def test_uninstalled_model_is_rejected_without_saving_message(self):
        response = self.client.post(
            reverse("stream_chat"),
            {"message": "Use this model", "model": "not-installed"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Message.objects.exists())

    @patch("chatbot.views.iter_ollama_response", return_value=iter(["Image received."]))
    def test_streaming_image_is_validated_stored_and_sent_to_vision_model(self, iter_response):
        image_buffer = BytesIO()
        Image.new("RGB", (12, 12), color="blue").save(image_buffer, format="PNG")
        image_upload = SimpleUploadedFile(
            "sample.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("stream_chat"),
                    {
                        "message": "Describe this image",
                        "model": "llava:latest",
                        "images": image_upload,
                    },
                )
                b"".join(response.streaming_content)
                stored_image = Message.objects.get(role="user").images.get()
                self.assertTrue(stored_image.image.storage.exists(stored_image.image.name))

        self.assertEqual(response.status_code, 200)
        ollama_payload = iter_response.call_args.args[0]
        self.assertIn("images", ollama_payload["messages"][-1])
        self.assertEqual(ollama_payload["model"], "llava:latest")

    def test_rename_memory_export_and_continue_actions(self):
        self.client.get(reverse("chat_home"))
        conversation = Conversation.objects.get()
        Message.objects.create(conversation=conversation, role="user", content="A question")
        Message.objects.create(conversation=conversation, role="assistant", content="An answer")
        csrf_token = self.client.cookies["csrftoken"].value

        rename = self.client.post(
            reverse("update_conversation"),
            {"action": "rename", "title": "Research notes", "csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(rename.status_code, 200)
        memory = self.client.post(
            reverse("update_conversation"),
            {
                "action": "memory",
                "memory": "Prefer concise explanations",
                "csrfmiddlewaretoken": csrf_token,
            },
        )
        self.assertEqual(memory.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.memory, "Prefer concise explanations")

        export = self.client.get(reverse("export_chat", args=[conversation.id]))
        self.assertEqual(export.status_code, 200)
        self.assertIn(b"# Research notes", b"".join(export.streaming_content))

        continued = self.client.post(reverse("continue_chat", args=[conversation.id]))
        self.assertRedirects(continued, reverse("chat_home"))
        self.assertEqual(Conversation.objects.count(), 2)
        new_chat = Conversation.objects.exclude(id=conversation.id).get()
        self.assertEqual(new_chat.messages.count(), 2)
        self.assertEqual(new_chat.memory, "Prefer concise explanations")

    def test_ollama_models_endpoint_reports_installed_models(self):
        response = self.client.get(reverse("ollama_models"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["models"],
            ["llama3.2:3b", "llava:latest"],
        )
