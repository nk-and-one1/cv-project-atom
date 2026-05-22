"""load_transactions: category path + category_id, account filtering."""

from expense_tracker.analytics.pivot import load_transactions


def test_load_transactions_includes_category_id_and_path(add_tx):
    add_tx([
        {"date": "2026-04-10", "amount_base": -100.0, "merchant": "MAGNUM", "category_id": 2},     # Food > Groceries
        {"date": "2026-04-11", "amount_base": -50.0, "merchant": "MYSTERY", "category_id": None},  # Uncategorized
    ])
    df = load_transactions()
    assert "category_id" in df.columns  # regression: budget matching depends on it
    cats = set(df["category"])
    assert "Food > Groceries" in cats
    assert "Uncategorized" in cats


def test_load_transactions_account_filter(add_tx, add_account):
    add_tx([{"date": "2026-04-10", "amount_base": -100.0, "merchant": "X", "category_id": 2}])
    second = add_account(name="Second", number="ACC-2")
    add_tx([{"date": "2026-04-11", "amount_base": -200.0, "merchant": "Y", "category_id": 2}], account_id=second)

    assert len(load_transactions()) == 2
    only_second = load_transactions(account_ids=[second])
    assert len(only_second) == 1
    assert only_second.iloc[0]["amount_base"] == -200.0
