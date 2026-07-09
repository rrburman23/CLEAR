class Payment:
    def calculate(self, amount):
        return amount


class DiscountPayment(Payment):
    def calculate(self, amount):
        return super().calculate(amount)


def final_price(payment, amount):
    return payment.calculate(amount)
