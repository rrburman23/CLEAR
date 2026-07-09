from target import DiscountPayment, final_price


def test_discount():
    p = DiscountPayment()

    assert final_price(p, 100) == 80
