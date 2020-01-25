import datetime as dt

from enum import Enum


class Type(Enum):
    DirectDebit = 1
    Card = 2
    Unknown = 0


type_tuples = [
    ("PDIRECT DEBIT PAYMENT TO ", Type.DirectDebit),
    ("PCARD PAYMENT TO ", Type.Card)
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
        entity = self.description
        for type_prefix, _ in type_tuples:
            entity = entity.replace(
                type_prefix,
                ""
            )

        return entity.split(",")[0]

    @property
    def payment_type(self):
        for type_tuple in type_tuples:
            if self.description.startswith(
                    type_tuple[0]
            ):
                return type_tuple[1]
        return Type.Unknown


if __name__ == "__main__":
    with open("Statements09012927366132.qif") as f:
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

    for item in items:
        if item.payment_type == Type.Unknown:
            print(item.description)
