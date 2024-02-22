from expression_parser.formula import Formula

if __name__ == '__main__':
    f1 = Formula("(m*v^2)/2")
    f1.set_variables({
        "m": 1.5,
        "v": 0.36
    })
    r1 = f1.calculate_result()
    t1 = (1.5 * 0.36 ** 2) / 2
    print(t1 == r1, r1, t1)

    f2 = Formula("N0*2**()-t/T)")
    print(f2.error_text)
    print(f2.calculate_result())

    f2 = Formula("N0*2**(-t/T)")
    f2.set_variables({
        "N0": 1
    })
    r2 = f2.calculate_result()
    print(r2, f2.error_text)

    f2.set_variables({
        "N0": 1,
        "t": 2,
        "T": 5
    })
    r2 = f2.calculate_result()
    print(r2, f2.error_text)

    f3 = Formula("abs(a) + sqrt(b)")
    f3.set_variables({
        "a": -2,
        "b": 4
    })
    print(f3.calculate_result(), 4)
