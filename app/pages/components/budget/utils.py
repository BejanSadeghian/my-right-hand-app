import pandas as pd
import numpy as np
import uuid

from sqlalchemy.engine.base import Engine
from sqlalchemy import text
from icecream import ic
from typing import Callable

from .exceptions import MissingData


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
                # data_to_insert = pd.DataFrame([row])

                date = row["date"]
                account = row["account"]
                desc = row["description"]
                category = row["category"]
                tags = row["tags"]
                amount = float(row["amount"])
                query = text(
                    (
                        f"INSERT INTO {schema}.transactions "
                        "(date, account, description, category, tags, amount, id) "
                        "VALUES (:date, :account, :desc, :category, "
                        ":tags, :amount, :id)"
                    )
                )
                conn.execute(
                    query,
                    parameters={
                        "date": date,
                        "account": account,
                        "desc": desc,
                        "category": category,
                        "tags": tags,
                        "amount": amount,
                        "id": id,
                    },
                )
                conn.commit()
                new_record_ids.append(id)
    return new_record_ids


def fetch_accounts(schema: str, sql_engine: Engine):
    with sql_engine.connect() as conn:
        query_accounts = f"SELECT * FROM {schema}.accounts"
        results = conn.execute(text(query_accounts))
        results = results.fetchall()

    if len(results) > 0:
        return pd.DataFrame(results)
    raise MissingData("No Account Data")


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


def replace_data(
    new_data: pd.DataFrame,
    table: str,
    schema: str,
    sql_engine: Engine,
    replace_ids: list[str] = None,
    replace_all: bool = False,
):
    # ic(new_data, replace_all)
    with sql_engine.connect() as conn:
        if replace_all:
            conn.execute(text(f"TRUNCATE {schema}.{table};"))
        elif replace_ids is not None:
            for id in replace_ids:
                delete_query = text(f"DELETE FROM {schema}.{table} WHERE id = :id")
                conn.execute(delete_query, parameters={"id": id})
        num_rows_effected = new_data.to_sql(
            name=table,
            con=conn,
            schema=schema,
            if_exists="append",
            index=False,
        )

        conn.commit()
        if num_rows_effected != new_data.shape[0]:
            return False
        else:
            return True


def generate_empty_budget(unique_categories: list[str]) -> pd.DataFrame:
    new_budget_df = pd.DataFrame()
    new_budget_df["id"] = [uuid.uuid4() for _ in unique_categories]
    new_budget_df["category"] = unique_categories
    new_budget_df["monthly"] = None
    new_budget_df["yearly"] = None
    return new_budget_df


def generate_empty_account(unique_accounts: list[str], default="Other") -> pd.DataFrame:
    new_account_df = pd.DataFrame()
    new_account_df["id"] = [uuid.uuid4() for _ in unique_accounts]
    new_account_df["name"] = unique_accounts
    new_account_df["type"] = None
    new_account_df["tag"] = None
    return new_account_df


def fetch_budget_data(
    schema: str,
    sql_engine: Engine,
):
    with sql_engine.connect() as conn:
        query = text(f"SELECT * FROM {schema}.budget")
        result = conn.execute(query)
        data = result.fetchall()
    if data:
        res = pd.DataFrame(data)
        res["monthly"] = res["monthly"].astype(float)
        res["yearly"] = res["yearly"].astype(float)
        res.columns = [x.capitalize() for x in res.columns]
        res = res.sort_values(by="Category")

        return res
    raise MissingData("No Budget Data Found")


def fetch_all_transaction_categories(
    schema: str,
    sql_engine: Engine,
) -> list[str]:
    with sql_engine.connect() as conn:
        query = text(f"SELECT DISTINCT category FROM {schema}.transactions")
        result = conn.execute(query)
        data = result.fetchall()
    if data:
        return [x[0] for x in data]
    raise MissingData("No Category Data Found")


def fetch_transaction_data(
    accounts: list[str],
    category: str,
    month: int,
    year: int,
    schema: str,
    sql_engine: Engine,
):
    ic(accounts, category, month, year)
    with sql_engine.connect() as conn:
        query = (
            "SELECT *, EXTRACT(MONTH FROM CAST(date AS DATE)) as Month, "
            "EXTRACT(YEAR FROM CAST(date AS DATE)) as Year "
            f"FROM {schema}.transactions"
        )
        conditions = []
        if not accounts:
            raise MissingData("No Account Specified")

        if "All" not in accounts:
            account_list = ["'" + account + "'" for account in accounts]
            conditions.append(f"account IN ({', '.join(account_list)})")
        if category != "All":
            conditions.append(f"category = '{category}'")
        if month != "All":
            conditions.append(f"EXTRACT(MONTH FROM CAST(date AS DATE)) = {month}")
        if year != "All":
            conditions.append(f"EXTRACT(YEAR FROM CAST(date AS DATE)) = {year}")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        result = conn.execute(text(query))
        data = result.fetchall()
    if len(data) != 0:
        data = pd.DataFrame(data)
        data["amount"] = data["amount"].astype(float)
        data.columns = [x.capitalize() for x in data.columns]
        data = data.sort_values(by="Date", ascending=False)
        return data
    ic(query)
    raise MissingData("No Data Found")


def reconcile_data(
    fetch_func: Callable,
    field_name: str,
    all_values: list[str],
    table: str,
    schema: str,
    sql_engine: Engine,
    generator_func: Callable,
):
    try:
        current_data = fetch_func(schema, sql_engine)
        existing_values = current_data[field_name].tolist()
    except MissingData as e:
        # st.toast(e, icon="❗")
        existing_values = []
    missing_data = [x for x in all_values if x not in existing_values]
    if missing_data:
        new_records = generator_func(missing_data)

        success_flag = replace_data(
            new_records,
            schema=schema,
            table=table,
            sql_engine=sql_engine,
        )
        return success_flag, missing_data
    return True, []
