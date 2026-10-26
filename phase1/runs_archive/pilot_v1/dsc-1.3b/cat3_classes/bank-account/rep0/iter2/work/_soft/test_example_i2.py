import _soft_assert

def test_cannot_deposit_non_numeric_amount():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:0', pytest.raises(ValueError)):
        account.deposit('abc')

def test_cannot_withdraw_non_numeric_amount():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with _soft_assert.raises('test_example_i2:1', pytest.raises(ValueError)):
        account.withdraw('abc')

def test_cannot_close_already_closed_account():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:2', pytest.raises(ValueError)):
        account.close()

def test_cannot_get_balance_on_closed_account():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:3', pytest.raises(ValueError)):
        account.get_balance()

def test_cannot_withdraw_more_than_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with _soft_assert.raises('test_example_i2:4', pytest.raises(ValueError)):
        account.withdraw(150)

def test_cannot_withdraw_negative_amount():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with _soft_assert.raises('test_example_i2:5', pytest.raises(ValueError)):
        account.withdraw(-100)

def test_cannot_deposit_negative_amount():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:6', pytest.raises(ValueError)):
        account.deposit(-100)