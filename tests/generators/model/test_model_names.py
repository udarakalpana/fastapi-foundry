"""Tests for how model names are validated and turned into file and table names.

These are pure string functions, so they are checked directly with parametrised
cases rather than by generating files.
"""

import pytest

from fastapi_foundry.generators.model import (
    InvalidModelNameError,
    model_module_name,
    model_name_for_table,
    normalize_model_name,
    table_name_for_model,
)

# --- normalize_model_name -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ProductModel", "ProductModel"),
        ("  ProductModel  ", "ProductModel"),
        ("Product", "Product"),
        ("OrderItem2Model", "OrderItem2Model"),
        ("HTTPClientModel", "HTTPClientModel"),
    ],
)
def test_pascal_case_model_names_are_accepted(raw: str, expected: str) -> None:
    assert normalize_model_name(raw) == expected


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
        "productModel",
        "product_model",
        "Product_Model",
        "Product Model",
        "Product-Model",
        "1ProductModel",
        "../ProductModel",
        "app/ProductModel",
        "Product.Model",
        "Model",
        "Base",
        "None",
        "True",
        "False",
    ],
)
def test_invalid_model_names_are_rejected(invalid_name: str) -> None:
    with pytest.raises(InvalidModelNameError):
        normalize_model_name(invalid_name)


def test_error_message_shows_an_example() -> None:
    with pytest.raises(InvalidModelNameError, match="ProductModel"):
        normalize_model_name("product")


def test_model_name_whose_table_name_is_too_long_is_rejected() -> None:
    with pytest.raises(InvalidModelNameError):
        normalize_model_name("A" * 70 + "Model")


# --- model_module_name ----------------------------------------------------


@pytest.mark.parametrize(
    ("model_name", "module"),
    [
        ("ProductModel", "product_model"),
        ("Product", "product"),
        ("OrderItemModel", "order_item_model"),
        ("HTTPClientModel", "http_client_model"),
        ("OrderItem2Model", "order_item2_model"),
    ],
)
def test_module_name_is_snake_case(model_name: str, module: str) -> None:
    assert model_module_name(model_name) == module


# --- table_name_for_model -------------------------------------------------


@pytest.mark.parametrize(
    ("model_name", "table"),
    [
        ("ProductModel", "products"),
        ("Product", "products"),
        ("UserModel", "users"),
        ("CategoryModel", "categories"),
        ("OrderItemModel", "order_items"),
        ("AddressModel", "addresses"),
        ("BoxModel", "boxes"),
        ("BranchModel", "branches"),
        ("DayModel", "days"),
        ("HTTPClientModel", "http_clients"),
    ],
)
def test_table_name_is_derived_from_the_model_name(model_name: str, table: str) -> None:
    assert table_name_for_model(model_name) == table


# --- model_name_for_table -------------------------------------------------


@pytest.mark.parametrize(
    ("table", "model_name"),
    [
        ("users", "UserModel"),
        ("products", "ProductModel"),
        ("user_roles", "UserRoleModel"),
        ("categories", "CategoryModel"),
        ("addresses", "AddressModel"),
        ("boxes", "BoxModel"),
        ("branches", "BranchModel"),
        ("status", "StatusModel"),
        ("access", "AccessModel"),
        ("inventory", "InventoryModel"),
    ],
)
def test_default_model_name_is_derived_from_the_table(table: str, model_name: str) -> None:
    assert model_name_for_table(table) == model_name


@pytest.mark.parametrize("table", ["users", "user_roles", "categories", "status", "a1_b2"])
def test_default_model_name_is_itself_valid(table: str) -> None:
    assert normalize_model_name(model_name_for_table(table)) == model_name_for_table(table)
