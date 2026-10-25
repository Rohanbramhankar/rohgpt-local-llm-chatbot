from django.urls import path
from . import views


urlpatterns = [
    path("", views.chat_home, name="chat_home"),
    path("accounts/login/", views.RohGPTLoginView.as_view(), name="login"),
    path("accounts/logout/", views.RohGPTLogoutView.as_view(), name="logout"),
    path("accounts/register/", views.register, name="register"),

    # Multi chat
    path("new-chat/", views.new_chat, name="new_chat"),
    path("chat/<int:chat_id>/open/", views.open_chat, name="open_chat"),
    path("chat/<int:chat_id>/delete/", views.delete_chat, name="delete_chat"),
    path("chat/<int:chat_id>/export/", views.export_chat, name="export_chat"),
    path("chat/<int:chat_id>/continue/", views.continue_chat, name="continue_chat"),
    path("chat/update/", views.update_conversation, name="update_conversation"),
    path("chat/stream/", views.stream_chat, name="stream_chat"),
    path("chat/image/<int:image_id>/", views.chat_image, name="chat_image"),
    path("api/models/", views.ollama_models, name="ollama_models"),
    path("service-worker.js", views.service_worker, name="service_worker"),

    # PDF
    path("upload-pdf/", views.upload_pdf, name="upload_pdf"),
    path("remove-pdf/", views.remove_pdf, name="remove_pdf"),
]