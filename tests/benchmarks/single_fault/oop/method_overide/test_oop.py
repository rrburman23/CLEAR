import pytest
from target import DiscountPayment, final_price


def test_discount_calculation() -> None:
    p = DiscountPayment()
    # Assuming 20% discount
    assert final_price(p, 100) == 80


def test_zero_amount() -> None:
    p = DiscountPayment()
    assert final_price(p, 0) == 0


def test_discount_instance() -> None:
    p = DiscountPayment()
    assert isinstance(final_price(p, 100), (int, float))
