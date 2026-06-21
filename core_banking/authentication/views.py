from django.shortcuts import render, redirect
from django.db import connection
from django.http import HttpResponse


def login_view(request):

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    u.user_id,
                    u.username,
                    u.password_hash,
                    u.is_active,
                    COALESCE(r.role_name, 'بدون نقش') AS role_name
                FROM users u
                LEFT JOIN role r ON u.fk_user_role = r.role_id
                WHERE u.username = %s
                LIMIT 1
            """, [username])

            user_data = cursor.fetchone()

        if user_data is None:
            return render(request, "login.html", {"error": "کاربری با این نام وجود ندارد."})

        user_id, db_username, db_password_hash, is_active, role_name = user_data

        # بررسی فعال بودن حساب کاربری
        if not is_active:
            return render(request, "login.html", {"error": "این حساب کاربری غیرفعال شده است."})

        # مقایسه رمز عبور (در حال حاضر Plain Text طبق دیتای نمونه)
        if password == db_password_hash:
            # ذخیره اطلاعات کلیدی در Session
            request.session["user_id"] = user_id
            request.session["username"] = db_username
            request.session["role"] = role_name
            request.session["full_name"] = db_username  # چون نام مجزا نداریم، یوزرنیم را به عنوان نمایش قرار می‌دهیم

            # ثبت قطعی Session در دیتابیس
            request.session.modified = True
            request.session.save()

            print(f"--- [Login Success] User: {db_username} | Role: {role_name} ---")
            return redirect("/")
        else:
            return render(request, "login.html", {"error": "رمز عبور اشتباه است."})

    return render(request, "login.html")


def profile_view(request):
    """
    نمایش مشخصات امنیتی و عمومی کاربر لاگین‌شده از جدول users و role.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("/auth/login/")  # اگر لاگین نکرده بود هدایت شود به صفحه لاگین

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.is_active,
                u.created_at,
                COALESCE(r.role_name, 'نامشخص') AS role_name
            FROM users u
            LEFT JOIN role r ON u.fk_user_role = r.role_id
            WHERE u.user_id = %s
            LIMIT 1
        """, [user_id])

        row = cursor.fetchone()

    # اگر کاربر در دیتابیس نبود (مثلاً حذف شده بود ولی سشن هنوز باقی مانده بود)
    if not row:
        request.session.flush()  # پاکسازی سشن نامعتبر
        return redirect("/auth/login/")

    # آماده‌سازی کانتکست جهت ارسال به تمپلیت جدید
    context = {
        "profile": {
            "user_id": row[0],
            "username": row[1],
            "is_active": bool(row[2]),
            "created_at": row[3],
            "role_name": row[4],
        }
    }
    return render(request, "profile.html", context)


def logout_view(request):
    """
    خروج کاربر و پاکسازی سشن‌ها.
    """
    request.session.flush()
    return redirect("/auth/login/")
