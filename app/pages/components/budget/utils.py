import pandas as pd
import numpy as np

from sqlalchemy.engine.base import Engine
from sqlalchemy import text
from icecream import ic


def get_filtered_data(df, accounts, category, month, year, ALL_VAR):
    return df[
        ((ALL_VAR in accounts) | (df["Account"].apply(lambda x: x in accounts)))
        & ((df["Category"] == category) | (category == ALL_VAR))
        & ((df["Month"] == month) | (month == ALL_VAR))
        & ((df["Year"] == year) | (year == ALL_VAR))
    ]


def generate_hash(df: pd.DataFrame):
    return pd.util.hash_pandas_object(df, index=False)


def add_records(
    df: pd.DataFrame,
    schema: str,
    sql_engine: Engine,
):
    new_record_ids = []
    unacknowledgements = []
    for index, row in df.iterrows():
        ic(row)
        with sql_engine.connect() as conn:
            id = row["id"]
            row = row.fillna("")
            result = conn.execute(
                text(f"SELECT * FROM {schema}.transactions WHERE id = '{id}'")
            )
            existing_record = result.fetchone()
            if existing_record is None:
                data_to_insert = pd.DataFrame([row])

                date = row["date"]
                account = row["account"]
                desc = row["description"]
                category = row["category"]
                tags = row["tags"]
                amount = row["amount"]
                query = text(
                    (
                        f"INSERT INTO {schema}.transactions "
                        "(date, account, description, category, tags, amount, id) "
                        f"VALUES ('{date}', '{account}', '{desc}', '{category}', "
                        f"'{tags}', {amount}, '{id}')"
                    )
                )
                conn.execute(query)
                conn.commit()
                new_record_ids.append(id)
    return new_record_ids


def fetch_options(schema: str, sql_engine: Engine):
    with sql_engine.connect() as conn:
        query_accounts = f"SELECT DISTINCT account FROM {schema}.transactions"
        result_accounts = conn.execute(text(query_accounts))
        unique_accounts = sorted([row[0] for row in result_accounts.fetchall()])

        query_categories = f"SELECT DISTINCT category FROM {schema}.transactions"
        result_categories = conn.execute(text(query_categories))
        unique_categories = sorted([row[0] for row in result_categories.fetchall()])

        query_months = f"SELECT DISTINCT EXTRACT(MONTH FROM CAST(date AS DATE)) AS month FROM {schema}.transactions"
        result_months = conn.execute(text(query_months))
        unique_months = sorted([int(row[0]) for row in result_months.fetchall()])

        query_years = f"SELECT DISTINCT EXTRACT(YEAR FROM CAST(date AS DATE)) AS year FROM {schema}.transactions"
        result_years = conn.execute(text(query_years))
        unique_years = sorted(
            [int(row[0]) for row in result_years.fetchall()],
            reverse=True,
        )

    return {
        "accounts": unique_accounts,
        "categories": unique_categories,
        "months": unique_months,
        "years": unique_years,
    }


def fetch_transaction_data(
    accounts: list[str],
    category: str,
    month: str,
    year: str,
    schema: str,
    sql_engine: Engine,
):
    with sql_engine.connect() as conn:
        query = (
            "SELECT *, EXTRACT(MONTH FROM CAST(date AS DATE)) as Month, "
            "EXTRACT(YEAR FROM CAST(date AS DATE)) as Year "
            f"FROM {schema}.transactions"
        )
        conditions = []
        if "All" not in accounts:
            account_list = ["'" + account + "'" for account in accounts]
            conditions.append(f"account IN ({', '.join(account_list)})")
        if category != "All":
            conditions.append(f"category = '{category}'")
        if month != "All":
            conditions.append(f"EXTRACT(MONTH FROM CAST(date AS DATE)) = '{month}'")
        if year != "All":
            conditions.append(f"EXTRACT(YEAR FROM CAST(date AS DATE)) = '{year}'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        result = conn.execute(text(query))
        data = result.fetchall()
    data = pd.DataFrame(data)
    data["amount"] = data["amount"].astype(float)
    data.columns = [x.capitalize() for x in data.columns]
    return data
