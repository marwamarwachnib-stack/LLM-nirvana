import _soft_assert

def test_deposit_on_closed_account():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:0', pytest.raises(ValueError)):
        account.deposit(100)

def test_withdraw_on_closed_account():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:1', pytest.raises(ValueError)):
        account.withdraw(100)

def test_close_on_closed_account():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:2', pytest.raises(ValueError)):
        account.close()

def test_get_balance_on_closed_account():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:3', pytest.raises(ValueError)):
        account.get_balance()