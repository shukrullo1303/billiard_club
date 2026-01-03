# myproject/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class AdminLoginRequiredMiddleware:
    """
    Butun sayt faqat superuser/login qilingan adminlar uchun.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Admin panel va static fayllar ruxsat berilsin
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return self.get_response(request)

        # Agar foydalanuvchi login qilmagan yoki superuser bo'lmasa
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect(reverse('admin:login'))

        return self.get_response(request)
