import datetime as dt


def simple_operation(description_string):
    return description_string.split(",")[0]


class PaymentType:
    def __init__(
            self,
            prefix="PDIRECT DEBIT PAYMENT TO ",
            operation=simple_operation
    ):
        self.prefix = prefix
        self.operation = operation

    def matches(self, description_string):
        return description_string.startswith(
            self.prefix
        )

    def __call__(self, description_string):
        return self.operation(
            description_string.replace(
                self.prefix,
                ""
            )
        )


payment_types = [
    PaymentType("PDIRECT DEBIT PAYMENT TO "),
    PaymentType("PCARD PAYMENT TO "),
    PaymentType(
        "PINTEREST PAID AFTER TAX 0.00 DEDUCTED",
        lambda _: "INTEREST"
    )
]


class Item:
    def __init__(
            self,
            date,
            amount,
            description
    ):
        self.date = date
        self.amount = amount
        self.description = description

    @classmethod
    def from_array(
            cls,
            array
    ):
        date_string = array[1]
        amount_string = array[2]
        description = array[3]
        return Item(
            dt.datetime.strptime(
                date_string,
                "D%d/%m/%Y"
            ),
            float(amount_string[1:]),
            description
        )

    def __str__(self):
        return self.description

    def __repr__(self):
        return f"<{self.__class__.__name__} {str(self)}>"

    @property
    def entity(self):
        try:
            return self.payment_type(
                self.description
            )
        except TypeError:
            return self.description

    @property
    def payment_type(self):
        for payment_type in payment_types:
            if payment_type.matches(
                    self.description
            ):
                return payment_type
        raise TypeError(
            "Unrecognised payment type"
        )


class Account:
    def __init__(
            self,
            items
    ):
        self.items = items

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __str__(self):
        return str(self.items)

    @property
    def entities(self):
        return {
            item.entity
            for item
            in self.items
        }

    @property
    def expenses(self):
        return Account(
            [
                item
                for item in self.items
                if item.amount <= 0
            ]
        )

    @property
    def profits(self):
        return Account(
            [
                item
                for item in self.items
                if item.amount > 0
            ]
        )

    @classmethod
    def load(cls, filename):
        with open(filename) as f:
            string = f.read()

        item_strings = string.split("^")
        items = []

        for item_string in item_strings:
            item_array = item_string.split("\n")
            try:
                items.append(
                    Item.from_array(
                        item_array
                    )
                )
            except IndexError:
                pass

        return Account(items)

    def filter(self, **kwargs):
        return Account([
            item for item
            in self.items
            if all([
                getattr(item, key) == value
                for key, value in kwargs.items()
            ])
        ])

    @property
    def total(self):
        return sum([
            item.amount
            for item in self
        ])


if __name__ == "__main__":
    account = Account.load("Statements09012927366132.qif")

    bagels = account.filter(
        entity="BAGELMANIA"
    )
    print(bagels.total)
