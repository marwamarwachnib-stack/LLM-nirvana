import _soft_assert

def test_bank_account_instantiation():
    account = BankAccount()
    try:
        _sa_v = account.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')

def test_bank_account_open():
    account = BankAccount()
    account.open()
    try:
        _sa_v = account.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = account.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')

def test_bank_account_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.balance == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:3', 'pass' if _sa_v else 'assertion')

def test_bank_account_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    try:
        _sa_v = account.balance == 50
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')

def test_bank_account_get_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.get_balance() == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')

def test_bank_account_close():
    account = BankAccount()
    account.open()
    account.close()
    try:
        _sa_v = account.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:6', 'pass' if _sa_v else 'assertion')

def test_bank_account_open_error():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:7', pytest.raises(ValueError)):
        account.open()

def test_bank_account_deposit_error():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:8', pytest.raises(ValueError)):
        account.deposit(0)

def test_bank_account_withdraw_error():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:9', pytest.raises(ValueError)):
        account.withdraw(0)

def test_bank_account_get_balance_error():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:10', pytest.raises(ValueError)):
        account.get_balance()

def test_bank_account_close_error():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:11', pytest.raises(ValueError)):
        account.close()

def test_bank_account_open_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:12', pytest.raises(ValueError)):
        account.open()

def test_bank_account_deposit_error_2():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:13', pytest.raises(ValueError)):
        account.deposit(100)

def test_bank_account_withdraw_error_2():
    account = BankAccount()
    with _soft_assert.raises('test_example_i2:14', pytest.raises(ValueError)):
        account.withdraw(100)

def test_bank_account_get_balance_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:15', pytest.raises(ValueError)):
        account.get_balance()

def test_bank_account_close_error_2():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:16', pytest.raises(ValueError)):
        account.close()

def test_bank_account_open_error_3():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:17', pytest.raises(ValueError)):
        account.open()

def test_bank_account_deposit_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:18', pytest.raises(ValueError)):
        account.deposit(100)

def test_bank_account_withdraw_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:19', pytest.raises(ValueError)):
        account.withdraw(100)

def test_bank_account_get_balance_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:20', pytest.raises(ValueError)):
        account.get_balance()

def test_bank_account_close_error_3():
    account = BankAccount()
    account.open()
    account.close()
    with _soft_assert.raises('test_example_i2:21', pytest.raises(ValueError)):
        account.close()