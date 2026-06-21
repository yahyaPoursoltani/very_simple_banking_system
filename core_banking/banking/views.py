from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import connection, transaction
from django.contrib import messages


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def app_aliveness_test(request):
    return HttpResponse("banking app is alive!!")


def get_active_accounts():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                a.account_id,
                a.account_number,
                a.balance,
                a.status,
                a.customer_id,
                CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                c.national_id
            FROM account a
            INNER JOIN customer c ON c.customer_id = a.customer_id
            WHERE a.status = 1
            ORDER BY a.account_number
        """)
        return dictfetchall(cursor)


def get_transaction_type_id(keyword):
    """
    تلاش برای پیدا کردن نوع تراکنش از جدول transactiontype.
    اگر ساختار جدول transactiontype در دیتابیس شما فقط id داشته باشد
    یا ستون نام آن مشخص نباشد، از fallback استفاده می‌کنیم.
    """
    with connection.cursor() as cursor:
        # تلاش اول: اگر ستونی مثل title / name / type_name وجود داشته باشد، این روش شاید جواب دهد
        possible_columns = [
            'transaction_type_name',
            'type_name',
            'name',
            'title',
            'description'
        ]

        for col in possible_columns:
            try:
                cursor.execute(f"""
                    SELECT transaction_type_id
                    FROM transactiontype
                    WHERE LOWER({col}) LIKE %s
                    LIMIT 1
                """, [f"%{keyword.lower()}%"])
                row = cursor.fetchone()
                if row:
                    return row[0]
            except Exception:
                continue

    # fallback
    fallback_map = {
        'deposit': 1,
        'withdraw': 2,
        'transfer': 3,
    }
    return fallback_map.get(keyword)


def get_next_transaction_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(transaction_id), 0) + 1 FROM bank_transaction")
        return cursor.fetchone()[0]


def get_account_by_number(account_number):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                account_id,
                account_number,
                balance,
                status,
                customer_id
            FROM account
            WHERE account_number = %s
            LIMIT 1
        """, [account_number])
        row = cursor.fetchone()
        if not row:
            return None
        return {
            'account_id': row[0],
            'account_number': row[1],
            'balance': row[2],
            'status': row[3],
            'customer_id': row[4],
        }


def create_transaction_record(account_id, amount, description, transaction_type_id, status=1):
    with connection.cursor() as cursor:
        new_id = get_next_transaction_id()
        cursor.execute("""
            INSERT INTO bank_transaction (
                transaction_id,
                description,
                amount,
                transaction_date,
                status,
                fk_transaction_account,
                fk_transaction_transactiontype
            )
            VALUES (%s, %s, %s, NOW(), %s, %s, %s)
        """, [
            new_id,
            description,
            str(amount),
            status,
            account_id,
            transaction_type_id,
        ])


def transaction_list(request):
    search = request.GET.get('search', '').strip()

    with connection.cursor() as cursor:
        base_sql = """
            SELECT
                bt.transaction_id,
                bt.description,
                bt.amount,
                bt.transaction_date,
                bt.status,
                bt.fk_transaction_account,
                bt.fk_transaction_transactiontype,
                a.account_number,
                CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                c.national_id
            FROM bank_transaction bt
            INNER JOIN account a ON a.account_id = bt.fk_transaction_account
            INNER JOIN customer c ON c.customer_id = a.customer_id
        """

        if search:
            sql = base_sql + """
                WHERE a.account_number LIKE %s
                   OR c.first_name LIKE %s
                   OR c.last_name LIKE %s
                   OR c.national_id LIKE %s
                   OR bt.description LIKE %s
                ORDER BY bt.transaction_id DESC
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
            sql = base_sql + " ORDER BY bt.transaction_id DESC"
            cursor.execute(sql)

        transactions = dictfetchall(cursor)

    return render(request, 'banking/transaction_list.html', {
        'transactions': transactions,
        'search': search,
    })


def deposit_create(request):
    accounts = get_active_accounts()

    if request.method == 'POST':
        account_number = request.POST.get('account_number', '').strip()
        amount = request.POST.get('amount', '').strip()
        description = request.POST.get('description', '').strip()

        if not account_number or not amount:
            messages.error(request, 'شماره حساب و مبلغ الزامی هستند.')
            return render(request, 'banking/deposit_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValueError('amount must be positive')
        except Exception:
            messages.error(request, 'مبلغ واریز نامعتبر است.')
            return render(request, 'banking/deposit_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        account = get_account_by_number(account_number)
        if not account:
            messages.error(request, 'حساب مورد نظر یافت نشد.')
            return render(request, 'banking/deposit_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if account['status'] != 1:
            messages.error(request, 'فقط حساب فعال امکان انجام عملیات دارد.')
            return render(request, 'banking/deposit_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE account
                        SET balance = COALESCE(balance, 0) + %s
                        WHERE account_id = %s
                    """, [amount_int, account['account_id']])

                tx_type_id = get_transaction_type_id('deposit')
                create_transaction_record(
                    account['account_id'],
                    amount_int,
                    description if description else 'واریز وجه',
                    tx_type_id
                )

            messages.success(request, 'واریز وجه با موفقیت انجام شد.')
            return redirect('transaction_list')

        except Exception as e:
            messages.error(request, f'خطا در انجام واریز: {e}')

    return render(request, 'banking/deposit_form.html', {
        'accounts': accounts,
        'form_data': {},
    })


def withdraw_create(request):
    accounts = get_active_accounts()

    if request.method == 'POST':
        account_number = request.POST.get('account_number', '').strip()
        amount = request.POST.get('amount', '').strip()
        description = request.POST.get('description', '').strip()

        if not account_number or not amount:
            messages.error(request, 'شماره حساب و مبلغ الزامی هستند.')
            return render(request, 'banking/withdraw_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValueError('amount must be positive')
        except Exception:
            messages.error(request, 'مبلغ برداشت نامعتبر است.')
            return render(request, 'banking/withdraw_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        account = get_account_by_number(account_number)
        if not account:
            messages.error(request, 'حساب مورد نظر یافت نشد.')
            return render(request, 'banking/withdraw_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if account['status'] != 1:
            messages.error(request, 'فقط حساب فعال امکان انجام عملیات دارد.')
            return render(request, 'banking/withdraw_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        current_balance = int(account['balance'] or 0)
        if current_balance < amount_int:
            messages.error(request, 'موجودی حساب کافی نیست.')
            return render(request, 'banking/withdraw_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE account
                        SET balance = COALESCE(balance, 0) - %s
                        WHERE account_id = %s
                    """, [amount_int, account['account_id']])

                tx_type_id = get_transaction_type_id('withdraw')
                create_transaction_record(
                    account['account_id'],
                    amount_int,
                    description if description else 'برداشت وجه',
                    tx_type_id
                )

            messages.success(request, 'برداشت وجه با موفقیت انجام شد.')
            return redirect('transaction_list')

        except Exception as e:
            messages.error(request, f'خطا در انجام برداشت: {e}')

    return render(request, 'banking/withdraw_form.html', {
        'accounts': accounts,
        'form_data': {},
    })

def transfer_create(request):
    accounts = get_active_accounts()

    if request.method == 'POST':
        from_account_number = request.POST.get('from_account_number', '').strip()
        to_account_number = request.POST.get('to_account_number', '').strip()
        amount = request.POST.get('amount', '').strip()
        description = request.POST.get('description', '').strip()

        if not from_account_number or not to_account_number or not amount:
            messages.error(request, 'حساب مبدا، حساب مقصد و مبلغ الزامی هستند.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if from_account_number == to_account_number:
            messages.error(request, 'حساب مبدا و مقصد نمی‌توانند یکسان باشند.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValueError()
        except Exception:
            messages.error(request, 'مبلغ انتقال نامعتبر است.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        from_account = get_account_by_number(from_account_number)
        to_account = get_account_by_number(to_account_number)

        if not from_account:
            messages.error(request, 'حساب مبدا یافت نشد.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if not to_account:
            messages.error(request, 'حساب مقصد یافت نشد.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if from_account['status'] != 1:
            messages.error(request, 'حساب مبدا فعال نیست.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        if to_account['status'] != 1:
            messages.error(request, 'حساب مقصد فعال نیست.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        from_balance = int(from_account['balance'] or 0)
        if from_balance < amount_int:
            messages.error(request, 'موجودی حساب مبدا کافی نیست.')
            return render(request, 'banking/transfer_form.html', {
                'accounts': accounts,
                'form_data': request.POST,
            })

        transfer_type_id = get_transaction_type_id('transfer')
        withdraw_type_id = get_transaction_type_id('withdraw')
        deposit_type_id = get_transaction_type_id('deposit')

        # اگر type انتقال تعریف نشده بود، از typeهای برداشت/واریز استفاده می‌کنیم
        from_type_id = transfer_type_id or withdraw_type_id
        to_type_id = transfer_type_id or deposit_type_id

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # برداشت از حساب مبدا
                    cursor.execute("""
                        UPDATE account
                        SET balance = COALESCE(balance, 0) - %s
                        WHERE account_id = %s
                    """, [amount_int, from_account['account_id']])

                    # واریز به حساب مقصد
                    cursor.execute("""
                        UPDATE account
                        SET balance = COALESCE(balance, 0) + %s
                        WHERE account_id = %s
                    """, [amount_int, to_account['account_id']])

                from_description = description.strip() if description.strip() else (
                    f'انتقال وجه از حساب {from_account_number} به حساب {to_account_number}'
                )

                to_description = description.strip() if description.strip() else (
                    f'دریافت وجه از حساب {from_account_number} به حساب {to_account_number}'
                )

                # ثبت تراکنش برای حساب مبدا
                create_transaction_record(
                    from_account['account_id'],
                    amount_int,
                    from_description,
                    from_type_id
                )

                # ثبت تراکنش برای حساب مقصد
                create_transaction_record(
                    to_account['account_id'],
                    amount_int,
                    to_description,
                    to_type_id
                )

            messages.success(request, 'انتقال وجه با موفقیت انجام شد.')
            return redirect('transaction_list')

        except Exception as e:
            messages.error(request, f'خطا در انجام انتقال وجه: {e}')

    return render(request, 'banking/transfer_form.html', {
        'accounts': accounts,
        'form_data': {},
    })

