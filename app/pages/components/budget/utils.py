import pandas as pd
import numpy as np

from sqlalchemy.engine.base import Engine
from sqlalchemy import text
from icecream import ic
from enum import Enum

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


# class BudgetType(Enum):
#     monthly = "monthly"
#     monthly = "yearly"


# def update_budget_record(
#     id: str,
#     field: BudgetType,
#     amount: float,
#     schema: str,
#     sql_engine: Engine,
# ) -> bool:
#     with sql_engine.connect() as conn:
#         query = text(f"UPDATE {schema}.budget SET :field = :amount where id = :id")
#         result = conn.execute(
#             query, parameters={"field": field, "amount": amount, "id": id}
#         )
#         conn.commit()
#     # Check if the update was successful
#     if result.rowcount == 0:
#         return False
#     else:
#         return True


def replace_budget(
    new_budget_data: pd.DataFrame,
    schema: str,
    sql_engine: Engine,
    replace_ids: list[str] = None,
    replace_all: bool = False,
):
    # ic(new_budget_data, replace_all)
    with sql_engine.connect() as conn:
        if replace_all:
            conn.execute(text(f"TRUNCATE {schema}.budget;"))
        elif replace_ids is not None:
            for id in replace_ids:
                delete_query = text(f"DELETE FROM {schema}.budget WHERE id = :id")
                conn.execute(delete_query, parameters={"id": id})
        num_rows_effected = new_budget_data.to_sql(
            name="budget",
            con=conn,
            schema=schema,
            if_exists="append",
            index=False,
        )

        conn.commit()
        if num_rows_effected != new_budget_data.shape[0]:
            return False
        else:
            return True


def generate_empty_budget(unique_categories: list[str]) -> pd.DataFrame:
    new_budget_df = pd.DataFrame()
    new_budget_df["id"] = [uuid.uuid4() for _ in unique_categories.values]
    new_budget_df["category"] = unique_categories.values
    new_budget_df["monthly"] = None
    new_budget_df["yearly"] = None
    return new_budget_df


def fetch_budget_data(
    gb_field: str,
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
    if len(data) == 0:
        ic(query)
        raise MissingData("No Data Found")
    data = pd.DataFrame(data)
    data["amount"] = data["amount"].astype(float)
    data.columns = [x.capitalize() for x in data.columns]
    data = data.sort_values(by="Date", ascending=False)
    return data
