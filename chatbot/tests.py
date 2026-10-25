from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import Conversation, Message
from .views import ask_ollama


class ChatHomeTests(TestCase):
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
        ask_ollama.assert_called_once_with(
            [{"role": "user", "content": "नमस्कार"}],
            pdf_text="",
        )

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
        ask_ollama.assert_called_once_with(
            [{"role": "user", "content": "हा प्रश्न आहे"}],
            pdf_text="",
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
