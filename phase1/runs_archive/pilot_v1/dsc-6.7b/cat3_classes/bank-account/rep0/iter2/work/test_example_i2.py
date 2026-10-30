def test_deposit_on_closed_account():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.deposit(100)

def test_withdraw_on_closed_account():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_close_on_closed_account():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.close()

def test_get_balance_on_closed_account():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.get_balance()
