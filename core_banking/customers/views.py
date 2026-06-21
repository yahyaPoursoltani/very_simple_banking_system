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
def app_aliveness_test(request):
    return HttpResponse("customer app is alive!!")
