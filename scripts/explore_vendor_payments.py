from pathlib import Path

import pandas as pd


CSV_PATH = Path(__file__).resolve().parents[1] / "vendor_payments.csv"


def main() -> None:
    payments = pd.read_csv(
        CSV_PATH,
        parse_dates=["invoice_date", "due_date", "payment_date"],
    )

    print(f"Shape: {payments.shape}")
    print("\nNulls by column:")
    print(payments.isna().sum().to_string())
    print("\nDtypes:")
    print(payments.dtypes.to_string())


if __name__ == "__main__":
    main()