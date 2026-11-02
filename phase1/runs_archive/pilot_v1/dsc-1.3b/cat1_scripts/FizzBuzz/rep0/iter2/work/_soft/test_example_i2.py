import _soft_assert

def test_fizzbuzz():
    with _soft_assert.raises('test_example_i2:1', pytest.raises(SystemExit)):
        sys.stdout = StringIO()
        num = [1, 3, 5]
        fizzbuzz(num)
        output = sys.stdout.getvalue().strip()
        try:
            _sa_v = output == '1\n2Fizz\n3FizzBuzz\n5'
        except AssertionError as _sa_e:
            _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
        except Exception as _sa_e:
            _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
        else:
            _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i2:3', pytest.raises(SystemExit)):
        sys.stdout = StringIO()
        num = [0, 0, 0]
        fizzbuzz(num)
        output = sys.stdout.getvalue().strip()
        try:
            _sa_v = output == '12Fizz'
        except AssertionError as _sa_e:
            _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
        except Exception as _sa_e:
            _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
        else:
            _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')
    sys.stdout = StringIO()
    num = [1, 2, 15]
    fizzbuzz(num)
    output = sys.stdout.getvalue().strip()
    try:
        _sa_v = output == '1\n2\nFizz\n3\n4\nBuzz\n5\n6\n7\n8\nFizz\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20\n21\n22\n23\n24\n25\n26\n27\n28\n29\n30\n31\n32\n33\n34\n35\n36\n37\n38\n39\n40\n41\n42\n43\n44\n45\n46\n47\n48\n49\n50\n51\n52\n53\n54\n55\n56\n57\n58\n59\n60\n61\n62\n63\n64\n65\n66\n67\n68\n69\n70\n71\n72\n73\n74\n75\n76\n77\n78\n79\n80\n81\n82\n83\n84\n85\n86\n87\n88\n89\n90\n91\n92\n93\n94\n95\n96\n97\n98\n99\n100'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')
    sys.stdout = StringIO()
    num = [-1, -2, -5]
    fizzbuzz(num)
    output = sys.stdout.getvalue().strip()
    try:
        _sa_v = output == '-1\n-2\n-5'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')
    sys.stdout = StringIO()
    num = [1, 2, 100]
    fizzbuzz(num)
    output = sys.stdout.getvalue().strip()
    try:
        _sa_v = output == '1\n2\nFizz\n3\n4\nBuzz\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20\n21\n22\n23\n24\n25\n26\n27\n28\n29\n30\n31\n32\n33\n34\n35\n36\n37\n38\n39\n40\n41\n42\n43\n44\n45\n46\n47\n48\n49\n50\n51\n52\n53\n54\n55\n56\n57\n58\n59\n60\n61\n62\n63\n64\n65\n66\n67\n68\n69\n70\n71\n72\n73\n74\n75\n76\n77\n78\n79\n80\n81\n82\n83\n84\n85\n86\n87\n88\n89\n90\n91\n92\n93\n94\n95\n96\n97\n98\n99\n100'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:6', 'pass' if _sa_v else 'assertion')