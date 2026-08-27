"""
Sample 1 — simple Python code with a basic code-quality issue.

Intentional issue: a mutable default argument (`items=[]`), which is a
classic Python pitfall — the same list object is reused and mutated
across every call that doesn't pass its own `items`.
"""


def add_item(item, items=[]):
    items.append(item)
    return items


def summarize(cart):
    total = 0
    for price in cart:
        total += price
    return total


if __name__ == "__main__":
    cart = add_item(9.99)
    cart = add_item(4.50, cart)
    print("Total:", summarize(cart))
