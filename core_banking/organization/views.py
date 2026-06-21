from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.db import connection, transaction
from django.contrib import messages


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_roles():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT role_id, role_name
            FROM role
            ORDER BY role_name
        """)
        return dictfetchall(cursor)


def bank_user_list(request):
    search = request.GET.get('search', '').strip()

    with connection.cursor() as cursor:
        base_sql = """
            SELECT
                u.user_id,
                u.username,
                u.fk_user_role,
                e.first_name,
                e.last_name,
                CONCAT(e.first_name, ' ', e.last_name) AS full_name,
                e.national_id,
                u.is_active,
                r.role_name
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.user_id
            LEFT JOIN role r ON r.role_id = u.fk_user_role
        """

        if search:
            sql = base_sql + """
                WHERE u.username LIKE %s
                   OR e.first_name LIKE %s
                   OR e.last_name LIKE %s
                   OR e.national_id LIKE %s
                   OR r.role_name LIKE %s
                ORDER BY u.user_id DESC
            """
            like_value = f"%{search}%"
            cursor.execute(sql, [like_value, like_value, like_value, like_value, like_value])
        else:
            sql = base_sql + " ORDER BY u.user_id DESC"
            cursor.execute(sql)

        users = dictfetchall(cursor)

    context = {
        'users': users,
        'search': search,
    }
    return render(request, 'organization/user_list.html', context)


def bank_user_create(request):
    roles = get_roles()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        fk_user_role = request.POST.get('fk_user_role', '').strip()
        is_active = 1 if request.POST.get('is_active') == '1' else 0

        user_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'national_id': national_id,
            'fk_user_role': int(fk_user_role) if fk_user_role.isdigit() else '',
            'is_active': is_active,
        }

        if not username or not first_name or not last_name or not national_id or not fk_user_role:
            messages.error(request, 'همه فیلدهای اجباری را تکمیل کنید.')
            return render(request, 'organization/user_form.html', {
                'form_mode': 'create',
                'roles': roles,
                'user_data': user_data,
            })

        # مقادیر پیش‌فرض برای ستون‌های اجباری که فعلاً در فرم نیستند
        password_hash = 'default_hash'  # بعداً باید با هش واقعی جایگزین شود
        is_headquarter = 0
        hire_date = '2024-01-01'
        salary = 0
        fk_employee_branch = 1  # باید branch_id معتبر باشد

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, is_active, fk_user_role)
                        VALUES (%s, %s, %s, %s)
                    """, [username, password_hash, is_active, fk_user_role])

                    new_user_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO employee (
                            employee_id,
                            first_name,
                            last_name,
                            national_id,
                            is_headquarter,
                            hire_date,
                            salary,
                            fk_employee_branch
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        new_user_id,
                        first_name,
                        last_name,
                        national_id,
                        is_headquarter,
                        hire_date,
                        salary,
                        fk_employee_branch,
                    ])

            messages.success(request, 'کاربر و کارمند جدید با موفقیت ایجاد شد.')
            return redirect('organization:bank_user_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد: {e}')
            return render(request, 'organization/user_form.html', {
                'form_mode': 'create',
                'roles': roles,
                'user_data': user_data,
            })

    return render(request, 'organization/user_form.html', {
        'form_mode': 'create',
        'roles': roles,
    })


def bank_user_edit(request, user_id):
    roles = get_roles()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                u.user_id,
                u.username,
                u.fk_user_role,
                e.first_name,
                e.last_name,
                e.national_id,
                u.is_active
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.user_id
            WHERE u.user_id = %s
        """, [user_id])
        rows = dictfetchall(cursor)

    if not rows:
        raise Http404("User not found")

    user_data = rows[0]

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        fk_user_role = request.POST.get('fk_user_role', '').strip()
        is_active = 1 if request.POST.get('is_active') == '1' else 0

        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'national_id': national_id,
            'fk_user_role': int(fk_user_role) if fk_user_role.isdigit() else '',
            'is_active': is_active,
        }

        if not username or not first_name or not last_name or not national_id or not fk_user_role:
            messages.error(request, 'همه فیلدهای اجباری را تکمیل کنید.')
            return render(request, 'organization/user_form.html', {
                'form_mode': 'edit',
                'roles': roles,
                'user_data': user_data,
            })

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users
                        SET username = %s, is_active = %s, fk_user_role = %s
                        WHERE user_id = %s
                    """, [username, is_active, fk_user_role, user_id])

                    cursor.execute("""
                        UPDATE employee
                        SET first_name = %s, last_name = %s, national_id = %s
                        WHERE employee_id = %s
                    """, [first_name, last_name, national_id, user_id])

            messages.success(request, 'ویرایش با موفقیت انجام شد.')
            return redirect('organization:bank_user_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش: {e}')

    return render(request, 'organization/user_form.html', {
        'form_mode': 'edit',
        'user_data': user_data,
        'roles': roles,
    })


def app_aliveness_test(request):
    return HttpResponse("organization app is alive!!")
