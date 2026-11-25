"""Tests for how controller names are validated and turned into module and route names.

These are pure string functions, so they are checked directly with parametrised
cases rather than by generating files.
"""

import pytest

from fastapi_foundry.generators.controller import (
    InvalidControllerNameError,
    controller_module_name,
    normalize_controller_name,
    route_function_name,
    route_path_for_controller,
)

# --- normalize_controller_name --------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ProductController", "ProductController"),
        ("  ProductController  ", "ProductController"),
        ("OrderItem2Controller", "OrderItem2Controller"),
        ("HTTPClientController", "HTTPClientController"),
    ],
)
def test_pascal_case_controller_names_are_accepted(raw: str, expected: str) -> None:
    assert normalize_controller_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Product", "ProductController"),
        ("OrderItem", "OrderItemController"),
        ("None", "NoneController"),
    ],
)
def test_controller_suffix_is_added_when_missing(raw: str, expected: str) -> None:
    assert normalize_controller_name(raw) == expected


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
        "productController",
        "product_controller",
        "Product_Controller",
        "Product Controller",
        "Product-Controller",
        "1ProductController",
        "../ProductController",
        "app/ProductController",
        "Product.Controller",
        "Controller",
    ],
)
def test_invalid_controller_names_are_rejected(invalid_name: str) -> None:
    with pytest.raises(InvalidControllerNameError):
        normalize_controller_name(invalid_name)


def test_error_message_shows_an_example() -> None:
    with pytest.raises(InvalidControllerNameError, match="ProductController"):
        normalize_controller_name("product")


def test_overly_long_controller_name_is_rejected() -> None:
    with pytest.raises(InvalidControllerNameError, match="too long"):
        normalize_controller_name("A" * 70 + "Controller")


# --- controller_module_name -----------------------------------------------


@pytest.mark.parametrize(
    ("controller_name", "module"),
    [
        ("ProductController", "product_controller"),
        ("HomeController", "home_controller"),
        ("OrderItemController", "order_item_controller"),
        ("HTTPClientController", "http_client_controller"),
        ("OrderItem2Controller", "order_item2_controller"),
    ],
)
def test_module_name_is_snake_case(controller_name: str, module: str) -> None:
    assert controller_module_name(controller_name) == module


# --- route names ----------------------------------------------------------


@pytest.mark.parametrize(
    ("controller_name", "path"),
    [
        ("ProductController", "/products"),
        ("CategoryController", "/categories"),
        ("OrderItemController", "/order-items"),
        ("AddressController", "/addresses"),
        ("HTTPClientController", "/http-clients"),
    ],
)
def test_route_path_is_the_plural_kebab_case_resource(controller_name: str, path: str) -> None:
    assert route_path_for_controller(controller_name) == path


@pytest.mark.parametrize(
    ("controller_name", "function"),
    [
        ("ProductController", "list_products"),
        ("OrderItemController", "list_order_items"),
    ],
)
def test_route_function_name_lists_the_resource(controller_name: str, function: str) -> None:
    assert route_function_name(controller_name) == function
