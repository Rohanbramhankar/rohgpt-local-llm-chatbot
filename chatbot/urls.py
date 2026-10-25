from django.urls import path

from . import views


urlpatterns = [
    path("", views.chat_home, name="chat_home"),

    # Multi chat
    path("new-chat/", views.new_chat, name="new_chat"),
    path("chat/<int:chat_id>/open/", views.open_chat, name="open_chat"),
    path("chat/<int:chat_id>/delete/", views.delete_chat, name="delete_chat"),

    # PDF
    path("upload-pdf/", views.upload_pdf, name="upload_pdf"),
    path("remove-pdf/", views.remove_pdf, name="remove_pdf"),
]