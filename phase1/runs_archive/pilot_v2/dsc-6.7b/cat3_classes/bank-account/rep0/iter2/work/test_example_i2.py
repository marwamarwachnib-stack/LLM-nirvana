from example import *
def test_deposit_zero():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(0)

def test_deposit_negative():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(-100)

def test_withdraw_zero():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(0)

def test_withdraw_negative():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(-100)

def test_withdraw_more_than_balance():
    account = BankAccount()
    account.open()
    account.deposit(50)
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_multiple_threads():
    account = BankAccount()
    account.open()

    def deposit():
        for _ in range(10000):
            account.deposit(1)

    def withdraw():
        for _ in range(10000):
            account.withdraw(1)

    t1 = threading.Thread(target=deposit)
    t2 = threading.Thread(target=withdraw)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert account.balance == 0
