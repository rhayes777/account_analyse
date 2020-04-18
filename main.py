import csv
import datetime as dt
import json
from hashlib import sha256


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


class Category:
    def __init__(self, name, is_included, entities=None):
        self.name = name
        self.entities = set(entities or {})
        self.is_included = is_included

    @property
    def dict(self):
        return {
            "name": self.name,
            "entities": list(map(str, self.entities)),
            "is_included": self.is_included
        }

    @classmethod
    def from_dict(cls, category_dict):
        return Category(
            name=category_dict["name"],
            is_included=category_dict["is_included"],
            entities=category_dict["entities"]
        )

    def __str__(self):
        return self.name


class Entity:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__} {str(self)}>"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name

    def __iter__(self):
        return iter(self.name)

    def __getitem__(self, item):
        return self.name[item]


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

    def row(self):
        return [
            self.date.strftime(
                "%Y-%d-%m"
            ),
            abs(self.amount)
        ]

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

    def __gt__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        return self.date < other.date

    @property
    def entity(self):
        try:
            return Entity(
                self.payment_type(
                    self.description
                )
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

    @property
    def id(self):
        return sha256(f"{self.date}:{self.description}:{self.amount}".encode("utf-8")).hexdigest()


class Account:
    def __init__(
            self,
            items,
            categories=None
    ):
        self.items = sorted(items)
        self.categories = categories or list()

    @property
    def categorised_entities(self):
        entities = set()
        for category in self.categories:
            entities.update(
                category.entities
            )
        return entities

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __str__(self):
        return str(self.items)

    def write_csv(self, filename):
        with open(filename, "w+") as f:
            writer = csv.writer(f)
            for item in self:
                writer.writerow(
                    item.row()
                )

    @property
    def entities(self):
        return {
            item.entity
            for item
            in self
        }

    def items_for_entity(self, entity):
        for item in self:
            if item.entity == entity:
                yield item

    @property
    def expenses(self):
        return Account(
            [
                item
                for item in self
                if item.amount <= 0
            ]
        )

    @property
    def profits(self):
        return Account(
            [
                item
                for item in self
                if item.amount > 0
            ]
        )

    @classmethod
    def load(cls, filename):
        with open(f"{filename}.qif") as f:
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

        try:
            with open(f"{filename}_categories.json") as f:
                categories = list(map(
                    Category.from_dict,
                    json.load(f)
                ))
        except FileNotFoundError:
            print("Categories file not found")
            categories = list()

        return Account(items, categories)

    def save_categories(self, filename):
        with open(f"{filename}_categories.json", "w+") as f:
            json.dump(
                [
                    category.dict
                    for category
                    in self.categories
                ],
                f
            )

    def filter(self, **kwargs):
        return Account([
            item for item
            in self
            if all([
                getattr(item, key) == value
                for key, value in kwargs.items()
            ])
        ])

    def filter_contains(self, **kwargs):
        return Account([
            item for item
            in self
            if all([
                value in getattr(item, key)
                for key, value in kwargs.items()
            ])
        ])

    @property
    def total(self):
        return sum([
            item.amount
            for item in self
        ])


def sort_expenses(account_name):
    account = Account.load(account_name)

    for entity in account.expenses.entities:
        if entity in account.categorised_entities:
            continue
        print(entity)
        print("1) New category")
        for i, category in enumerate(account.categories):
            print(f"{i + 2}) {category}")
        value = int(input())
        if value == 1:
            name = input(
                "Enter a name for the new category "
            )
            is_included = "y" in input(
                "Should entities in this category be included (y/n)? "
            )
            account.categories.append(
                Category(
                    name=name,
                    is_included=is_included
                )
            )
        account.categories[value - 2].entities.add(
            entity
        )
        account.save_categories(
            account_name
        )

    with open("expenses.csv", "w+") as f:
        writer = csv.writer(f)
        for category in account.categories:
            if category.is_included:
                for entity in category.entities:
                    for item in account.expenses.items_for_entity(
                            entity
                    ):
                        writer.writerow(item.row() + [category.name])


if __name__ == "__main__":
    sort_expenses("Statements09012927366132")
