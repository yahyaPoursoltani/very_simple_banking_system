from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_cities():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT city_id, city_name
            FROM city
            ORDER BY city_name
        """)
        return dictfetchall(cursor)


def get_customers():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                customer_id,
                first_name,
                last_name,
                CONCAT(first_name, ' ', last_name) AS full_name,
                national_id
            FROM customer
            ORDER BY first_name, last_name
        """)
        return dictfetchall(cursor)


def get_account_types():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM accounttype
            ORDER BY account_type_id
        """)
        return dictfetchall(cursor)


def customer_create(request):
    cities = get_cities()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        fk_customer_city = request.POST.get('fk_customer_city', '').strip()

        if not first_name or not last_name or not national_id or not phone_number or not address or not fk_customer_city:
            messages.error(request, 'لطفاً همه فیلدهای الزامی را تکمیل کنید.')
            return render(request, 'customers/customer_form.html', {
                'cities': cities,
                'form_data': request.POST,
                'is_edit': False,
            })

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(customer_id), 0) + 1 FROM customer")
                new_customer_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO customer (
                        customer_id,
                        first_name,
                        last_name,
                        national_id,
                        phone_number,
                        email,
                        address,
                        sign_up,
                        fk_customer_city
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """, [
                    new_customer_id,
                    first_name,
                    last_name,
                    national_id,
                    phone_number,
                    email if email else None,
                    address,
                    fk_customer_city,
                ])

            messages.success(request, 'مشتری با موفقیت ثبت شد.')
            return redirect('customer_list')

        except Exception as e:
            messages.error(request, f'خطا در ثبت مشتری: {e}')
            return render(request, 'customers/customer_form.html', {
                'cities': cities,
                'form_data': request.POST,
                'is_edit': False,
            })

    return render(request, 'customers/customer_form.html', {
        'cities': cities,
        'form_data': {},
        'is_edit': False,
    })


def customer_list(request):
    search = request.GET.get('search', '').strip()

    with connection.cursor() as cursor:
        base_sql = """
            SELECT
                c.customer_id,
                c.first_name,
                c.last_name,
                CONCAT(c.first_name, ' ', c.last_name) AS full_name,
                c.national_id,
                c.phone_number,
                c.email,
                c.address,
                c.sign_up,
                c.fk_customer_city,
                ci.city_name
            FROM customer c
            LEFT JOIN city ci ON ci.city_id = c.fk_customer_city
        """

        if search:
            sql = base_sql + """
                WHERE c.first_name LIKE %s
                   OR c.last_name LIKE %s
                   OR c.national_id LIKE %s
                   OR c.phone_number LIKE %s
                   OR c.email LIKE %s
                   OR ci.city_name LIKE %s
                ORDER BY c.customer_id DESC
            """
            like_value = f"%{search}%"
            cursor.execute(sql, [
                like_value,
                like_value,
                like_value,
                like_value,
                like_value,
                like_value,
            ])
        else:
            sql = base_sql + " ORDER BY c.customer_id DESC"
            cursor.execute(sql)

        customers = dictfetchall(cursor)

    return render(request, 'customers/customer_list.html', {
        'customers': customers,
        'search': search,
    })


def account_list(request):
    search = request.GET.get('search', '').strip()

    with connection.cursor() as cursor:
        base_sql = """
            SELECT
                a.account_id,
                a.account_number,
                a.balance,
                a.open_date,
                a.status,
                a.customer_id,
                a.fk_account_product,
                a.fk_account_accounttype,
                CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                c.national_id,
                at.account_type_id
            FROM account a
            LEFT JOIN customer c ON c.customer_id = a.customer_id
            LEFT JOIN accounttype at ON at.account_type_id = a.fk_account_accounttype
        """

        if search:
            sql = base_sql + """
                WHERE a.account_number LIKE %s
                   OR c.first_name LIKE %s
                   OR c.last_name LIKE %s
                   OR c.national_id LIKE %s
                   OR CAST(at.account_type_id AS CHAR) LIKE %s
                ORDER BY a.account_id DESC
            """
            like_value = f"%{search}%"
            cursor.execute(sql, [
                like_value,
                like_value,
                like_value,
                like_value,
                like_value,
            ])
        else:
            sql = base_sql + " ORDER BY a.account_id DESC"
            cursor.execute(sql)

        accounts = dictfetchall(cursor)

    return render(request, 'customers/account_list.html', {
        'accounts': accounts,
        'search': search,
    })


def account_create(request):
    customers = get_customers()
    account_types = get_account_types()

    if request.method == 'POST':
        account_number = request.POST.get('account_number', '').strip()
        balance = request.POST.get('balance', '').strip()
        status = request.POST.get('status', '').strip()
        customer_id = request.POST.get('customer_id', '').strip()
        fk_account_accounttype = request.POST.get('fk_account_accounttype', '').strip()

        if not account_number or not balance or not status or not customer_id or not fk_account_accounttype:
            messages.error(request, 'لطفاً همه فیلدهای الزامی را تکمیل کنید.')
            return render(request, 'customers/account_form.html', {
                'customers': customers,
                'account_types': account_types,
                'form_data': request.POST,
            })

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(account_id), 0) + 1 FROM account")
                new_account_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO account (
                        account_id,
                        account_number,
                        balance,
                        open_date,
                        status,
                        customer_id,
                        fk_account_product,
                        fk_account_accounttype
                    )
                    VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s)
                """, [
                    new_account_id,
                    account_number,
                    balance,
                    status,
                    customer_id,
                    1,
                    fk_account_accounttype,
                ])

            messages.success(request, 'حساب با موفقیت افتتاح شد.')
            return redirect('account_list')

        except Exception as e:
            messages.error(request, f'خطا در افتتاح حساب: {e}')
            return render(request, 'customers/account_form.html', {
                'customers': customers,
                'account_types': account_types,
                'form_data': request.POST,
            })

    return render(request, 'customers/account_form.html', {
        'customers': customers,
        'account_types': account_types,
        'form_data': {},
    })


def app_aliveness_test(request):
    return HttpResponse("customer app is alive!!")
