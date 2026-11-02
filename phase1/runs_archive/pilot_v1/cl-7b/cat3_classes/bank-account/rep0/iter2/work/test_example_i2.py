def test_bank_account_instantiation():
    account = BankAccount()
    assert account.is_open is False


def test_bank_account_open():
    account = BankAccount()
    account.open()
    assert account.is_open is True
    assert account.balance == 0


def test_bank_account_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.balance == 100


def test_bank_account_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    assert account.balance == 50


def test_bank_account_get_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.get_balance() == 100


def test_bank_account_close():
    account = BankAccount()
    account.open()
    account.close()
    assert account.is_open is False


def test_bank_account_open_error():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.open()


def test_bank_account_deposit_error():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(0)


def test_bank_account_withdraw_error():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(0)


def test_bank_account_get_balance_error():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_close_error():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.close()


def test_bank_account_open_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.open()


def test_bank_account_deposit_error_2():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.deposit(100)


def test_bank_account_withdraw_error_2():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.withdraw(100)


def test_bank_account_get_balance_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_close_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.close()


def test_bank_account_open_error_3():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.open()


def test_bank_account_deposit_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.deposit(100)


def test_bank_account_withdraw_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.withdraw(100)


def test_bank_account_get_balance_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_close_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with pytest.raises(ValueError):
        account.close()
